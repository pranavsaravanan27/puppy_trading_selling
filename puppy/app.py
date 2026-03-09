import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename # Used to secure file names
import datetime

# Configuration
app = Flask(__name__, template_folder='.') 
app.config['SECRET_KEY'] = 'secret_key_change_this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuration for Image Uploads
# Use os.path.join for better Windows compatibility
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create folder only if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- DATABASE MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='buyer')

class Puppy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    breed = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    image_filename = db.Column(db.String(100), nullable=True) # New column for image
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='Available')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES ---

@app.route('/')
def index():
    puppies = Puppy.query.filter_by(status='Available').all()
    return render_template('index.html', puppies=puppies)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        
        hashed_pw = generate_password_hash(password, method='sha256')
        new_user = User(username=username, password=hashed_pw, role=role)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except:
            flash('Username already exists')
            
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/add_puppy', methods=['GET', 'POST'])
@login_required
def add_puppy():
    if current_user.role != 'seller':
        flash('Only sellers can add puppies.')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        breed = request.form.get('breed')
        price = request.form.get('price')
        description = request.form.get('description')
        
        # Handle Image Upload
        file = request.files['image']
        filename = None
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        new_puppy = Puppy(name=name, breed=breed, price=float(price), 
                          description=description, image_filename=filename, 
                          seller_id=current_user.id)
        db.session.add(new_puppy)
        db.session.commit()
        flash('Puppy added successfully!')
        return redirect(url_for('index'))
        
    return render_template('add_puppy.html')

@app.route('/buy/<int:puppy_id>')
@login_required
def buy(puppy_id):
    puppy = Puppy.query.get(puppy_id)
    if puppy.status == 'Sold':
        flash('This puppy is already sold.')
        return redirect(url_for('index'))
    return render_template('buy.html', puppy=puppy)

@app.route('/pay/<int:puppy_id>', methods=['POST'])
@login_required
def pay(puppy_id):
    puppy = Puppy.query.get(puppy_id)
    puppy.status = 'Sold'
    db.session.commit()
    
    transaction_id = f"TXN{datetime.datetime.now().timestamp()}"
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return render_template('payment.html', puppy=puppy, transaction_id=transaction_id, date=date)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)