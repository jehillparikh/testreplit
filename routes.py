from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db, login_manager
from models import User, MutualFund, Portfolio, Transaction, Payment
from werkzeug.security import generate_password_hash
from services.payment_service import PaymentService
from services.kyc_service import KYCService
import json
import base64
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import random
from openai import OpenAI
import os

payment_service = PaymentService()
kyc_service = KYCService()

@login_manager.user_loader
def load_user(id):
    return db.session.get(User, int(id))

def init_mock_data():
    # Create test admin user if not exists
    if User.query.filter_by(email='admin@test.com').first() is None:
        admin_user = User(
            username='admin',
            email='admin@test.com'
        )
        admin_user.set_password('admin123')  # Set a known password for testing
        db.session.add(admin_user)
        db.session.commit()
        app.logger.info('Created test admin user')
    else:
        app.logger.info('Test admin user already exists')

    # Initialize mock funds if not exists
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
        app.logger.info('Initialized mock funds')

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
        # Step 1: Basic user registration
        existing_user = User.query.filter_by(email=request.form['email']).first()
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 400

        user = User(
            username=request.form['username'],
            email=request.form['email']
        )
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.commit()

        # Initialize KYC record
        kyc = kyc_service.start_kyc(user.id)

        login_user(user)
        return jsonify({'status': 'success', 'user_id': user.id})

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
    # Get all funds
    funds = MutualFund.query.all()

    # Mock recommended funds with detailed information
    recommended_funds = []
    fund_managers = [
        {"name": "John Smith", "experience": 15, "fund_house": "Alpha Investments"},
        {"name": "Sarah Johnson", "experience": 12, "fund_house": "Beta Capital"},
        {"name": "Michael Chen", "experience": 18, "fund_house": "Gamma Asset Management"},
        {"name": "Lisa Brown", "experience": 10, "fund_house": "Delta Funds"}
    ]

    for i, fund in enumerate(funds[:10]):  # Taking top 10 funds as recommended
        fund.returns_1y = random.uniform(12, 18)
        fund.returns_3y = random.uniform(35, 50)
        fund.returns_5y = random.uniform(75, 95)
        fund.expense_ratio = random.uniform(0.5, 1.5)
        fund.fund_house = fund_managers[i % len(fund_managers)]["fund_house"]
        fund.manager_name = fund_managers[i % len(fund_managers)]["name"]
        fund.manager_experience = fund_managers[i % len(fund_managers)]["experience"]
        recommended_funds.append(fund)

    # Add mock returns to all funds
    for fund in funds:
        if fund not in recommended_funds:
            fund.returns_1y = random.uniform(8, 20)
            fund.returns_3y = random.uniform(30, 55)
            fund.returns_5y = random.uniform(70, 100)
            fund.expense_ratio = random.uniform(0.5, 2.0)
            fund.fund_house = random.choice([m["fund_house"] for m in fund_managers])
            fund.manager_name = random.choice([m["name"] for m in fund_managers])
            fund.manager_experience = random.randint(8, 20)

    return render_template('funds.html', funds=funds, recommended_funds=recommended_funds)

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

