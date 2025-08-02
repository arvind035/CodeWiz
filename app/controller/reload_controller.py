from flask import Blueprint
from flask import Flask, render_template, request, jsonify
from app.services.reload_service import ReloadService

reload_bp = Blueprint("reload", __name__)

# Create a single instance of 
single_instance_of_reload_service = ReloadService()



@reload_bp.route("/reload", methods=["POST"])
def reload_controller():
    req_body = request.get_json()
    print('req_body', req_body)
    if not req_body or ("user_input_link" or 'req_type') not in req_body:
        return jsonify({"error": "Missing user_input_link or req_type in request body"}), 400
    
    user_input_link = req_body["user_input_link"]
    req_type = req_body["req_type"]

    data = single_instance_of_reload_service.reload(user_input_link, req_type)
    return jsonify(data), 200