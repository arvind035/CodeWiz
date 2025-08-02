from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import psutil


load_dotenv('.env')

from app.controller.home_controller import home_bp
from app.controller.submit_controller import submit_bp
from app.controller.polling_controller import polling_bp;
from app.controller.reload_controller import reload_bp
from app.controller.coder_controller import coder_bp

app = Flask(__name__)

prefix_url = '/flask-api'
app.register_blueprint(home_bp, url_prefix=prefix_url)
app.register_blueprint(submit_bp, url_prefix=prefix_url)
app.register_blueprint(polling_bp, url_prefix=prefix_url)
app.register_blueprint(reload_bp, url_prefix=prefix_url)
app.register_blueprint(coder_bp, url_prefix=prefix_url)


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/flask-api/health')
def health_check():
    return 'OK! CPU - {}, Memory - {}'.format(psutil.cpu_percent(2), psutil.virtual_memory().percent), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)