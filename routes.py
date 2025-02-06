from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db, login_manager
from models import User, MutualFund, Portfolio, Transaction
from werkzeug.security import generate_password_hash
import json

@login_manager.user_loader
def load_user(id):
    return db.session.get(User, int(id))

def init_mock_data():
    if MutualFund.query.first() is None:
        mock_funds = [
            {'name': 'Growth Fund', 'ticker': 'GRWTH', 'category': 'Equity', 'nav': 25.75, 'expense_ratio': 1.2, 'risk_level': 'High', 'min_investment': 5000},
            {'name': 'Balanced Fund', 'ticker': 'BLNCD', 'category': 'Hybrid', 'nav': 18.50, 'expense_ratio': 1.0, 'risk_level': 'Medium', 'min_investment': 3000},
            {'name': 'Income Fund', 'ticker': 'INCM', 'category': 'Debt', 'nav': 15.25, 'expense_ratio': 0.8, 'risk_level': 'Low', 'min_investment': 2000}
        ]

        for fund_data in mock_funds:
            fund = MutualFund(**fund_data)
            db.session.add(fund)

        db.session.commit()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        existing_user = User.query.filter_by(email=request.form['email']).first()
        if existing_user:
            flash('Email already registered')
            return redirect(url_for('register'))

        user = User(
            username=request.form['username'],
            email=request.form['email']
        )
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    portfolios = Portfolio.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', portfolios=portfolios)

@app.route('/funds')
@login_required
def funds():
    funds = MutualFund.query.all()
    return render_template('funds.html', funds=funds)

@app.route('/transactions')
@login_required
def transactions():
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.timestamp.desc()).all()
    return render_template('transactions.html', transactions=transactions)

@app.route('/api/portfolio-data')
@login_required
def portfolio_data():
    portfolios = Portfolio.query.filter_by(user_id=current_user.id).all()
    data = []
    for portfolio in portfolios:
        fund = MutualFund.query.get(portfolio.fund_id)
        current_value = portfolio.units * fund.nav
        data.append({
            'fund_name': fund.name,
            'units': portfolio.units,
            'current_value': current_value,
            'purchase_value': portfolio.units * portfolio.purchase_nav
        })
    return jsonify(data)

with app.app_context():
    init_mock_data()