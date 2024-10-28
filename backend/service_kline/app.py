import sys
import os
import random
import datetime as dt
from flask import Flask, request, jsonify
import requests
from flask_cors import CORS
from functools import wraps
from common_clickhouse import ClickHouseReader

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})  # This enables CORS for all routes

# # Only use the Flask-CORS extension configuration
# CORS(app, resources={
#     r"/*": {
#         "origins": ["http://127.0.0.1", "http://localhost", "http://127.0.0.1:5500"],
#         "methods": ["GET", "POST", "OPTIONS"],
#         "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
#         "supports_credentials": True
#     }
# })

cache_store = {}

# Rest of your code remains the same...
def cache(seconds=5):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            if cache_key in cache_store:
                result, timestamp = cache_store[cache_key]
                time_diff = (dt.datetime.now() - timestamp).seconds
                if time_diff < seconds:
                    print(f'Cache hit for {func.__name__}: less than {seconds} seconds passed')
                    return result
            result = func(*args, **kwargs)
            cache_store[cache_key] = (result, dt.datetime.now())
            return result
        return wrapper
    return decorator

@app.route('/crypto/24hr_stats', methods=['GET'])
@cache(seconds=10)
def crypto_24_hour_stats():
    from helper_binance import scanner
    ret_df = scanner.get_latest_snapshot()
    return ret_df.to_json(orient='records'), 200

reader = ClickHouseReader()

@app.route('/crypto/latest_agg_trades', methods=['GET'])
@cache(seconds=8)
def latest_agg_trades():
    trades = reader.get_agg_trades('BTCUSDT', 100)
    return jsonify(trades), 200

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)