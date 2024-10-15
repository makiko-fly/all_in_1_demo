import atexit
from flask import Flask, request, jsonify
import jwt
import datetime
import bcrypt
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.service_registry import ServiceRegistry
from dao.models import Base, User
from dao.dao_user import UserDAO

app = Flask(__name__)

# Database configuration
db_url = (f"mysql+mysqlconnector://{os.environ['MYSQL_USER']}:{os.environ['MYSQL_PASSWORD']}@"
          f"{os.environ['MYSQL_HOST']}/{os.environ['MYSQL_DATABASE']}")
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)

registry = ServiceRegistry(redis_host='redis', redis_port=6379)

SECRET_KEY = "tmp_secret_key"

# Create a new UserDAO instance with the Session
user_dao = UserDAO(Session)


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    existing_user = user_dao.get_user_by_username(username)
    if existing_user:
        return jsonify({"error": "Username already exists"}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user_dao.create_user(username, hashed_password.decode('utf-8'))

    return jsonify({"message": "User registered successfully"}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = user_dao.get_user_by_username(username)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        token = jwt.encode({
            'user': username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, SECRET_KEY, algorithm='HS256')
        return jsonify({"token": token})

    return jsonify({"error": "Invalid credentials"}), 401


@app.route('/users', methods=['GET'])
def list_users():
    users = user_dao.get_all_users()
    user_list = [
        {
            "id": user.id,
            "username": user.username,
        }
        for user in users
    ]
    return jsonify(user_list), 200


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    instance_id = registry.register('service_auth', 'service_auth', 5001)
    atexit.register(registry.deregister, 'service_auth', instance_id)

    # Create all tables
    Base.metadata.create_all(engine)

    app.run(host='0.0.0.0', port=5001)