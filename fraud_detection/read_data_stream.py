from confluent_kafka import Consumer
from confluent_kafka.admin import AdminClient, NewTopic
from neural_network import FraudDetectionModel, XGBoostModel
from retraining_pipeline import RetrainingPipeline
from data_manager import DataService, PostgresDataService
import json
import asyncio
import os
import pandas as pd
from datetime import datetime

def _kafka_bootstrap_servers() -> str:
    return os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:29092")


class ProcessDataStream:
    def __init__(self, data_service: DataService, model: FraudDetectionModel, retraining_pipeline: RetrainingPipeline):
        bootstrap = _kafka_bootstrap_servers()
        self.consumer = Consumer({
            "bootstrap.servers": bootstrap,
            "group.id": "fraud-detection-consumer",
            "auto.offset.reset": "earliest"
        })
        
        self.admin_client = AdminClient({"bootstrap.servers": bootstrap})
        self.admin_client.create_topics(
            [NewTopic("transactions", num_partitions=1, replication_factor=1)]
        )
        self.consumer.subscribe(["transactions"])
        self.model = model
        self.data_service = data_service
        self.retraining_pipeline = retraining_pipeline
        
    async def read_data_stream(self):
        while True:
            msg = await asyncio.to_thread(self.consumer.poll, 1.0)
            if msg is None:
                continue
            if msg.error():
                print("Error: %s" % msg.error())
                continue
            json_data = json.loads(msg.value().decode('utf-8'))
            await self.process_data(json_data)
    
    async def _check_for_retraining_loop(self) -> None:
        """
        Every 10 minutes, check if we have enough labeled data to retrain.
        If yeah, request retraining and run it in executor.
        """
        loop = asyncio.get_running_loop()
        while True:
            await asyncio.sleep(600)
            labeled = self.retraining_pipeline.get_labeled_count()
            if not self.retraining_pipeline.request_retraining():
                print(f"Retraining check: {labeled} labeled samples (need 500). Next check in 10 min.")
                continue

            print("Enough labeled data reached — attempting retraining...")
            try:
                result = await loop.run_in_executor(
                    None,
                    self.retraining_pipeline.run_retraining,
                )
                if not result.get("success"):
                    print("Retraining failed:", result.get("error", "unknown"))
                    continue
                print("Retraining finished, loading latest model from mlflow")
                self.model.reload_model()
                print("Latest model loaded successfully")
            except Exception as e:
                print(f"Retraining or model reload failed: {e}")

    async def process_data(self, json_data):
        """
        Process the data asynchronously.
        If prediction fails (e.g. corrupted model), try reloading model once and retry.
        """
        try:
            prediction = self.model.predict_fraud(json_data)
        except Exception as e:
            print(f"Prediction failed (possible corrupted model): {e}. Attempting model reload...")
            try:
                self.model.reload_model()
                prediction = self.model.predict_fraud(json_data)
            except Exception as e2:
                print(f"Reload and retry failed: {e2}")
                raise
            
        if prediction.prediction == 1:
            print(f"""
                Fraud detected! 
                Transaction ID: {json_data['TransactionID']}
                Processing time: {prediction.processing_time} ms
                Probability: {prediction.probability}
            """)
        else:
            print(f"""
                No fraud detected. 
                Transaction ID: {json_data['TransactionID']}
                Processing time: {prediction.processing_time} ms
                Probability: {prediction.probability}
            """)

        self.data_service.insert_transaction(
            transaction_id=json_data["TransactionID"],
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            transaction_data=json_data,
            prediction=prediction.prediction,
            probability=prediction.probability,
            processing_time=prediction.processing_time
        )
    
    async def close(self):
        self.consumer.close()
        self.data_service.close()
    
    async def run(self):
        stream_task = asyncio.create_task(self.read_data_stream())
        retrain_task = asyncio.create_task(self._check_for_retraining_loop())
        try:
            await asyncio.gather(stream_task, retrain_task)
        except asyncio.CancelledError:
            stream_task.cancel()
            retrain_task.cancel()
            try:
                await asyncio.gather(stream_task, retrain_task)
            except asyncio.CancelledError:
                pass
        except KeyboardInterrupt:
            print("Keyboard interrupt received, shutting down...")
            stream_task.cancel()
            retrain_task.cancel()
            try:
                await asyncio.gather(stream_task, retrain_task)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        finally:
            await self.close()
    
    
if __name__ == "__main__":
    postgres_data_service = PostgresDataService()
    retraining_pipeline = RetrainingPipeline(data_service=PostgresDataService())
    xgb_model = XGBoostModel()
    
    process_data_stream = ProcessDataStream(
        data_service=postgres_data_service, 
        model=xgb_model, 
        retraining_pipeline=retraining_pipeline
    )
    asyncio.run(process_data_stream.run())