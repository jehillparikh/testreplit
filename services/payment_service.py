import os
import razorpay
from datetime import datetime
from flask import current_app
from app import db
from models import Payment, Transaction, Portfolio

class PaymentService:
    def __init__(self):
        self.client = razorpay.Client(
            auth=(
                os.environ.get('RAZORPAY_KEY_ID', 'dummy_key'),
                os.environ.get('RAZORPAY_KEY_SECRET', 'dummy_secret')
            )
        )

    def create_order(self, user_id: int, amount: float) -> Payment:
        """Create a new payment order"""
        # RazorPay expects amount in paise (1 INR = 100 paise)
        amount_in_paise = int(amount * 100)
        
        order_data = {
            'amount': amount_in_paise,
            'currency': 'INR',
            'payment_capture': 1  # Auto capture payment
        }
        
        razorpay_order = self.client.order.create(data=order_data)
        
        # Create payment record
        payment = Payment(
            user_id=user_id,
            amount=amount,
            razorpay_order_id=razorpay_order['id'],
            status='pending'
        )
        
        db.session.add(payment)
        db.session.commit()
        
        return payment

    def verify_payment(self, payment_id: int, razorpay_payment_id: str, razorpay_signature: str) -> bool:
        """Verify the payment signature"""
        payment = Payment.query.get(payment_id)
        if not payment:
            return False

        # Verify signature
        params_dict = {
            'razorpay_order_id': payment.razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }

        try:
            self.client.utility.verify_payment_signature(params_dict)
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = 'completed'
            payment.completed_at = datetime.utcnow()
            db.session.commit()
            return True
        except Exception:
            payment.status = 'failed'
            db.session.commit()
            return False

    def process_investment(self, payment: Payment, fund_id: int) -> Transaction:
        """Process the mutual fund investment after successful payment"""
        from models import MutualFund
        
        fund = MutualFund.query.get(fund_id)
        if not fund:
            raise ValueError("Invalid fund ID")

        # Calculate units based on current NAV
        units = payment.amount / fund.nav

        # Create transaction record
        transaction = Transaction(
            user_id=payment.user_id,
            fund_id=fund_id,
            transaction_type='BUY',
            units=units,
            nav=fund.nav,
            amount=payment.amount,
            payment_id=payment.id
        )

        # Update or create portfolio
        portfolio = Portfolio.query.filter_by(
            user_id=payment.user_id,
            fund_id=fund_id
        ).first()

        if portfolio:
            portfolio.units += units
        else:
            portfolio = Portfolio(
                user_id=payment.user_id,
                fund_id=fund_id,
                units=units,
                purchase_nav=fund.nav
            )
            db.session.add(portfolio)

        db.session.add(transaction)
        db.session.commit()

        return transaction
