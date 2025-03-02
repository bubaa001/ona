from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, FileField
from wtforms.validators import DataRequired, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
import stripe
import os
import random

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Replace with a secure key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ona.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/images/profiles')
stripe.api_key = 'your-stripe-secret-key'  # Replace with your Stripe secret key

# Initialize extensions
db = SQLAlchemy(app)  # Single db instance tied to app
socketio = SocketIO(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Import models after db is initialized to avoid circular imports
from models import User, Gift

# Forms
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    gender = StringField('Gender', validators=[DataRequired()])
    is_model = BooleanField('Register as Model')
    submit = SubmitField('Register')

class ProfileForm(FlaskForm):
    profile_picture = FileField('Profile Picture')
    submit = SubmitField('Update Profile')

# User Loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('profile'))
        flash('Invalid credentials')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(username=form.username.data, email=form.email.data, password=hashed_password,
                    gender=form.gender.data.lower(), is_model=form.is_model.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    if form.validate_on_submit():
        if form.profile_picture.data:
            file = form.profile_picture.data
            filename = f"{current_user.id}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            current_user.profile_picture = filename
            db.session.commit()
            flash('Profile picture updated!')
    return render_template('profile.html', user=current_user, form=form)

@app.route('/chat')
@login_required
def chat():
    opposite_gender = 'female' if current_user.gender == 'male' else 'male'
    potential_partners = User.query.filter_by(gender=opposite_gender).all()
    chat_partner = random.choice(potential_partners) if potential_partners else None
    return render_template('chat.html', partner=chat_partner)

@app.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    if request.method == 'POST':
        amount = int(request.form['amount']) * 100
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='usd',
                payment_method=request.form['payment_method_id'],
                confirmation_method='manual',
                confirm=True,
            )
            current_user.balance += amount / 100
            db.session.commit()
            flash('Payment successful!')
            return redirect(url_for('profile'))
        except stripe.error.StripeError as e:
            flash(f'Payment failed: {str(e)}')
    return render_template('payment.html')

@app.route('/create-payment-intent', methods=['POST'])
@login_required
def create_payment_intent():
    amount = int(request.json['amount']) * 100
    intent = stripe.PaymentIntent.create(
        amount=amount,
        currency='usd',
    )
    return jsonify({'clientSecret': intent['client_secret']})

@app.route('/profiles/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# SocketIO Events
@socketio.on('connect')
def handle_connect():
    emit('message', {'data': 'Connected'})

@socketio.on('start_chat')
def handle_chat(data):
    peer_id = data['peer_id']
    emit('chat_started', {'user': current_user.username, 'peer_id': peer_id}, broadcast=True)

@socketio.on('send_gift')
def handle_gift(data):
    gift = Gift.query.get(data['gift_id'])
    if current_user.balance >= gift.cost:
        current_user.balance -= gift.cost
        recipient = User.query.get(data['recipient_id'])
        if recipient.is_model:
            recipient.balance += gift.cost * 0.8
        db.session.commit()
        emit('gift_received', {'gift': gift.name, 'from': current_user.username}, room=data['recipient_id'])

# Database initialization function
def init_db():
    with app.app_context():
        db.create_all()
        if not Gift.query.first():
            gifts = [Gift(name='Heart', cost=1.0), Gift(name='Flower', cost=2.0)]
            db.session.bulk_save_objects(gifts)
            db.session.commit()

if __name__ == '__main__':
    init_db()  # Call initialization function
    socketio.run(app, debug=True)