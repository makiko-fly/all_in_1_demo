import redis
from redis.exceptions import ConnectionError
import json
from loguru import logger
from typing import List, Dict, Any, Tuple, Optional


class RedisStreamManager:
    def __init__(self, host='localhost', port=6379, stream_name='trades', max_size=10000):
        self.redis_client = redis.Redis(host=host, port=port, decode_responses=True)
        self.stream_name = stream_name
        self.group_name = 'trade_processors'
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

    def produce_trade(self, trade_data: Dict) -> str:
        """Add trade to Redis Stream"""
        try:
            message_id = self.redis_client.xadd(
                name=self.stream_name,
                fields={'data': json.dumps(trade_data)},
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

    def read_latest_n(self, n=100):
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
            print(f'stream_info: {stream_info}')
            print(f'last_id: {last_id}')

            # Read the latest n messages
            messages = self.redis_client.xrevrange(
                self.stream_name,
                max=last_id,
                min='-',
                count=n
            )

            print(f'message: {messages}')

            # Extract and return only the trade data
            trades = []
            for msg_id, msg_data in messages:
                trade_data = json.loads(msg_data['data'])
                trades.append(trade_data)

            return trades

        except Exception as e:
            print(f"Error reading from Redis stream: {e}")
            return []

    def consume_trades(self, batch_size=100, timeout=1000) -> List[Tuple[List[Dict], List[str]]]:
        """
        Consume trades from Redis Stream
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

            result = []
            stream_messages = messages[0][1]

            current_batch = []
            current_ids = []

            for message_id, message in stream_messages:
                trade_data = json.loads(message['data'])
                current_batch.append(trade_data)
                current_ids.append(message_id)

                if len(current_batch) >= batch_size:
                    result.append((current_batch, current_ids))
                    current_batch = []
                    current_ids = []

            if current_batch:
                result.append((current_batch, current_ids))

            return result

        except ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing messages: {e}")
            raise

    def ack_messages(self, message_ids: List[str]):
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

    def delete_messages_older_than(self, message_id):
        """Delete all messages older than current consumer position"""
        try:
            group_info = self.redis_client.xinfo_consumers(
                name=self.stream_name,
                groupname=self.group_name
            )

            if not group_info:
                logger.warning("No consumer info found")
                return

            min_pending_id = None
            for consumer in group_info:
                if consumer['pending'] > 0:
                    pending_range = self.redis_client.xpending(
                        name=self.stream_name,
                        groupname=self.group_name
                    )
                    if pending_range:
                        pending_messages = self.redis_client.xpending_range(
                            name=self.stream_name,
                            groupname=self.group_name,
                            min='-',
                            max='+',
                            count=1,
                            consumername=consumer['name']
                        )
                        if pending_messages:
                            consumer_min_id = pending_messages[0]['message_id']
                            if min_pending_id is None or consumer_min_id < min_pending_id:
                                min_pending_id = consumer_min_id

            if min_pending_id:
                self.redis_client.xtrim(
                    name=self.stream_name,
                    minid=min_pending_id,
                    approximate=False
                )
                logger.info(f"Deleted messages older than ID {min_pending_id}")
            else:
                logger.info("No pending messages found to use as reference point")

        except Exception as e:
            logger.error(f"Error deleting old messages: {e}")
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