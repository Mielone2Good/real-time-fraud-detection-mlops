from confluent_kafka import Producer
import json
import pandas as pd
import time
import random
import argparse
import threading
import os
from confluent_kafka.admin import AdminClient, NewTopic
from abc import ABC, abstractmethod
from dotenv import load_dotenv

load_dotenv()

class TransactionsDataset(ABC):
    @abstractmethod
    def get_random_transaction(self, fraud_only: bool = False) -> dict:
        pass

class CreditCardTransactionsDataset(TransactionsDataset):
    """
    Class to simulate a dataset of transactions.
    """
    
    def __init__(self, csv_path: str, columns_to_exclude: list = []) -> None:
        """
        Undersample the data for better simulation.
        """
        try:
            self.data = pd.read_csv(csv_path)
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            exit(1)
            
        self.data = self._undersample_data(self.data)
        self.columns_to_exclude = columns_to_exclude

    def get_random_transaction(self, fraud_only: bool = False) -> dict:
        """
        Returns a random transaction from the dataset
        """

        if fraud_only:
           transaction = self.data[self.data["Class"] == 1].sample(1)
        else:
           transaction = self.data.sample(1)
           
        transaction["TransactionID"] = transaction.index[0]
        print("Generated random transaction with class: ", transaction["Class"].iloc[0])
        transaction_dict = transaction.drop(columns=self.columns_to_exclude).iloc[0].to_dict()
        
        return transaction_dict
        
    def _undersample_data(self, data: pd.DataFrame):
        df_fraud = data[data["Class"] == 1]  
        df_nonfraud = data[data["Class"] == 0]
        n_fraud = len(df_fraud)
        n_nonfraud = n_fraud * 5
        df_nonfraud_sampled = df_nonfraud.sample(n=min(n_nonfraud, len(df_nonfraud)), random_state=42)
        df_balanced = pd.concat([df_fraud, df_nonfraud_sampled]).sample(frac=1, random_state=42)
        return df_balanced
        
class TransactionStreamSimulator:
    """
    Class to simulate a stream of transactions 
    using Kafka for testing.
    """
    
    def __init__(self, 
            csv_path: str, 
            columns_to_exclude: list = [], 
            workers: int = 1, 
            fraud_only: bool = False, 
            transactions_dataset: TransactionsDataset = None
        ) -> None:
        
        bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:29092")
        self.p = Producer({"bootstrap.servers": bootstrap})
        self.admin_client = AdminClient({"bootstrap.servers": bootstrap})
        self.admin_client.create_topics(
            [NewTopic("transactions", num_partitions=1, replication_factor=1)]
        )
        self.transactions_dataset = transactions_dataset
        self.fraud_only = fraud_only
        self.workers = workers
        self._stop_event = threading.Event()

    def _data_stream_worker(self, sleep_time: int = 1, worker_id: int = 0):
        """
        One worker will simulate a stream of transactions.
        """
        while not self._stop_event.is_set():
            random_transaction = self.transactions_dataset.get_random_transaction(fraud_only=self.fraud_only)
            try:
                self.p.produce(
                    topic="transactions",
                    key=str(random_transaction["TransactionID"]),
                    value=json.dumps(random_transaction),
                )
                remaining = self.p.flush(timeout=1)
                if remaining > 0 and self._stop_event.is_set():
                    break
            except Exception as e:
                if not self._stop_event.is_set():
                    print(f"Error producing transaction for worker {worker_id}: {e}")
            if self._stop_event.wait(timeout=sleep_time / 1000.0):
                break

    def simulate_data_stream(self, sleep_time: int = 1):
        """
        Simulates a stream of transactions.
        """
        threads = []
        for worker_id in range(self.workers):
            t = threading.Thread(target=self._data_stream_worker, args=(sleep_time, worker_id), daemon=True)
            t.start()
            threads.append(t)
        try:
            while not self._stop_event.wait(timeout=1):
                pass
        except KeyboardInterrupt:
            pass

    def close(self) -> None:
        """
        Stops workers and flushes the Kafka producer.
        """
        self._stop_event.set()
        try:
            self.p.flush(timeout=3)
        except Exception:
            pass

    def run(self, sleep_time: int = 1) -> None:
        """
        Runs the simulation of the data stream.
        """
        try:
            self.simulate_data_stream(sleep_time)
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, stopping simulation...")
        finally:
            self.close()
    
    
if __name__ == "__main__":
    """
    Main function to run the simulation.
    Args:
        --sleep-time: The time to sleep between transactions in milliseconds.
    """
    import os
    default_csv = os.getenv("CREDITCARD_CSV_PATH", "data/raw_data/creditcard.csv")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--sleep-time", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--csv-path", type=str, default=default_csv, help="Path to creditcard.csv")
    args = parser.parse_args()
    print(f"Sleep time: {args.sleep_time} ms, Workers: {args.workers}, CSV: {args.csv_path}")
    
    transaction_stream_simulator = TransactionStreamSimulator(
        csv_path=args.csv_path,
        columns_to_exclude=["Time", "Class"],
        workers=args.workers,
        fraud_only=False,
        transactions_dataset=CreditCardTransactionsDataset(
            csv_path=args.csv_path,
            columns_to_exclude=["Time", "Class"]
        )
    )
    transaction_stream_simulator.run(sleep_time=args.sleep_time)