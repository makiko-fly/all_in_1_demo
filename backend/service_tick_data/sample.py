import websocket
import json
import threading
import time


class AllTickWebSocket:
    def __init__(self, api_key):
        self.ws = None
        self.api_key = api_key
        self.symbols = ["EURUSD", "GBPUSD", "USDJPY"]  # Add more forex pairs as needed

    def on_message(self, ws, message):
        # Parse and handle incoming tick data
        try:
            tick = json.loads(message)
            print(f"Tick: {tick}")
        except json.JSONDecodeError:
            print(f"Failed to parse message: {message}")

    def on_error(self, ws, error):
        print(f"Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket connection closed")

    def on_open(self, ws):
        print("WebSocket connection established")
        # Subscribe to forex symbols
        for symbol in self.symbols:
            subscribe_message = {
                "type": "subscribe",
                "symbol": symbol,
                "api_key": self.api_key
            }
            ws.send(json.dumps(subscribe_message))

    def keep_alive(self):
        while True:
            try:
                self.ws.send(json.dumps({"type": "ping"}))
            except:
                break
            time.sleep(30)

    def connect(self):
        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(
            f"wss://quote.tradeswitcher.com/quote-b-ws-api?token={self.api_key}",  # Replace with actual WebSocket URL
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )

        # Start keep-alive thread
        keep_alive_thread = threading.Thread(target=self.keep_alive)
        keep_alive_thread.daemon = True
        keep_alive_thread.start()

        # Start WebSocket connection
        self.ws.run_forever()

    def disconnect(self):
        if self.ws:
            self.ws.close()


def main():
    api_key = "4ab4cb16d95e98a959db82ae5a6f6cd3-c-app"
    client = AllTickWebSocket(api_key)

    try:
        client.connect()
    except KeyboardInterrupt:
        print("Stopping...")
        client.disconnect()


if __name__ == "__main__":
    main()