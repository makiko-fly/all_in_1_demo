import sys
import redis
from redis.exceptions import ConnectionError
import json
from loguru import logger
from typing import List, Dict, Any, Tuple, Optional


class RedisStreamManager:
    # def __init__(self, host='localhost', port=6379, stream_name='trades', max_size=10000):
    def __init__(self, host, port, stream_name, max_size=2000):
        self.redis_client = redis.Redis(host=host, port=port, decode_responses=True)
        self.stream_name = stream_name
        self.group_name = stream_name + '_read_group'
        self.consumer_name = 'consumer_1'
        self.max_size = max_size

        try:
            self.redis_client.xgroup_create(
                name=self.stream_name,
                groupname=self.group_name,
                id='$',
                mkstream=True
            )
        except redis.ResponseError as e:
            if 'BUSYGROUP' not in str(e):
                raise

    def get_stream_length(self) -> int:
        """Get current length of the stream"""
        try:
            return self.redis_client.xlen(name=self.stream_name)
        except ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            raise

    def write_record(self, record_data: Dict) -> str:
        """Add trade to Redis Stream"""
        try:
            message_id = self.redis_client.xadd(
                name=self.stream_name,
                fields={'data': json.dumps(record_data)},
            )

            current_length = self.get_stream_length()
            if current_length > self.max_size + 1000:
                self.redis_client.xtrim(
                    name=self.stream_name,
                    maxlen=self.max_size,
                    approximate=False
                )
                logger.info(f"Performed precise trim to {self.max_size} messages")

            logger.debug(f"Added message {message_id}, stream length: {self.get_stream_length()}")
            return message_id

        except ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error producing trade: {e}")
            raise

    def read_records(self, batch_size=100, timeout=1000) -> List[Tuple[List[Dict], List[str]]]:
        """
        Consume records from Redis Stream
        Returns:
            List[Tuple[List[Dict], List[str]]]: List of (trades_data, message_ids) tuples
        """
        try:
            messages = self.redis_client.xreadgroup(
                groupname=self.group_name,
                consumername=self.consumer_name,
                streams={self.stream_name: '>'},
                count=batch_size,
                block=timeout
            )

            if not messages:
                return []

            stream_messages = messages[0][1]

            records = []
            for msg_id, msg_data in stream_messages:
                record = json.loads(msg_data['data'])
                records.append((msg_id, record))

            return records

        except ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing messages: {e}")
            raise

    def read_latest_records(self, n=100):
        """
        Read the latest n records from the Redis stream

        Args:
            n (int): Number of records to read (default: 100)

        Returns:
            list: List of the latest n trades
        """
        try:
            # Get the last ID
            stream_info = self.redis_client.xinfo_stream(self.stream_name)
            last_id = stream_info.get('last-generated-id', '0-0')

            # Read the latest n messages
            messages = self.redis_client.xrevrange(
                self.stream_name,
                max=last_id,
                min='-',
                count=n
            )

            records = []
            for msg_id, msg_data in messages:
                record = json.loads(msg_data['data'])
                records.append((msg_id, record))

            return records

        except Exception as e:
            print(f"Error reading from Redis stream: {e}")
            return []

    def ack_messages(self, message_ids):
        """Acknowledge processed messages"""
        if not message_ids:
            return

        try:
            self.redis_client.xack(
                self.stream_name,
                self.group_name,
                *message_ids  # Pass message_ids as unpacked positional arguments
            )

            # if self.get_stream_length() > 1000:
            #     self.delete_old_messages()

            logger.debug(f"Acknowledged {len(message_ids)} messages")
        except Exception as e:
            logger.error(f"Error acknowledging messages: {e}")
            raise

    def get_stream_info(self) -> Dict:
        """Get information about the stream"""
        try:
            length = self.get_stream_length()
            first_entry = self.redis_client.xrange(
                name=self.stream_name,
                count=1
            )
            last_entry = self.redis_client.xrevrange(
                name=self.stream_name,
                count=1
            )

            return {
                'length': length,
                'first_id': first_entry[0][0] if first_entry else None,
                'last_id': last_entry[0][0] if last_entry else None,
                'max_size': self.max_size
            }
        except Exception as e:
            logger.error(f"Error getting stream info: {e}")
            raise

    def delete_stream(self):
        """Delete the entire stream"""
        try:
            self.redis_client.delete(self.stream_name)
            logger.info(f"Stream {self.stream_name} deleted")

            try:
                self.redis_client.xgroup_destroy(
                    name=self.stream_name,
                    groupname=self.group_name
                )
                logger.info(f"Consumer group {self.group_name} deleted")
            except:
                pass

        except Exception as e:
            logger.error(f"Error deleting stream: {e}")
            raise

    def cleanup(self):
        """Cleanup resources"""
        try:
            self.redis_client.close()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise