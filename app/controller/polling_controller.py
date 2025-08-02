from flask import Blueprint, jsonify, request
from app.services.polling_service import PollingService

polling_bp = Blueprint("polling", __name__)

# Create a single instance of PollingService
single_instance_of_polling_service = PollingService()

@polling_bp.route("/polling", methods=["POST"])
def polling_controller():

    req_body = request.get_json()
    if not req_body or ("user_input_link" or 'req_type') not in req_body:
        return jsonify({"error": "Missing user_input_link or req_type in request body"}), 400
    
    user_input_link = req_body["user_input_link"]
    req_type = req_body["req_type"]

    data = single_instance_of_polling_service.poll(user_input_link, req_type)
    return jsonify(data), 200