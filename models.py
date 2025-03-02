from flask_login import UserMixin
from app import db  # Import db from app.py

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)  # Hashed
    gender = db.Column(db.String(10), nullable=False)
    is_model = db.Column(db.Boolean, default=False)
    balance = db.Column(db.Float, default=0.0)
    profile_picture = db.Column(db.String(200), default='default.png')

class Gift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    cost = db.Column(db.Float, nullable=False)