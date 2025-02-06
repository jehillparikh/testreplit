from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    portfolios = db.relationship('Portfolio', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)
    kyc = db.relationship('KYC', backref='user', uselist=False, lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class KYC(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pan_number = db.Column(db.String(10), unique=True)
    aadhaar_number = db.Column(db.String(12), unique=True)
    pan_verified = db.Column(db.Boolean, default=False)
    aadhaar_verified = db.Column(db.Boolean, default=False)
    face_verified = db.Column(db.Boolean, default=False)
    bank_verified = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, rejected
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class MutualFund(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    ticker = db.Column(db.String(10), unique=True, nullable=False)
    category = db.Column(db.String(50))
    nav = db.Column(db.Float, nullable=False)
    expense_ratio = db.Column(db.Float)
    risk_level = db.Column(db.String(20))
    min_investment = db.Column(db.Float)

class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    fund_id = db.Column(db.Integer, db.ForeignKey('mutual_fund.id'), nullable=False)
    units = db.Column(db.Float, nullable=False)
    purchase_nav = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    fund_id = db.Column(db.Integer, db.ForeignKey('mutual_fund.id'), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)  # 'BUY' or 'SELL'
    units = db.Column(db.Float, nullable=False)
    nav = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=True)

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='INR')
    razorpay_order_id = db.Column(db.String(200), unique=True)
    razorpay_payment_id = db.Column(db.String(200), unique=True)
    razorpay_signature = db.Column(db.String(500))
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, completed, failed
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)