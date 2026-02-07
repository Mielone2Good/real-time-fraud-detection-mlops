import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os
import traceback
import json
from abc import ABC, abstractmethod

class DataService(ABC):
    @abstractmethod
    def get_transactions(self) -> list[dict]:
        pass

    @abstractmethod
    def insert_transaction(self, 
        transaction_id: str, 
        timestamp: str, 
        transaction_data: dict, 
        prediction: int, 
        probability: float, 
        processing_time: float) -> None:
        pass
    
    @abstractmethod
    def close(self) -> None:
        pass
    
    @abstractmethod
    def _create_transactions_table(self) -> None:
        pass
    
    @abstractmethod
    def _clean_transactions_table(self) -> None:
        pass


class PostgresDataService(DataService):
    def __init__(self):
        load_dotenv()
        try:
            self.conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                database=os.getenv("POSTGRES_DB", "fraud_detection"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "postgres")
            )
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            self._create_transactions_table()

        except Exception as e:
            print(f"Error connecting to database: {e}")
            print(traceback.format_exc())
            exit(1)

    def insert_transaction(self, 
        transaction_id: str,
        timestamp: str,
        transaction_data: dict,
        prediction: int,
        probability: float,
        processing_time: float
    ) -> None:
        try:
            transaction_data_json = json.dumps(transaction_data)
            self.cursor.execute("INSERT INTO transactions (transaction_id, timestamp, transaction_data, prediction, probability, processing_time) VALUES (%s, %s, %s, %s, %s, %s)", (transaction_id, timestamp, transaction_data_json, prediction, probability, processing_time))
            self.conn.commit()
        except Exception as e:
            print(f"Error inserting transaction: {e}")

    def get_transactions(self) -> list[dict]:
        try:
            self.cursor.execute("SELECT * FROM transactions")
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting transactions: {e}")
            return []

    def _create_transactions_table(self) -> None:
        try:
            self.cursor.execute("CREATE TABLE IF NOT EXISTS transactions (transaction_id VARCHAR(255), timestamp TIMESTAMP, transaction_data JSONB, prediction INT, probability FLOAT, processing_time FLOAT, isReallyFraud INT DEFAULT NULL)")
        except Exception as e:
            print(f"Error creating transactions table: {e}")

    def _clean_transactions_table(self) -> None:
        try:
            self.cursor.execute("DELETE FROM transactions")
            self.conn.commit()
        except Exception as e:
            print(f"Error cleaning transactions table: {e}")


    def close(self) -> None:
        self.cursor.close()
        self.conn.close()


if __name__ == "__main__":
    """ Test the data manager """
    data_service = PostgresDataService()
    transactions = data_service.get_transactions()
    print(transactions)
    data_service.close()
