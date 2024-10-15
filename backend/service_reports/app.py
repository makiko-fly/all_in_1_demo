import atexit
from flask import Flask, jsonify
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.service_registry import ServiceRegistry

app = Flask(__name__)
registry = ServiceRegistry(redis_host='redis', redis_port=6379)

@app.route('/hello', methods=['GET'])
def hello():
    return jsonify({"message": "Hello from Service Reports!"})

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    instance_id = registry.register('service_reports', 'service_reports', 5002)
    atexit.register(registry.deregister, 'service_reports', instance_id)
    app.run(host='0.0.0.0', port=5002)
