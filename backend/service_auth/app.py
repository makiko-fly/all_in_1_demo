import atexit
from flask import Flask, request, jsonify
import jwt
import datetime
import bcrypt
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.common.service_registry import ServiceRegistry

app = Flask(__name__)
registry = ServiceRegistry(redis_host='redis', redis_port=6379)

SECRET_KEY = "tmp_secret_key"
users = {}


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if username in users:
        return jsonify({"error": "Username already exists"}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    users[username] = hashed_password

    return jsonify({"message": "User registered successfully"}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if username not in users:
        return jsonify({"error": "Invalid credentials"}), 401

    if bcrypt.checkpw(password.encode('utf-8'), users[username]):
        token = jwt.encode({
            'user': username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, SECRET_KEY, algorithm='HS256')
        return jsonify({"token": token})

    return jsonify({"error": "Invalid credentials"}), 401


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    instance_id = registry.register('auth_service', 'auth_service', 5001)
    atexit.register(registry.deregister, 'auth_service', instance_id)
    app.run(host='0.0.0.0', port=5001)