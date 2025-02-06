import os
import requests
from datetime import datetime
from app import db
from models import KYC

class HyperVergeService:
    def __init__(self):
        self.app_id = os.environ.get('HYPERVERGE_APP_ID', 'dummy_app_id')
        self.app_key = os.environ.get('HYPERVERGE_APP_KEY', 'dummy_app_key')
        self.base_url = 'https://ind-docs.hyperverge.co/v2.0'
        
    def _get_headers(self):
        """Get authentication headers for HyperVerge API"""
        return {
            'appId': self.app_id,
            'appKey': self.app_key,
            'Content-Type': 'application/json'
        }

    def verify_pan(self, pan_number, pan_image):
        """Verify PAN card details"""
        try:
            response = requests.post(
                f"{self.base_url}/readPan",
                headers=self._get_headers(),
                json={'image': pan_image}
            )
            data = response.json()
            if data.get('status') == 'success':
                return True, data.get('result', {})
            return False, data.get('message', 'Verification failed')
        except Exception as e:
            return False, str(e)

    def verify_aadhaar(self, aadhaar_number, aadhaar_front, aadhaar_back):
        """Verify Aadhaar card details"""
        try:
            response = requests.post(
                f"{self.base_url}/readAadhaar",
                headers=self._get_headers(),
                json={
                    'frontImage': aadhaar_front,
                    'backImage': aadhaar_back
                }
            )
            data = response.json()
            if data.get('status') == 'success':
                return True, data.get('result', {})
            return False, data.get('message', 'Verification failed')
        except Exception as e:
            return False, str(e)

    def face_match(self, selfie_image, id_image):
        """Match face with ID proof"""
        try:
            response = requests.post(
                f"{self.base_url}/facematch",
                headers=self._get_headers(),
                json={
                    'image1': selfie_image,
                    'image2': id_image
                }
            )
            data = response.json()
            if data.get('status') == 'success':
                match_score = data.get('result', {}).get('match', 0)
                return match_score > 90, match_score
            return False, data.get('message', 'Face matching failed')
        except Exception as e:
            return False, str(e)

    def verify_bank_account(self, account_number, ifsc_code):
        """Verify bank account details"""
        try:
            response = requests.post(
                f"{self.base_url}/verifyBankAccount",
                headers=self._get_headers(),
                json={
                    'accountNumber': account_number,
                    'ifscCode': ifsc_code
                }
            )
            data = response.json()
            if data.get('status') == 'success':
                return True, data.get('result', {})
            return False, data.get('message', 'Bank verification failed')
        except Exception as e:
            return False, str(e)

class KYCService:
    def __init__(self):
        self.hyperverge = HyperVergeService()

    def start_kyc(self, user_id):
        """Initialize KYC process for a user"""
        kyc = KYC(
            user_id=user_id,
            status='in_progress'
        )
        db.session.add(kyc)
        db.session.commit()
        return kyc

    def update_kyc_status(self, kyc_id, **kwargs):
        """Update KYC verification status"""
        kyc = KYC.query.get(kyc_id)
        if not kyc:
            return False, "KYC record not found"

        for key, value in kwargs.items():
            if hasattr(kyc, key):
                setattr(kyc, key, value)
        
        kyc.updated_at = datetime.utcnow()
        
        # Check if all verifications are complete
        if all([kyc.pan_verified, kyc.aadhaar_verified, kyc.face_verified, kyc.bank_verified]):
            kyc.status = 'completed'
        
        db.session.commit()
        return True, kyc
