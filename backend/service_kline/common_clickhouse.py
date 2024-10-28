from clickhouse_driver import Client
from datetime import datetime
import threading
import time
from typing import List, Dict, Any
import queue
import pytz
from loguru import logger
from abc import ABC
from common_redis_stream_mgr import RedisStreamManager



class ClickHouseBase(ABC):
    """Base class for ClickHouse operations"""

    def __init__(self, host: str = 'localhost', port: int = 9000,
                 database: str = 'crypto_data', timezone: str = 'Asia/Singapore'):
        self.client = Client(
            host=host,
            port=port,
            database=database,
            settings={'timezone': timezone}
        )
        self.timezone = pytz.timezone(timezone)

    def _convert_timestamp(self, timestamp_ms: int) -> datetime:
        """Convert millisecond timestamp to datetime"""
        return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=self.timezone)

    def shutdown(self):
        """Close the database connection"""
        try:
            self.client.disconnect()
            logger.info(f"{self.__class__.__name__} shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

    def __del__(self):
        """Ensure clean shutdown"""
        self.shutdown()


class ClickHouseWriter(ClickHouseBase):
    def __init__(self, max_retries: int = 3, retry_delay: float = 5,
                 redis_host: str = 'localhost', redis_port: int = 6379,
                 batch_size: int = 100, **kwargs):
        super().__init__(**kwargs)

        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.batch_size = batch_size

        # Initialize Redis Stream Manager
        self.redis_stream = RedisStreamManager(
            host=redis_host,
            port=redis_port
        )

        self.error_queue = queue.Queue()
        self.is_running = True
        self.consumer_thread = None

    def start(self):
        """Start the writer and its consumer thread"""
        self.consumer_thread = threading.Thread(target=self._consume_stream)
        self.consumer_thread.daemon = False
        self.consumer_thread.start()

    def _process_batch(self, trades_batch: List[Dict[str, Any]]) -> bool:
        """
        Process a batch of trades
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            processed_batch = []
            for trade_data in trades_batch:
                try:
                    processed_data = {
                        'event_type': trade_data['e'],
                        'event_time': self._convert_timestamp(trade_data['E']),
                        'symbol': trade_data['s'],
                        'agg_trade_id': int(trade_data['a']),
                        'price': float(trade_data['p']),
                        'quantity': float(trade_data['q']),
                        'first_trade_id': int(trade_data['f']),
                        'last_trade_id': int(trade_data['l']),
                        'trade_time': self._convert_timestamp(trade_data['T']),
                        'is_buyer_maker': bool(trade_data['m'])
                    }
                    processed_batch.append(processed_data)
                except Exception as e:
                    logger.error(f"Error processing trade data: {e}")
                    self.error_queue.put(trade_data)
                    return False

            if processed_batch:
                return self._insert_batch(processed_batch)
            return True  # Return True if batch was empty (no processing needed)

        except Exception as e:
            logger.error(f"Error in process_batch: {e}")
            return False

    def _insert_batch(self, batch: List[Dict[str, Any]]) -> bool:
        """
        Insert a batch of trades into ClickHouse
        Returns:
            bool: True if insertion was successful, False otherwise
        """
        for attempt in range(self.max_retries):
            try:
                self.client.execute(
                    '''
                    INSERT INTO crypto_data.aggTrades (
                        event_type, event_time, symbol, agg_trade_id,
                        price, quantity, first_trade_id, last_trade_id,
                        trade_time, is_buyer_maker
                    ) VALUES
                    ''',
                    batch
                )
                logger.info(f"Inserted {len(batch)} records")
                return True
            except Exception as e:
                logger.error(f"Insert attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    for record in batch:
                        self.error_queue.put(record)
                time.sleep(self.retry_delay)

        return False

    def _consume_stream(self):
        """Consume trades from Redis Stream"""
        while self.is_running:
            try:
                batches = self.redis_stream.consume_trades()
                if not batches:
                    continue

                for trades_batch, message_ids in batches:
                    if not self.is_running:
                        break

                    if trades_batch:  # Only process if we have trades
                        success = self._process_batch(trades_batch)
                        if success:
                            self.redis_stream.ack_messages(message_ids)
                        else:
                            logger.error(f"Failed to process batch of {len(trades_batch)} trades")

                if len(batches) < 5:
                    time.sleep(1)  # reduce clickhouse insertions

            except Exception as e:
                logger.error(f"Error consuming from Redis Stream: {e}")
                if self.is_running:
                    time.sleep(self.retry_delay)

    def shutdown(self):
        """Gracefully shutdown the writer"""
        logger.info("Initiating shutdown...")
        self.is_running = False

        # Wait for consumer thread to finish
        if self.consumer_thread and self.consumer_thread.is_alive():
            self.consumer_thread.join()

        # Cleanup Redis
        self.redis_stream.cleanup()

        # Cleanup ClickHouse
        super().shutdown()

        logger.info("Shutdown complete")


class ClickHouseReader(ClickHouseBase):
    def get_agg_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get aggregated trades for a symbol"""
        query = '''
            SELECT
                event_type,
                event_time,
                symbol,
                agg_trade_id,
                price,
                quantity,
                first_trade_id,
                last_trade_id,
                trade_time,
                is_buyer_maker
            FROM crypto_data.aggTrades
            WHERE symbol = %(symbol)s
            ORDER BY trade_time DESC
            LIMIT %(limit)s
        '''
        try:
            result = self.client.execute(
                query,
                {'symbol': symbol.upper(), 'limit': limit}
            )

            return [
                {
                    'event_type': row[0],
                    'event_time': row[1],
                    'symbol': row[2],
                    'agg_trade_id': row[3],
                    'price': float(row[4]),
                    'quantity': float(row[5]),
                    'first_trade_id': row[6],
                    'last_trade_id': row[7],
                    'trade_time': row[8],
                    'is_buyer_maker': row[9]
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []

    def get_trade_statistics(self, symbol: str, interval_minutes: int = 5) -> Dict[str, Any]:
        """Get trade statistics for a symbol over the specified interval"""
        query = '''
            SELECT
                round(avg(price), 2) as avg_price,
                round(sum(quantity), 4) as volume,
                count() as trade_count,
                min(price) as low_price,
                max(price) as high_price
            FROM crypto_data.aggTrades
            WHERE symbol = %(symbol)s
                AND trade_time >= now() - INTERVAL %(interval)s MINUTE
        '''
        try:
            result = self.client.execute(
                query,
                {'symbol': symbol.upper(), 'interval': interval_minutes}
            )

            if result and result[0]:
                return {
                    'avg_price': float(result[0][0]),
                    'volume': float(result[0][1]),
                    'trade_count': int(result[0][2]),
                    'low_price': float(result[0][3]),
                    'high_price': float(result[0][4]),
                    'interval_minutes': interval_minutes,
                    'symbol': symbol.upper()
                }
            return {}
        except Exception as e:
            logger.error(f"Error fetching trade statistics: {e}")
            return {}