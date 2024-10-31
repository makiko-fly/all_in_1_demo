import sys
import os
import random
import datetime as dt
from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps
from click_house_mgr import ClickHouseMgr
import common


app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})  # This enables CORS for all routes

# tmp solution, in production env please use prod.yaml and dev.yaml
ch_host = 'localhost'
if common.is_service_reachable('clickhouse-markets', 9000):
    ch_host = 'clickhouse-markets'

clickhouse_config = {
        'host': ch_host,
        'port': 9000,
        'user': 'default',
        'password': '',
        'database': 'default'
    }
ch_mgr = ClickHouseMgr(**clickhouse_config)


cache_store = {}

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


@app.route('/cn_stock/book', methods=['GET'])
@cache(seconds=4)
def cn_stock_book():
    book_records_df = ch_mgr.get_latest_cn_stock_book(20)
    book_records = book_records_df.to_dict('records')

    stat_records_df = ch_mgr.get_data_distribution()
    stat_records = stat_records_df.to_dict('records')
    ret_obj = {'book': book_records, 'stat': stat_records}
    return jsonify(ret_obj), 200, {'Content-Type': 'application/json'}


@app.route('/cn_stock/ch_stats', methods=['GET'])
@cache(seconds=4)
def cn_stock_ch_stats():
    records = ch_mgr.get_data_distribution()
    records = records.to_dict('records')
    return jsonify(records), 200, {'Content-Type': 'application/json'}


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=8080)
    finally:
        if ch_mgr is not None:
            ch_mgr.close()