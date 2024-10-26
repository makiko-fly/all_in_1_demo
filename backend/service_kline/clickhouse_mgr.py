from clickhouse_driver import Client
import logging
from datetime import datetime
import threading
import time
from typing import List, Dict, Any
import queue
import pytz

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClickHouseManager:
    def __init__(self,
                 batch_size,
                 flush_interval,
                 max_retries,
                 retry_delay):

        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timezone = pytz.timezone('Asia/Singapore')

        # Initialize connection parameters
        self.connection_params = {
            'host': 'localhost',
            'port': 9000,
            'database': 'default',
            # 'user': 'default',
            # 'password': 'your_password',
            'settings': {
                'timezone': 'Asia/Singapore'  # Set timezone for connection
            }
        }

        # Initialize buffers and synchronization
        self.buffer: List[Dict[str, Any]] = []
        self.buffer_lock = threading.Lock()
        self.error_queue = queue.Queue()

        # Initialize connection
        self.client = self._create_client()

        # Create database and tables
        self._setup_database()
        self._setup_tables()

        # Start background tasks
        self._start_background_tasks()

    def _create_client(self) -> Client:
        """Create a new ClickHouse client connection"""
        try:
            return Client(**self.connection_params)
        except Exception as e:
            logger.error(f"Failed to create ClickHouse client: {e}")
            raise

    def _setup_database(self):
        """Create database if it doesn't exist"""
        try:
            # Create database if not exists
            self.client.execute(
                'CREATE DATABASE IF NOT EXISTS crypto_data'
            )
            logger.info("Database setup completed")
        except Exception as e:
            logger.error(f"Database setup failed: {e}")
            raise

    def _setup_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            # Create aggTrades table with timezone specification
            self.client.execute('''
                CREATE TABLE IF NOT EXISTS crypto_data.aggTrades (
                    event_type String,
                    event_time DateTime64(3, 'Asia/Singapore'),
                    symbol String,
                    agg_trade_id Int64,
                    price Float64,
                    quantity Float64,
                    first_trade_id Int64,
                    last_trade_id Int64,
                    trade_time DateTime64(3, 'Asia/Singapore'),
                    is_buyer_maker Bool,
                    insert_time DateTime64(3, 'Asia/Singapore') DEFAULT now64(3)
                ) ENGINE = MergeTree()
                ORDER BY (event_time, symbol)
                PARTITION BY toYYYYMMDD(event_time)
                SETTINGS index_granularity = 8192
            ''')

            logger.info("Table setup completed")
        except Exception as e:
            logger.error(f"Table setup failed: {e}")
            raise

    def _start_background_tasks(self):
        """Start background tasks for periodic flushing and error handling"""
        # Start periodic flush thread
        self.is_running = True
        self.flush_thread = threading.Thread(target=self._periodic_flush)
        self.flush_thread.daemon = True
        self.flush_thread.start()

        # Start error handling thread
        self.error_thread = threading.Thread(target=self._handle_errors)
        self.error_thread.daemon = True
        self.error_thread.start()

    def _periodic_flush(self):
        """Periodically flush the buffer"""
        while self.is_running:
            time.sleep(self.flush_interval)
            self.flush_buffer()

    def _handle_errors(self):
        """Handle errors from the error queue"""
        while self.is_running:
            try:
                error_data = self.error_queue.get(timeout=1)
                if error_data:
                    logger.error(f"Failed data: {error_data}")
                    # Here you could implement additional error handling
                    # such as writing to a dead letter queue or retry logic
            except queue.Empty:
                continue

    def _convert_timestamp_to_datetime(self, timestamp_ms: int) -> datetime:
        """Convert millisecond timestamp to datetime with UTC+8"""
        return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=self.timezone)

    def insert_trade(self, trade_data: Dict[str, Any]):
        """Insert a single trade into the buffer"""
        try:
            # Convert timestamps with timezone
            event_time = self._convert_timestamp_to_datetime(trade_data['E'])
            trade_time = self._convert_timestamp_to_datetime(trade_data['T'])

            # Prepare data
            data = {
                'event_type': trade_data['e'],
                'event_time': event_time,
                'symbol': trade_data['s'],
                'agg_trade_id': int(trade_data['a']),
                'price': float(trade_data['p']),
                'quantity': float(trade_data['q']),
                'first_trade_id': int(trade_data['f']),
                'last_trade_id': int(trade_data['l']),
                'trade_time': trade_time,
                'is_buyer_maker': bool(trade_data['m'])
            }

            # Add to buffer thread-safely
            with self.buffer_lock:
                self.buffer.append(data)

                # Flush if batch size reached
                if len(self.buffer) >= self.batch_size:
                    self.flush_buffer()

        except Exception as e:
            logger.error(f"Error preparing trade data: {e}")
            self.error_queue.put(trade_data)

    def flush_buffer(self):
        """Flush the current buffer to ClickHouse"""
        with self.buffer_lock:
            if not self.buffer:
                return

            local_buffer = self.buffer.copy()
            self.buffer = []

        retry_count = 0
        while retry_count < self.max_retries:
            try:
                self.client.execute(
                    '''
                    INSERT INTO crypto_data.aggTrades (
                        event_type, event_time, symbol, agg_trade_id,
                        price, quantity, first_trade_id, last_trade_id,
                        trade_time, is_buyer_maker
                    ) VALUES
                    ''',
                    local_buffer
                )
                logger.info(f"== Successfully inserted {len(local_buffer)} records")
                break

            except Exception as e:
                retry_count += 1
                logger.error(f"Insert attempt {retry_count} failed: {e}")

                if retry_count >= self.max_retries:
                    logger.error("Max retries reached, adding to error queue")
                    for record in local_buffer:
                        self.error_queue.put(record)
                    break

                time.sleep(self.retry_delay)

    def shutdown(self):
        """Gracefully shutdown the manager"""
        self.is_running = False
        self.flush_buffer()  # Final flush
        if hasattr(self, 'client'):
            self.client.disconnect()
        logger.info("ClickHouseManager shutdown complete")

    def __del__(self):
        """Destructor to ensure clean shutdown"""
        try:
            self.shutdown()
        except:
            pass