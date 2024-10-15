import sys
import os
import random
from flask import Flask, request, jsonify
import requests
import jwt

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.service_registry import ServiceRegistry

app = Flask(__name__)
registry = ServiceRegistry()

def get_service_url(service_name):
    services = registry.get_service(service_name)
    if services:
        service = random.choice(services)  # Simple round-robin load balancing
        return f"http://{service['host']}:{service['port']}"
    return None

SECRET_KEY = "tmp_secret_key"  # Same as in auth_service

def token_required(f):
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except:
            return jsonify({"error": "Token is invalid"}), 401
        return f(*args, **kwargs)
    return decorated


@app.route('/register', methods=['POST'])
def register():
    service_info = registry.get_service('auth_service')
    if not service_info:
        return jsonify({"error": "Auth service not available"}), 503

    auth_url = f"http://{service_info['host']}:{service_info['port']}/register"
    response = requests.post(auth_url, json=request.json)
    return jsonify(response.json()), response.status_code


@app.route('/login', methods=['POST'])
def login():
    service_info = registry.get_service('auth_service')
    if not service_info:
        return jsonify({"error": "Auth service not available"}), 503

    auth_url = f"http://{service_info['host']}:{service_info['port']}/login"
    response = requests.post(auth_url, json=request.json)
    return jsonify(response.json()), response.status_code

@app.route('/service_data/hello', methods=['GET'])
# @token_required
def service_data_route():
    service_url = get_service_url('service_reports')
    if not service_url:
        return jsonify({"error": "Service not found"}), 404
    response = requests.get(f"{service_url}/hello")
    return jsonify(response.json()), response.status_code

@app.route('/hello', methods=['GET'])
def hello():
    return jsonify({"message": "Hello from API gateway 2"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)