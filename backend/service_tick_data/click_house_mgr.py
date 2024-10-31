from clickhouse_driver import Client
from loguru import logger
from typing import Optional, List, Dict, Any, Union
import pandas as pd


class ClickHouseMgr:
    def __init__(
            self,
            host: str = 'localhost',
            port: int = 9000,
            user: str = 'default',
            password: str = '',
            database: str = 'default'
    ):
        """
        Initialize ClickHouse connection manager

        Args:
            host (str): ClickHouse server host
            port (int): ClickHouse server port
            user (str): Username for authentication
            password (str): Password for authentication
            database (str): Default database name
        """
        self.connection_params = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database
        }

        self.client = None
        self.connect()

    def connect(self) -> None:
        """Establish connection to ClickHouse server"""
        try:
            self.client = Client(**self.connection_params)
            logger.info(
                f"Connected to ClickHouse server at {self.connection_params['host']}:{self.connection_params['port']}")
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise

    def execute(self, query: str, params: Optional[Dict] = None) -> List:
        """
        Execute a SQL query

        Args:
            query (str): SQL query to execute
            params (dict, optional): Query parameters for parameterized queries

        Returns:
            list: Query results
        """
        try:
            result = self.client.execute(query, params or {})
            logger.debug(f"Executed query: {query}")
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query}")
            raise

    def execute_df(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """
        Execute a SQL query and return results as a pandas DataFrame

        Args:
            query (str): SQL query to execute
            params (dict, optional): Query parameters for parameterized queries

        Returns:
            pandas.DataFrame: Query results as a DataFrame
        """
        try:
            result = self.client.execute(query, params or {}, with_column_types=True)
            columns = [col[0] for col in result[1]]
            df = pd.DataFrame(result[0], columns=columns)
            logger.debug(f"Executed query and converted to DataFrame: {query}")
            return df
        except Exception as e:
            logger.error(f"Query execution or DataFrame conversion failed: {e}\nQuery: {query}")
            raise

    def insert_df(self, table: str, df: pd.DataFrame, batch_size: int = 100000) -> None:
        """
        Insert pandas DataFrame into ClickHouse table

        Args:
            table (str): Target table name
            df (pandas.DataFrame): DataFrame to insert
            batch_size (int): Number of rows per batch insert
        """
        try:
            columns = df.columns.tolist()
            data = df.to_dict('records')

            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                self.client.execute(
                    f'INSERT INTO {table} ({", ".join(columns)}) VALUES',
                    batch
                )

            logger.info(f"Inserted {len(df)} rows into table {table}")
        except Exception as e:
            logger.error(f"Failed to insert data into table {table}: {e}")
            raise

    def create_table(self, table: str, schema: Dict[str, str], engine: str = "MergeTree()") -> None:
        """
        Create a new table in ClickHouse

        Args:
            table (str): Table name
            schema (dict): Column definitions {column_name: column_type}
            engine (str): Table engine specification
        """
        try:
            columns = ", ".join([f"{col} {dtype}" for col, dtype in schema.items()])
            query = f"CREATE TABLE IF NOT EXISTS {table} ({columns}) ENGINE = {engine}"
            self.execute(query)
            logger.info(f"Created table {table}")
        except Exception as e:
            logger.error(f"Failed to create table {table}: {e}")
            raise

    def get_table_schema(self, table: str) -> Dict[str, str]:
        """
        Get schema information for a table

        Args:
            table (str): Table name

        Returns:
            dict: Column names and their types
        """
        try:
            query = f"DESCRIBE TABLE {table}"
            result = self.execute(query)
            return {row[0]: row[1] for row in result}
        except Exception as e:
            logger.error(f"Failed to get schema for table {table}: {e}")
            raise

    def close(self) -> None:
        """Close the ClickHouse connection"""
        try:
            if self.client:
                self.client.disconnect()
                logger.info("Disconnected from ClickHouse server")
        except Exception as e:
            logger.error(f"Error while closing connection: {e}")
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def init_dbs_and_tables(self, cluster_name: str = 'cl-mkt-data') -> None:
        """
        Initialize the cn_stock database and book tables on the specified cluster

        Args:
            cluster_name (str): Name of the ClickHouse cluster
        """
        try:
            # Create database if not exists
            self.execute(f"""
                CREATE DATABASE IF NOT EXISTS cn_stock ON CLUSTER '{cluster_name}'
            """)
            logger.info("Database 'cn_stock' created or already exists")

            # Create replicated table
            self.execute(f"""
                CREATE TABLE IF NOT EXISTS cn_stock.book ON CLUSTER '{cluster_name}'
                (
                    HostName String,
                    Date String,
                    DateTimeStr String,
                    LongTimestamp Int64,
                    Symbol String,
                    BidPrice1 Float64,
                    BidPrice2 Float64,
                    BidPrice3 Float64,
                    BidPrice4 Float64,
                    BidPrice5 Float64,
                    AskPrice1 Float64,
                    AskPrice2 Float64,
                    AskPrice3 Float64,
                    AskPrice4 Float64,
                    AskPrice5 Float64,
                    BidSize1 Float64,
                    BidSize2 Float64,
                    BidSize3 Float64,
                    BidSize4 Float64,
                    BidSize5 Float64,
                    AskSize1 Float64,
                    AskSize2 Float64,
                    AskSize3 Float64,
                    AskSize4 Float64,
                    AskSize5 Float64,
                    PRIMARY KEY (DateTimeStr, Symbol)
                )
                ENGINE = ReplicatedMergeTree('/clickhouse/tables/{{shard}}/cn_stock.book', '{{replica}}')
                PARTITION BY Date
                ORDER BY (DateTimeStr, Symbol)
                SETTINGS index_granularity = 8192
            """)
            logger.info("Table 'cn_stock.book' created or already exists")

            # Create distributed table
            self.execute(f"""
                CREATE TABLE IF NOT EXISTS cn_stock.book_distributed ON CLUSTER '{cluster_name}'
                (
                    HostName String,
                    Date String,
                    DateTimeStr String,
                    LongTimestamp Int64,
                    Symbol String,
                    BidPrice1 Float64,
                    BidPrice2 Float64,
                    BidPrice3 Float64,
                    BidPrice4 Float64,
                    BidPrice5 Float64,
                    AskPrice1 Float64,
                    AskPrice2 Float64,
                    AskPrice3 Float64,
                    AskPrice4 Float64,
                    AskPrice5 Float64,
                    BidSize1 Float64,
                    BidSize2 Float64,
                    BidSize3 Float64,
                    BidSize4 Float64,
                    BidSize5 Float64,
                    AskSize1 Float64,
                    AskSize2 Float64,
                    AskSize3 Float64,
                    AskSize4 Float64,
                    AskSize5 Float64,
                )
                ENGINE = Distributed('{cluster_name}', 'cn_stock', 'book', rand())
            """)
            logger.info("Distributed table 'cn_stock.book_distributed' created or already exists")

        except Exception as e:
            logger.error(f"Failed to setup ClickHouse database and table: {e}")
            raise

    def recreate_tables(self, cluster_name: str = 'cl-mkt-data') -> None:
        """Drop and recreate the tables"""
        try:
            # Drop tables in correct order
            self.execute(f"""
                DROP TABLE IF EXISTS cn_stock.book_distributed ON CLUSTER '{cluster_name}'
            """)
            logger.info("Dropped distributed table 'cn_stock.book_distributed'")

            self.execute(f"""
                DROP TABLE IF EXISTS cn_stock.book ON CLUSTER '{cluster_name}'
            """)
            logger.info("Dropped table 'cn_stock.book'")

            # # Recreate tables using init_dbs_and_tables
            # self.init_dbs_and_tables(cluster_name)

        except Exception as e:
            logger.error(f"Failed to recreate tables: {e}")
            raise

    def show_database_info(self, database: str = 'cn_stock') -> None:
        """
        List all tables, shards, replicas, and partitions in the specified database

        Args:
            database (str): Database name to inspect
        """
        try:
            # List all tables
            tables = self.execute(f"""
                SELECT name, engine, create_table_query
                FROM system.tables
                WHERE database = '{database}'
                FORMAT Pretty
            """)
            print(f"\n=== Tables in {database} ===")
            print(tables)

            # List shards and replicas
            cluster_info = self.execute("""
                SELECT 
                    cluster,
                    shard_num,
                    shard_weight,
                    replica_num,
                    host_name,
                    host_address,
                    port,
                    is_local
                FROM system.clusters
                FORMAT Pretty
            """)
            print("\n=== Cluster Configuration ===")
            print(cluster_info)

            # Get all tables for partition information
            tables_query = self.execute(f"""
                SELECT name
                FROM system.tables
                WHERE database = '{database}'
            """)

            # List partitions for each table
            print("\n=== Partitions Information ===")
            for table in tables_query:
                table_name = table[0]
                partitions = self.execute(f"""
                    SELECT 
                        partition,
                        name,
                        active,
                        partition_id,
                        rows,
                        disk_name,
                        data_compressed_bytes,
                        data_uncompressed_bytes,
                        marks_bytes,
                        modification_time
                    FROM system.parts
                    WHERE database = '{database}'
                    AND table = '{table_name}'
                    FORMAT Pretty
                """)
                print(f"\nPartitions for {database}.{table_name}:")
                print(partitions)

            # Show table sizes
            table_sizes = self.execute(f"""
                SELECT 
                    table,
                    formatReadableSize(sum(bytes)) as size,
                    sum(rows) as total_rows,
                    min(modification_time) as min_mod_time,
                    max(modification_time) as max_mod_time
                FROM system.parts
                WHERE database = '{database}'
                GROUP BY table
                FORMAT Pretty
            """)
            print("\n=== Table Sizes ===")
            print(table_sizes)

            # Show recent modifications
            recent_mods = self.execute(f"""
                SELECT 
                    table,
                    partition_id,
                    formatReadableSize(bytes) as part_size,
                    rows,
                    modification_time
                FROM system.parts
                WHERE database = '{database}'
                ORDER BY modification_time DESC
                LIMIT 5
                FORMAT Pretty
            """)
            print("\n=== Recent Modifications ===")
            print(recent_mods)

        except Exception as e:
            logger.error(f"Failed to get database information: {e}")
            raise

    def get_latest_cn_stock_book(self, limit: int = 100):
        """
        Get latest X records from cn_stock.book_distributed table ordered by DateTimeStr,
        including the shard server name where the record is stored in

        Args:
            limit (int): Number of latest records to return. Defaults to 100

        Returns:
            List of tuples with columns:
                HostName: String - hostname of the server
                Date: String - date in YYYY-MM-DD format
                DateTimeStr: String - datetime string
                LongTimestamp: Int64 - unix timestamp
                Symbol: String - stock symbol
                BidPrice1-5: Float64 - bid price levels 1-5
                AskPrice1-5: Float64 - ask price levels 1-5
                BidSize1-5: Float64 - bid size levels 1-5
                AskSize1-5: Float64 - ask size levels 1-5
                StoredIn: String - clickhouse server name storing this record
        """
        query = f"""
        SELECT 
            *,
            hostname() as ReadFrom
        FROM cn_stock.book_distributed
        ORDER BY DateTimeStr DESC
        LIMIT {limit}
        """
        return self.execute_df(query)

    def get_data_distribution(self):
        """
        Get data distribution across servers
        """
        query = """
        SELECT 
            hostname() as server,
            count() as row_count,
            min(Date) as min_date,
            max(Date) as max_date
        FROM cn_stock.book_distributed
        GROUP BY hostname()
        ORDER BY server
        """
        return self.execute_df(query)