# app/services/web3_service.py
from eth_account.messages import encode_defunct
from eth_account import Account
import json
from datetime import datetime, timedelta
from flask import current_app
import logging


class Web3Service:
    def __init__(self, redis_client):
        self.redis = redis_client

    def create_signing_session(self, whatsapp_number, signature_data):
        session_id = Account.create().address
        session_data = {
            "whatsapp_number": whatsapp_number,
            "signature_data": signature_data,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "verified": False,
        }
        self.redis.setex(
            f"loi_session:{session_id}", timedelta(minutes=15), json.dumps(session_data)
        )
        return session_id

    def verify_loi_ownership(self, session_id, user_signature):
        """Verify if user owns the LOI"""
        session_data = self.get_session(session_id)
        if not session_data:
            return False

        original_content = session_data["signature_data"]["text_content"]
        phone_number = session_data["whatsapp_number"]

        # Verify user signature matches original signer
        verification_message = f"{original_content}:{phone_number}"
        return self.verify_signature(
            verification_message,
            user_signature,
            session_data["signature_data"]["signature"],
        )

    def verify_signature(self, message, signature, address):
        """Verify an Ethereum signature"""
        try:
            message_hash = encode_defunct(text=message)
            recovered_address = Account.recover_message(
                message_hash, signature=signature
            )
            return recovered_address.lower() == address.lower()
        except Exception as e:
            logging.error(f"Signature verification error: {str(e)}")
            return False

    def get_session(self, session_id):
        """Get session data from Redis"""
        data = self.redis.get(f"loi_session:{session_id}")
        return json.loads(data) if data else None

    def update_session(self, session_id, updates):
        """Update session data in Redis"""
        data = self.get_session(session_id)
        if data:
            data.update(updates)
            self.redis.setex(
                f"loi_session:{session_id}", timedelta(minutes=15), json.dumps(data)
            )
            return True
        return False
