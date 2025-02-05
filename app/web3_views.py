# app/web3_views.py
from flask import Blueprint, request, render_template, jsonify, current_app
import logging
from .services.web3_service import Web3Service
import redis
import json

web3_blueprint = Blueprint("web3", __name__)
redis_client = redis.Redis(host="localhost", port=6379, db=0)
web3_service = Web3Service(redis_client)


@web3_blueprint.route("/sign/<session_id>")
def sign_page(session_id):
    """Render signing page"""
    session_data = web3_service.get_session(session_id)
    if not session_data:
        return "Invalid or expired session", 404

    return render_template("sign.html", session_id=session_id)


@web3_blueprint.route("/api/store-signature", methods=["POST"])
def store_signature():
    """Handle signature storage"""
    try:
        data = request.json
        session_id = data.get("session_id")
        signature = data.get("signature")
        address = data.get("address")

        session_data = web3_service.get_session(session_id)
        if not session_data:
            return jsonify({"error": "Invalid session"}), 404

        # Verify the signature
        message = json.dumps(
            {
                "session_id": session_id,
                "timestamp": session_data.get("created_at"),
                "action": "sign_loi",
            }
        )

        if not web3_service.verify_signature(message, signature, address):
            return jsonify({"error": "Invalid signature"}), 400

        # Update session with verified data
        success = web3_service.update_session(
            session_id,
            {"eth_address": address, "signature": signature, "status": "signed"},
        )

        if not success:
            return jsonify({"error": "Failed to update session"}), 500

        # Generate WhatsApp redirect URL
        whatsapp_url = f"https://wa.me/{session_data['whatsapp_number']}"

        return jsonify({"success": True, "redirect_url": whatsapp_url})

    except Exception as e:
        logging.error(f"Error in store_signature: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
