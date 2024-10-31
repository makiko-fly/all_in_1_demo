import json
import websocket
import time
import threading
from loguru import logger
from redis_stream_mgr import RedisStreamManager

class AllTickClient:
    def __init__(self, token, market_type="stock"):
        """
        Initialize AllTick WebSocket client

        Args:
            token (str): Your AllTick API token
            market_type (str): "stock", "forex", or "crypto"
        """
        self.token = token
        self.base_url = "wss://quote.tradeswitcher.com"
        self.endpoint = f"/quote-stock-b-ws-api" if market_type == "stock" else "/quote-b-ws-api"
        self.ws = None
        self.subscriptions = set()
        self.is_connected = False
        self.heartbeat_interval = 15  # seconds
        self.redis_mgr = RedisStreamManager(host='localhost', port=6379, stream_name='cn_stock', max_size=2000)

    def _get_ws_url(self):
        """Construct WebSocket URL with token"""
        return f"{self.base_url}{self.endpoint}?token={self.token}"

    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            # logger.debug(f"Received message: {data}")

            # Handle different message types
            if "cmd_id" in data:
                if data["cmd_id"] == 22003:  # Subscription response
                    logger.info("Subscription successful")
                elif data["cmd_id"] == 20003:  # Heartbeat response
                    logger.debug("Heartbeat acknowledged")
                else:
                    logger.info(f"Market data received: {data}")
                    self.redis_mgr.write_record(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")

    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection closure"""
        self.is_connected = False
        logger.info(f"WebSocket connection closed: {close_msg} ({close_status_code})")
        # self._reconnect()

    def _on_open(self, ws):
        """Handle WebSocket connection opening"""
        self.is_connected = True
        logger.info("WebSocket connection established")

        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()

        # Resubscribe to previous subscriptions
        self._resubscribe()

    def _heartbeat_loop(self):
        """Send periodic heartbeat messages"""
        while self.is_connected:
            try:
                heartbeat_msg = {
                    "cmd_id": 20002,
                    "seq_id": int(time.time()),
                    "data": {}
                }
                self.ws.send(json.dumps(heartbeat_msg))
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    def _reconnect(self):
        """Handle reconnection logic"""
        if not self.is_connected:
            logger.info("Attempting to reconnect...")
            time.sleep(5)  # Wait before reconnecting
            self.connect()

    def _resubscribe(self):
        """Resubscribe to previously subscribed symbols"""
        if self.subscriptions:
            self.subscribe(list(self.subscriptions))

    def connect(self):
        """Establish WebSocket connection"""
        self.ws = websocket.WebSocketApp(
            self._get_ws_url(),
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )

        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()

    def subscribe(self, symbols, depth_level=5):
        """
        Subscribe to market data for specified symbols

        Args:
            symbols (list): List of symbol codes (e.g., ["700.HK", "AAPL.US"])
            depth_level (int): Order book depth level (default: 5)
        """
        if not self.is_connected:
            logger.error("Not connected. Please connect first.")
            return

        symbol_list = [{"code": symbol, "depth_level": depth_level} for symbol in symbols]

        subscribe_msg = {
            "cmd_id": 22002,
            "seq_id": int(time.time()),
            "trace": f"sub-{time.time()}",
            "data": {
                "symbol_list": symbol_list
            }
        }

        try:
            self.ws.send(json.dumps(subscribe_msg))
            self.subscriptions.update(symbols)
            logger.info(f"Subscribed to symbols: {symbols}")
        except Exception as e:
            logger.error(f"Subscription error: {e}")

    def unsubscribe(self, symbols):
        """
        Unsubscribe from market data for specified symbols

        Args:
            symbols (list): List of symbol codes to unsubscribe from
        """
        if not self.is_connected:
            logger.error("Not connected. Please connect first.")
            return

        unsubscribe_msg = {
            "cmd_id": 22004,
            "seq_id": int(time.time()),
            "trace": f"unsub-{time.time()}",
            "data": {
                "symbol_list": symbols
            }
        }

        try:
            self.ws.send(json.dumps(unsubscribe_msg))
            self.subscriptions.difference_update(symbols)
            logger.info(f"Unsubscribed from symbols: {symbols}")
        except Exception as e:
            logger.error(f"Unsubscription error: {e}")

    def disconnect(self):
        """Close WebSocket connection"""
        if self.is_connected:
            self.ws.close()
            self.is_connected = False
            logger.info("WebSocket connection closed")


def main():
    # Replace with your actual API token from AllTick
    api_token = "4ab4cb16d95e98a959db82ae5a6f6cd3-c-app"

    # Create client instance
    client = AllTickClient(token=api_token, market_type="stock")

    try:
        # Connect to WebSocket
        client.connect()

        # Wait for connection to establish
        time.sleep(2)

        # Subscribe to some symbols
        symbols = ["600519.SH", "300750.SZ", "300059.SZ", "002352.SZ"]
        client.subscribe(symbols)

        # Keep the main thread running
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("\nReceived keyboard interrupt. Closing connection...")
                client.disconnect()
                break

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        client.disconnect()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Program terminated with error: {e}")