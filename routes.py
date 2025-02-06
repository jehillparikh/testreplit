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
        admin_user.set_password('dummy')
        db.session.add(admin_user)
        db.session.commit()

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

with app.app_context():
    init_mock_data()