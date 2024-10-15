import sys
import os
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import jwt

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # This enables CORS for all routes

from common.service_registry import ServiceRegistry
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

def admin_required(f):
    def wrapper(*args, **kwargs):
        # token = request.headers.get('Authorization')
        # if not token:
        #     return jsonify({'message': 'Token is missing!'}), 401
        # try:
        #     payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        #     # This is a placeholder. You should implement proper admin check logic.
        #     if 'admin' not in payload or not payload['admin']:
        #         return jsonify({'message': 'Admin access required!'}), 403
        # except:
        #     return jsonify({'message': 'Token is invalid!'}), 401
        return f(*args, **kwargs)
    return wrapper

@app.route('/register', methods=['POST'])
def register():
    service_info = registry.get_service('service_auth')
    if not service_info:
        return jsonify({"error": "Auth service not available"}), 503
    service_info = service_info[0]

    auth_url = f"http://{service_info['host']}:{service_info['port']}/register"
    response = requests.post(auth_url, json=request.json)
    return jsonify(response.json()), response.status_code


@app.route('/login', methods=['POST'])
def login():
    service_info = registry.get_service('service_auth')
    if not service_info:
        return jsonify({"error": "Auth service not available"}), 503
    service_info = service_info[0]

    auth_url = f"http://{service_info['host']}:{service_info['port']}/login"
    response = requests.post(auth_url, json=request.json)
    return jsonify(response.json()), response.status_code

@app.route('/users', methods=['GET'])
@admin_required
def list_users():
    auth_service_url = get_service_url('service_auth')
    if not auth_service_url:
        return jsonify({"error": "Auth service not available"}), 503
    response = requests.get(f"{auth_service_url}/users", params=request.args)
    return response.json(), response.status_code


@app.route('/services', methods=['GET'])
def get_services():
    services = ['service_auth', 'service_reports']  # List of known services
    running_services = []

    for service_name in services:
        instances = registry.get_service(service_name)
        if instances:
            for instance in instances:
                service_url = f"http://{instance['host']}:{instance['port']}"
                try:
                    response = requests.get(f"{service_url}/health", timeout=1)
                    if response.status_code == 200:
                        running_services.append({
                            'name': service_name,
                            'status': 'Running',
                            'health': response.json(),
                            'instance_id': instance['id']
                        })
                    else:
                        running_services.append({
                            'name': service_name,
                            'status': 'Unhealthy',
                            'health': None,
                            'instance_id': instance['id']
                        })
                except requests.RequestException:
                    running_services.append({
                        'name': service_name,
                        'status': 'Not Running',
                        'health': None,
                        'instance_id': instance['id']
                    })
        else:
            running_services.append({
                'name': service_name,
                'status': 'Not Registered',
                'health': None,
                'instance_id': None
            })

    return jsonify(running_services)


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)