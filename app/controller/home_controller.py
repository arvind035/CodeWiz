from flask import Blueprint
from flask import Flask, render_template, request, jsonify

home_bp = Blueprint("home", __name__)

# Create a single instance of 


@home_bp.route("/home", methods=["GET"])
def index():
    return render_template('homepage.html')