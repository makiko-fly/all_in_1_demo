import sys
import time
from click_house_mgr import ClickHouseMgr
from redis_stream_mgr import RedisStreamManager
from loguru import logger
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple
import socket


class TickDataConsumer:
    def __init__(self, redis_config: Dict[str, Any], clickhouse_config: Dict[str, Any]):
        self.hostname = socket.gethostname()
        self.redis_mgr = RedisStreamManager(
            host=redis_config['host'],
            port=redis_config['port'],
            stream_name=redis_config['stream_name'],
            max_size=redis_config.get('max_size', 2000)
        )
        self.ch_mgr = ClickHouseMgr(**clickhouse_config)

    def start_consuming(self, batch_size=100):
        """Start consuming messages from Redis Stream"""
        logger.info('start consuming records from redis stream')
        while True:
            try:
                batch_data = self.redis_mgr.read_records(batch_size=batch_size)
                logger.info(f'== batch data: {batch_data}')

                # batch_data = self.redis_mgr.read_latest_records(100)
                self.process_batch(batch_data)
                time.sleep(2)
            except Exception as e:
                logger.error(f"Error in consumption loop: {e}")
                continue

    def transform_tick_data(self, data):
        """Transform Redis stream data to ClickHouse table format"""
        try:
            tick_data = data['data']
            bids = tick_data['bids']
            asks = tick_data['asks']

            # Store original timestamp
            long_timestamp = int(tick_data['tick_time'])

            # Convert timestamp to formatted string
            timestamp = datetime.fromtimestamp(long_timestamp / 1000)
            datetime_str = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            date_str = timestamp.strftime('%Y-%m-%d')

            transformed_data = {
                'Date': date_str,
                'DateTimeStr': datetime_str,
                'LongTimestamp': long_timestamp,
                'Symbol': tick_data['code'],
                # Bid prices and sizes
                'BidPrice1': float(bids[0]['price']),
                'BidPrice2': float(bids[1]['price']),
                'BidPrice3': float(bids[2]['price']),
                'BidPrice4': float(bids[3]['price']),
                'BidPrice5': float(bids[4]['price']),
                'BidSize1': float(bids[0]['volume']),
                'BidSize2': float(bids[1]['volume']),
                'BidSize3': float(bids[2]['volume']),
                'BidSize4': float(bids[3]['volume']),
                'BidSize5': float(bids[4]['volume']),
                # Ask prices and sizes
                'AskPrice1': float(asks[0]['price']),
                'AskPrice2': float(asks[1]['price']),
                'AskPrice3': float(asks[2]['price']),
                'AskPrice4': float(asks[3]['price']),
                'AskPrice5': float(asks[4]['price']),
                'AskSize1': float(asks[0]['volume']),
                'AskSize2': float(asks[1]['volume']),
                'AskSize3': float(asks[2]['volume']),
                'AskSize4': float(asks[3]['volume']),
                'AskSize5': float(asks[4]['volume'])
            }
            return transformed_data
        except Exception as e:
            logger.error(f"Error transforming tick data: {e}")
            raise

    def process_batch(self, batch_data):
        """Process a batch of messages and insert into ClickHouse"""
        try:
            transformed_data = []
            message_ids = []
            for msg_id, data in batch_data:
                try:
                    transformed = self.transform_tick_data(data)
                    transformed_data.append(transformed)
                    message_ids.append(msg_id)
                except Exception as e:
                    logger.error(f"Error transforming data: {e}")
                    continue

            if transformed_data:
                # Prepare the values for insertion
                values = []
                for item in transformed_data:
                    value = f"(hostname(), " \
                            f"'{item['Date']}', " \
                            f"'{item['DateTimeStr']}', " \
                            f"{item['LongTimestamp']}, " \
                            f"'{item['Symbol']}', " \
                            f"{item['BidPrice1']}, {item['BidPrice2']}, {item['BidPrice3']}, {item['BidPrice4']}, {item['BidPrice5']}, " \
                            f"{item['AskPrice1']}, {item['AskPrice2']}, {item['AskPrice3']}, {item['AskPrice4']}, {item['AskPrice5']}, " \
                            f"{item['BidSize1']}, {item['BidSize2']}, {item['BidSize3']}, {item['BidSize4']}, {item['BidSize5']}, " \
                            f"{item['AskSize1']}, {item['AskSize2']}, {item['AskSize3']}, {item['AskSize4']}, {item['AskSize5']})"
                    values.append(value)

                query = """
                INSERT INTO cn_stock.book_distributed 
                (
                    HostName, Date, DateTimeStr, LongTimestamp, Symbol,
                    BidPrice1, BidPrice2, BidPrice3, BidPrice4, BidPrice5,
                    AskPrice1, AskPrice2, AskPrice3, AskPrice4, AskPrice5,
                    BidSize1, BidSize2, BidSize3, BidSize4, BidSize5,
                    AskSize1, AskSize2, AskSize3, AskSize4, AskSize5
                )
                VALUES 
                """ + ",\n".join(values)

                self.ch_mgr.execute(query)
                logger.info(f"Successfully inserted {len(transformed_data)} records")

                # Acknowledge messages after successful insertion
                self.redis_mgr.ack_messages(message_ids)

        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            raise


def main():
    redis_config = {
        'host': 'localhost',
        'port': 6379,
        'stream_name': 'cn_stock',
        'max_size': 2000
    }

    clickhouse_config = {
        'host': 'localhost',
        'port': 9000,
        'user': 'default',
        'password': '',
        'database': 'default'
    }

    try:
        # # Initialize database and tables
        # with ClickHouseMgr(**clickhouse_config) as ch_mgr:
        #     ch_mgr.init_dbs_and_tables(cluster_name='cl-mkt-data')
        #     logger.info("Successfully initialized database and tables")

        # Start consuming messages
        consumer = TickDataConsumer(redis_config, clickhouse_config)
        consumer.start_consuming()

    except Exception as e:
        logger.error(f"Failed to initialize or run consumer: {e}")
        raise


if __name__ == "__main__":
    main()