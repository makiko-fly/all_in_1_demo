import sys
import os
import datetime as dt
from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps
from common_redis_stream_mgr import RedisStreamManager

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize Redis Stream Manager
redis_manager = RedisStreamManager(
    host='localhost',  # Update with your Redis host
    port=6379,  # Update with your Redis port
    stream_name='trades',
    max_size=10000
)

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


def format_trade(trade):
    # Convert timestamps to datetime and format
    event_time = dt.datetime.fromtimestamp(int(trade['E']) / 1000).strftime("%a, %d %b %Y %H:%M:%S GMT")
    trade_time = dt.datetime.fromtimestamp(int(trade['T']) / 1000).strftime("%a, %d %b %Y %H:%M:%S GMT")

    return {
        "agg_trade_id": int(trade['a']),
        "event_time": event_time,
        "event_type": trade['e'],
        "first_trade_id": int(trade['f']),
        "is_buyer_maker": bool(trade['m']),
        "last_trade_id": int(trade['l']),
        "price": float(trade['p']),
        "quantity": float(trade['q']),
        "symbol": trade['s'],
        "trade_time": trade_time
    }


@app.route('/crypto/24hr_stats', methods=['GET'])
@cache(seconds=10)
def crypto_24_hour_stats():
    from helper_binance import scanner
    ret_df = scanner.get_latest_snapshot()
    return ret_df.to_json(orient='records'), 200


@app.route('/crypto/latest_agg_trades', methods=['GET'])
@cache(seconds=8)
def latest_agg_trades():
    try:
        # Get trades from Redis Stream
        trades_batches = redis_manager.consume_trades(batch_size=100, timeout=1000)

        if not trades_batches:
            return jsonify([]), 200  # Return empty array if no trades

        # Process the trades from Redis
        all_trades = []
        for trades_batch, message_ids in trades_batches:
            formatted_trades = [format_trade(trade) for trade in trades_batch]
            all_trades.extend(formatted_trades)
            # Acknowledge the processed messages
            redis_manager.ack_messages(message_ids)

        return jsonify(all_trades), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    try:
        # Include Redis stream info in health check
        stream_info = redis_manager.get_stream_info()
        return jsonify({
            "status": "healthy",
            "redis_stream": stream_info
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)