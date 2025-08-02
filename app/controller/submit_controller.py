from flask import Blueprint
from flask import Flask, render_template, request, jsonify
from app.services.submit_service import SubmitService
from threading import Thread

submit_bp = Blueprint("submit", __name__)

single_instance_of_submit_service = SubmitService()

@submit_bp.route("/submit", methods=["POST"])
def submit_controller():
    try:
        req_body = request.get_json()
        if not req_body or ("user_input_link" or "req_type") not in req_body:
            return jsonify({"error": "Missing user_input_link or req_type in request body"}), 400

        user_input_link = req_body["user_input_link"]
        req_type = req_body["req_type"]
        user_input_language = req_body.get("user_input_language", "software")  # Default to 'python' if not provided

        hash_key, is_exist = single_instance_of_submit_service.create_hash(user_input_link, req_type)

        if is_exist:
            return jsonify({"message": "This request is already in progress.", "key": hash_key}), 200

        # Create a thread for the function
        t = Thread(
            target=single_instance_of_submit_service.submit,
            args=(user_input_link, req_type, user_input_language, hash_key),
            daemon=True  # Mark it as a daemon thread
        )
        t.start()


        return {"message":"We have started your process. Please wait for few minutes. We will update all the content in the dashbaord.","key":hash_key}
    except Exception as e:
        return jsonify({"error": str(e)}), 500