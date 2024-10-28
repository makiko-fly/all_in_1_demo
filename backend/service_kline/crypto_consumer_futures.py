import time
from loguru import logger
from common_clickhouse import ClickHouseWriter


if __name__ == "__main__":
    # Initialize the writer
    writer = ClickHouseWriter(
        host='localhost',
        port=9000,
        database='crypto_data',
        redis_host='localhost',
        redis_port=6379,
        retry_delay=0.5,
    )

    try:
        # Start the writer
        writer.start()
        logger.info("Writer started successfully")

        # Keep the main thread running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        writer.shutdown()