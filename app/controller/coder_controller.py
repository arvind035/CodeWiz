from flask import Blueprint
from flask import Flask, render_template, request, jsonify
from app.services.coder_service import Coder

coder_bp = Blueprint("coder", __name__)

# Create a single instance of
single_instance_of_coder_service = Coder()


@coder_bp.route("/code", methods=["POST"])
def coder_controller():
    req_body = request.get_json()
    print('req_body', req_body)
    question = req_body.get("question")
    user_input_language = req_body.get("user_input_language", "python")  # Default to 'python' if not provided

    if not question and not user_input_language:
        return jsonify({"error": "Missing question or language in request body"}), 400
    data = single_instance_of_coder_service.coder(question, user_input_language)

    return jsonify({'message':"Successfully fetch data",'data':data}), 200