@app.route('/api/create-payment', methods=['POST'])
@login_required
def create_payment():
    data = request.get_json()
    fund_id = data.get('fund_id')
    amount = float(data.get('amount'))

    fund = MutualFund.query.get(fund_id)
    if not fund:
        return jsonify({'error': 'Invalid fund'}), 400

    if amount < fund.min_investment:
        return jsonify({'error': f'Minimum investment amount is ₹{fund.min_investment}'}), 400

    try:
        payment = payment_service.create_order(current_user.id, amount)
        return jsonify({
            'id': payment.id,
            'order_id': payment.razorpay_order_id,
            'amount': payment.amount,
            'key': app.config.get('RAZORPAY_KEY_ID', 'dummy_key')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify-payment', methods=['POST'])
@login_required
def verify_payment():
    data = request.get_json()
    payment_id = data.get('payment_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    fund_id = data.get('fund_id')

    try:
        if payment_service.verify_payment(payment_id, razorpay_payment_id, razorpay_signature):
            payment = Payment.query.get(payment_id)
            transaction = payment_service.process_investment(payment, fund_id)
            return jsonify({
                'status': 'success',
                'transaction_id': transaction.id
            })
        return jsonify({'error': 'Payment verification failed'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/kyc', methods=['GET'])
@login_required
def kyc():
    kyc_record = current_user.kyc
    return render_template('kyc.html', kyc=kyc_record)

@app.route('/api/kyc/upload-pan', methods=['POST'])
@login_required
def upload_pan():
    if 'pan_image' not in request.files:
        return jsonify({'error': 'No PAN image provided'}), 400

    pan_image = request.files['pan_image']
    pan_number = request.form.get('pan_number')

    if not pan_image or not pan_number:
        return jsonify({'error': 'Missing required fields'}), 400

    # Convert image to base64 for API
    image_data = base64.b64encode(pan_image.read()).decode()

    success, result = kyc_service.hyperverge.verify_pan(pan_number, image_data)
    if success:
        kyc_service.update_kyc_status(
            current_user.kyc.id,
            pan_number=pan_number,
            pan_verified=True
        )
        return jsonify({'status': 'success', 'message': 'PAN verified successfully'})

    return jsonify({'error': result}), 400

@app.route('/api/kyc/upload-aadhaar', methods=['POST'])
@login_required
def upload_aadhaar():
    if 'aadhaar_front' not in request.files or 'aadhaar_back' not in request.files:
        return jsonify({'error': 'Both Aadhaar front and back images are required'}), 400

    aadhaar_front = request.files['aadhaar_front']
    aadhaar_back = request.files['aadhaar_back']
    aadhaar_number = request.form.get('aadhaar_number')

    if not aadhaar_number:
        return jsonify({'error': 'Aadhaar number is required'}), 400

    # Convert images to base64
    front_data = base64.b64encode(aadhaar_front.read()).decode()
    back_data = base64.b64encode(aadhaar_back.read()).decode()

    success, result = kyc_service.hyperverge.verify_aadhaar(aadhaar_number, front_data, back_data)
    if success:
        kyc_service.update_kyc_status(
            current_user.kyc.id,
            aadhaar_number=aadhaar_number,
            aadhaar_verified=True
        )
        return jsonify({'status': 'success', 'message': 'Aadhaar verified successfully'})

    return jsonify({'error': result}), 400

@app.route('/api/kyc/verify-face', methods=['POST'])
@login_required
def verify_face():
    if 'selfie' not in request.files:
        return jsonify({'error': 'Selfie image is required'}), 400

    selfie = request.files['selfie']
    id_image = request.files.get('id_image')  # Optional, can use previously uploaded ID

    selfie_data = base64.b64encode(selfie.read()).decode()
    id_data = base64.b64encode(id_image.read()).decode() if id_image else None

    success, result = kyc_service.hyperverge.face_match(selfie_data, id_data)
    if success:
        kyc_service.update_kyc_status(
            current_user.kyc.id,
            face_verified=True
        )
        return jsonify({'status': 'success', 'message': 'Face verification successful'})

    return jsonify({'error': result}), 400

@app.route('/api/kyc/verify-bank', methods=['POST'])
@login_required
def verify_bank():
    account_number = request.form.get('account_number')
    ifsc_code = request.form.get('ifsc_code')

    if not account_number or not ifsc_code:
        return jsonify({'error': 'Account number and IFSC code are required'}), 400

    success, result = kyc_service.hyperverge.verify_bank_account(account_number, ifsc_code)
    if success:
        kyc_service.update_kyc_status(
            current_user.kyc.id,
            bank_verified=True
        )
        return jsonify({'status': 'success', 'message': 'Bank account verified successfully'})

    return jsonify({'error': result}), 400

@app.route('/api/chatbot', methods=['POST'])
@login_required
def chatbot():
    data = request.get_json()
    message = data.get('message', '').lower()

    # Check if OpenAI API key is configured
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return jsonify({
            'response': "I apologize, but I'm currently under maintenance. Please try again later when the service is fully configured."
        }), 503

    try:
        # Initialize OpenAI client only when needed
        openai_client = OpenAI(api_key=api_key)

        # Prepare system message for finance expertise
        system_message = """You are a knowledgeable mutual fund investment advisor. 
        Provide clear, accurate advice about mutual funds, investment strategies, 
        and market insights. Use simple language and explain complex terms. 
        Keep responses concise yet informative."""

        # Create chat completion
        response = openai_client.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=500
        )

        return jsonify({'response': response.choices[0].message.content})

    except Exception as e:
        app.logger.error(f"OpenAI API error: {str(e)}")
        return jsonify({
            'response': 'I apologize, but I encountered an error. Please try again or contact support if the issue persists.'
        }), 500

@app.route('/agent')
@login_required
def agent():
    return render_template('agent.html')

@app.route('/fund/<int:fund_id>')
@login_required
def fund_details(fund_id):
    fund = MutualFund.query.get_or_404(fund_id)
    portfolio = Portfolio.query.filter_by(user_id=current_user.id, fund_id=fund_id).first()

    # Add mock sector allocation data
    fund.sector_allocation = {
        'Financial Services': 35.2,
        'Technology': 25.8,
        'Consumer Goods': 15.5,
        'Healthcare': 10.2,
        'Automobile': 8.3,
        'Others': 5.0
    }

    fund.manager_name = "John Smith"
    fund.manager_experience = 15
    fund.manager_image = url_for('static', filename='images/default_manager.svg')
    fund.manager_bio = "Over 15 years of experience in fund management with expertise in equity markets."
    fund.launch_date = "Jan 1, 2010"
    fund.aum = "1,234.56"
    fund.exit_load = "1% if redeemed within 1 year"

    return render_template('fund_details.html', fund=fund, portfolio=portfolio)

@app.route('/api/fund-performance/<int:fund_id>')
@login_required
def fund_performance(fund_id):
    period = request.args.get('period', '1Y')

    # Mock performance data

    dates = []
    fund_nav = []
    benchmark = []

    periods = {
        '1M': 30,
        '3M': 90,
        '6M': 180,
        '1Y': 365,
        '3Y': 1095,
        '5Y': 1825
    }

    days = periods.get(period, 365)
    base_nav = 100
    base_benchmark = 100

    for i in range(days):
        date = datetime.now() - timedelta(days=days-i)
        dates.append(date.strftime('%Y-%m-%d'))

        # Generate slightly different random walks for fund and benchmark
        base_nav *= (1 + random.uniform(-0.01, 0.012))
        base_benchmark *= (1 + random.uniform(-0.009, 0.01))

        fund_nav.append(round(base_nav, 2))
        benchmark.append(round(base_benchmark, 2))

    # Calculate returns for different periods
    returns = {
        '1M': {'fund': 2.5, 'category': 2.1, 'benchmark': 1.9},
        '3M': {'fund': 7.8, 'category': 6.9, 'benchmark': 6.5},
        '6M': {'fund': 15.2, 'category': 14.1, 'benchmark': 13.8},
        '1Y': {'fund': 22.5, 'category': 20.8, 'benchmark': 19.5},
        '3Y': {'fund': 45.6, 'category': 42.3, 'benchmark': 40.1},
        '5Y': {'fund': 98.4, 'category': 92.1, 'benchmark': 88.7}
    }

    return jsonify({
        'labels': dates,
        'fund_nav': fund_nav,
        'benchmark': benchmark,
        'returns': returns
    })

@app.route('/api/sell-units', methods=['POST'])
@login_required
def sell_units():
    data = request.get_json()
    fund_id = data.get('fund_id')
    units = float(data.get('units'))

    portfolio = Portfolio.query.filter_by(
        user_id=current_user.id,
        fund_id=fund_id
    ).first()

    if not portfolio or portfolio.units < units:
        return jsonify({'error': 'Insufficient units'}), 400

    fund = MutualFund.query.get(fund_id)
    amount = units * fund.nav

    # Create sell transaction
    transaction = Transaction(
        user_id=current_user.id,
        fund_id=fund_id,
        transaction_type='SELL',
        units=units,
        nav=fund.nav,
        amount=amount
    )

    # Update portfolio
    portfolio.units -= units
    if portfolio.units == 0:
        db.session.delete(portfolio)

    db.session.add(transaction)
    db.session.commit()

    return jsonify({'status': 'success', 'amount': amount})

@app.route('/api/create-sip', methods=['POST'])
@login_required
def create_sip():
    data = request.get_json()
    fund_id = data.get('fund_id')
    amount = float(data.get('amount'))
    sip_date = int(data.get('sip_date'))

    fund = MutualFund.query.get_or_404(fund_id)

    if amount < fund.min_investment:
        return jsonify({'error': f'Minimum SIP amount is ₹{fund.min_investment}'}), 400

    # Create SIP record (implement SIP model and logic)
    # For now, return success
    return jsonify({'status': 'success'})


with app.app_context():
    init_mock_data()