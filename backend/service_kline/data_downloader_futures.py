import logging
from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
import time
import datetime as dt
import platform
from datetime import datetime
import json
import threading
from clickhouse_mgr import ClickHouseManager

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.ws_client = None
        self.is_running = False
        self.reconnect_count = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        self.last_connected_at = None
        self.connection_timeout = 24 * 60 * 60  # 24 hours in seconds

        self.clickhouse = ClickHouseManager(
            batch_size=100,  # Adjust based on your needs
            flush_interval=5,  # Flush every 60 seconds
            max_retries=3,  # Maximum retry attempts
            retry_delay=5  # Seconds between retries
        )

    def message_handler(self, _, message):
        try:
            if not isinstance(message, str):
                raise Exception(f'message is not a str: {message}')
            return

            if 'e' in message:
                event_type = message['e']

                if event_type == 'aggTrade':
                    print("\n===== 归集成交信息 =====")
                    print(f"事件类型: {message['e']}")
                    print(f"事件时间: {datetime.fromtimestamp(message['E'] / 1000)}")
                    print(f"交易对: {message['s']}")
                    print(f"归集成交ID: {message['a']}")
                    print(f"成交价格: {message['p']}")
                    print(f"成交数量: {message['q']}")
                    print(f"首个成交ID: {message['f']}")
                    print(f"末个成交ID: {message['l']}")
                    print(f"成交时间: {datetime.fromtimestamp(message['T'] / 1000)}")
                    print(f"是否为主动卖出: {message['m']}")
                    # from latest documentation: ignore 'M'
                    # print(f"是否为交易市场最优价格: {message.get('M', 'N/A')}")
                    self.clickhouse.insert_trade(message)

                elif event_type == 'markPriceUpdate':
                    print("\n===== 标记价格更新 =====")
                    print(f"事件类型: {message['e']}")
                    print(f"事件时间: {datetime.fromtimestamp(message['E'] / 1000)}")
                    print(f"交易对: {message['s']}")
                    print(f"标记价格: {message['p']}")
                    print(f"预估结算价: {message['i']}")
                    print(f"资金费率: {message['r']}")
                    print(f"下次资金费率时间: {datetime.fromtimestamp(message['T'] / 1000)}")

                elif event_type == 'kline':
                    k = message['k']
                    print("\n===== K线数据 =====")
                    print(f"事件类型: {message['e']}")
                    print(f"事件时间: {datetime.fromtimestamp(message['E'] / 1000)}")
                    print(f"交易对: {message['s']}")
                    print(f"K线开始时间: {datetime.fromtimestamp(k['t'] / 1000)}")
                    print(f"K线结束时间: {datetime.fromtimestamp(k['T'] / 1000)}")
                    print(f"交易对: {k['s']}")
                    print(f"时间间隔: {k['i']}")
                    print(f"第一笔成交ID: {k['f']}")
                    print(f"最后一笔成交ID: {k['L']}")
                    print(f"开盘价: {k['o']}")
                    print(f"收盘价: {k['c']}")
                    print(f"最高价: {k['h']}")
                    print(f"最低价: {k['l']}")
                    print(f"成交量: {k['v']}")
                    print(f"成交笔数: {k['n']}")
                    print(f"是否已完结: {k['x']}")
                    print(f"成交额: {k['q']}")
                    print(f"主动买入成交量: {k['V']}")
                    print(f"主动买入成交额: {k['Q']}")

                elif event_type == 'depthUpdate':
                    print("\n===== 深度信息更新 =====")
                    print(f"事件类型: {message['e']}")
                    print(f"事件时间: {datetime.fromtimestamp(message['E'] / 1000)}")
                    print(f"交易对: {message['s']}")
                    print(f"第一个更新ID: {message['U']}")
                    print(f"最后一个更新ID: {message['u']}")
                    print(f"最新更新ID: {message['pu']}")
                    print("\n买盘更新:")
                    for bid in message['b'][:5]:  # 只显示前5个变化
                        print(f"价格: {bid[0]}, 数量: {bid[1]}")
                    print("\n卖盘更新:")
                    for ask in message['a'][:5]:  # 只显示前5个变化
                        print(f"价格: {ask[0]}, 数量: {ask[1]}")

                elif event_type == 'bookTicker':
                    print("\n===== 最优挂单信息 =====")
                    print(f"事件类型: {message['e']}")
                    print(f"更新ID: {message['u']}")
                    print(f"交易对: {message['s']}")
                    print(f"最优买价: {message['b']}")
                    print(f"最优买量: {message['B']}")
                    print(f"最优卖价: {message['a']}")
                    print(f"最优卖量: {message['A']}")

                elif event_type == 'continuous_kline':
                    k = message['k']
                    print("\n===== 连续合约K线数据 =====")
                    print(f"事件类型: {message['e']}")
                    print(f"事件时间: {datetime.fromtimestamp(message['E'] / 1000)}")
                    print(f"交易对: {message['ps']}")
                    print(f"合约类型: {message['ct']}")
                    print(f"K线开始时间: {datetime.fromtimestamp(k['t'] / 1000)}")
                    print(f"K线结束时间: {datetime.fromtimestamp(k['T'] / 1000)}")
                    print(f"时间间隔: {k['i']}")
                    print(f"开盘价: {k['o']}")
                    print(f"收盘价: {k['c']}")
                    print(f"最高价: {k['h']}")
                    print(f"最低价: {k['l']}")
                    print(f"成交量: {k['v']}")
                    print(f"成交额: {k['q']}")

                elif event_type == '24hrMiniTicker':
                    print("\n===== 24小时迷你Ticker =====")
                    print(f"事件类型: {message['e']}")
                    print(f"事件时间: {datetime.fromtimestamp(message['E'] / 1000)}")
                    print(f"交易对: {message['s']}")
                    print(f"收盘价: {message['c']}")
                    print(f"开盘价: {message['o']}")
                    print(f"最高价: {message['h']}")
                    print(f"最低价: {message['l']}")
                    print(f"成交量: {message['v']}")
                    print(f"成交额: {message['q']}")

                elif event_type == '24hrTicker':
                    print("\n===== 24小时完整Ticker =====")
                    print(f"事件类型: {message['e']}")
                    print(f"事件时间: {datetime.fromtimestamp(message['E'] / 1000)}")
                    print(f"交易对: {message['s']}")
                    print(f"价格变化: {message['p']}")
                    print(f"价格变化百分比: {message['P']}")
                    print(f"加权平均价: {message['w']}")
                    print(f"最新价格: {message['c']}")
                    print(f"最新成交量: {message['Q']}")
                    print(f"最高价: {message['h']}")
                    print(f"最低价: {message['l']}")
                    print(f"24小时成交量: {message['v']}")
                    print(f"24小时成交额: {message['q']}")
                    print(f"开盘价: {message['o']}")
                    print(f"统计开始时间: {datetime.fromtimestamp(message['O'] / 1000)}")
                    print(f"统计结束时间: {datetime.fromtimestamp(message['C'] / 1000)}")
                    print(f"首笔成交ID: {message['F']}")
                    print(f"末笔成交ID: {message['L']}")
                    print(f"成交笔数: {message['n']}")

                elif event_type == 'liquidationOrder':
                    print("\n===== 强平订单 =====")
                    print(f"事件类型: {message['e']}")
                    print(f"事件时间: {datetime.fromtimestamp(message['E'] / 1000)}")
                    print(f"交易对: {message['o']['s']}")
                    print(f"订单价格: {message['o']['p']}")
                    print(f"订单数量: {message['o']['q']}")
                    print(f"订单方向: {message['o']['S']}")
                    print(f"订单类型: {message['o']['o']}")
                    print(f"强平类型: {message['o']['f']}")
                    print(f"成交时间: {datetime.fromtimestamp(message['o']['T'] / 1000)}")

                elif event_type == 'compositeIndex':
                    print("\n===== 综合指数更新 =====")
                    print(f"事件类型: {message['e']}")
                    print(f"事件时间: {datetime.fromtimestamp(message['E'] / 1000)}")
                    print(f"交易对: {message['s']}")
                    print(f"指数价格: {message['p']}")

                else:
                    print(f"\n===== 其他事件: {event_type} =====")
                    print(json.dumps(message, indent=2))

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Raw message: {message}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.error(f"Message content: {message}")

    def setup_subscriptions(self):
        symbol = 'btcusdt'

        # 订阅全部市场数据流
        # # 1. K线数据
        # ws_client.kline(
        #     symbol=symbol,
        #     id=1,
        #     interval='1m'  # 可选: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
        # )

        # # 2. 标记价格
        # ws_client.mark_price(
        #     symbol=symbol,
        #     id=2,
        #     speed=1000  # 1000ms或100ms
        # )

        # # 3. 深度信息
        # ws_client.diff_book_depth(
        #     symbol=symbol,
        #     id=3,
        #     speed=500  # 100ms或500ms
        # )

        # 4. 归集交易
        self.ws_client.agg_trade(
            symbol=symbol,
            id=4
        )

        # # 5. 最优挂单信息
        # ws_client.book_ticker(
        #     symbol=symbol,
        #     id=5
        # )

        # # 6. 连续合约K线
        # ws_client.continuous_kline(
        #     pair=symbol,
        #     id=6,
        #     contractType='PERPETUAL',  # 可选: PERPETUAL, CURRENT_QUARTER, NEXT_QUARTER
        #     interval='1m'
        # )
        #
        # # 7. 24小时迷你Ticker
        # ws_client.mini_ticker(
        #     id=7,
        #     symbol=symbol
        # )
        #
        # # 8. 24小时完整Ticker
        # ws_client.ticker(
        #     id=8,
        #     symbol=symbol
        # )

        # # 9. 全市场强平订单
        # ws_client.liquidation_order(
        #     id=9,
        #     symbol=symbol,
        # )
        #
        # # 10. 综合指数
        # ws_client.composite_index(
        #     id=10,
        #     symbol=symbol
        # )

    def connection_monitor(self):
        while self.is_running:
            current_time = time.time()

            # Check if connection is too old (near 24h limit)
            if current_time - self.last_connected_at > self.connection_timeout - 1 * 60 * 60:  # 1 hour earlier
                logger.info("Connection age will surpass 24h limit, initiating reconnect...")
                self.reconnect()

            time.sleep(30)  # Check every 30 seconds

    def reconnect(self):
        if self.reconnect_count >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached. Stopping...")
            self.stop()
            return

        logger.info(f"Attempting reconnection... (Attempt {self.reconnect_count + 1})")
        try:
            if self.ws_client:
                self.ws_client.stop()

            time.sleep(self.reconnect_delay)
            self.start_websocket()
            self.reconnect_count = 0
            logger.info("Reconnection successful")
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            self.reconnect_count += 1
            if self.reconnect_count < self.max_reconnect_attempts:
                time.sleep(self.reconnect_delay)
                self.reconnect()

    def get_client_kwargs(self):
        kwargs = {
            'stream_url': "wss://fstream.binance.com",
            'on_message': self.message_handler,
        }

        # Only add proxy if running on MacOS
        if platform.system() == 'Darwin':  # Darwin is the system name for MacOS
            kwargs['proxies'] = {
                'http': 'http://127.0.0.1:59527',
                'https': 'http://127.0.0.1:59527'
            }
            logger.info("Running on MacOS - Using proxy settings")
        else:
            logger.info(f"Running on {platform.system()} - No proxy needed")

        return kwargs

    def start_websocket(self):
        try:
            # Get kwargs based on operating system
            client_kwargs = self.get_client_kwargs()

            # Initialize websocket client with appropriate settings
            self.ws_client = UMFuturesWebsocketClient(**client_kwargs)

            # Rest of your existing start_websocket code...
            self.setup_subscriptions()
            self.is_running = True
            self.last_connected_at = time.time()

            # Start connection monitor in a separate thread
            monitor_thread = threading.Thread(target=self.connection_monitor)
            monitor_thread.daemon = True
            monitor_thread.start()

            logger.info("WebSocket subscriptions completed")

        except Exception as e:
            logger.error(f"WebSocket setup error: {e}")
            raise

    def stop(self):
        self.is_running = False
        if self.ws_client:
            self.ws_client.stop()
        logger.info("WebSocket connection stopped")
        logger.info('shutting down click house manager')
        self.clickhouse.shutdown()

def main():
    ws_manager = WebSocketManager()
    try:
        logger.info("Starting WebSocket connection...")
        ws_manager.start_websocket()

        while ws_manager.is_running:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received...")
        ws_manager.stop()
    except Exception as e:
        logger.error(f"Main program error: {e}")
    finally:
        ws_manager.stop()
        logger.info("Program terminated")

if __name__ == "__main__":
    main()