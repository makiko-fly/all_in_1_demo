import sys
import os
import random
import datetime as dt
from flask import Flask, request, jsonify
import requests
from flask_cors import CORS

from helper_binance import scanner


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # This enables CORS for all routes

LAST_RETURNED_DF_1 = None
PREV_ACCESS_TIME = None
@app.route('/crypto/24hr_stats', methods=['GET'])
def crypto_24_hour_stats():
    global LAST_RETURNED_DF_1, PREV_ACCESS_TIME
    ret_df = None
    if LAST_RETURNED_DF_1 is not None:
        cache_seconds = 120
        if (dt.datetime.now() - PREV_ACCESS_TIME).seconds < cache_seconds:
            print(f'less than {cache_seconds} seconds passed, use old df')
            ret_df = LAST_RETURNED_DF_1
    if ret_df is None:
        ret_df = scanner.get_latest_snapshot()
        LAST_RETURNED_DF_1 = ret_df
        PREV_ACCESS_TIME = dt.datetime.now()
    return ret_df.to_json(orient='records'), 200


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200



if __name__ == '__main__':
    print('=====')
    app.run(host='0.0.0.0', port=8080)
