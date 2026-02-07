
import xgboost as xgb
import pandas as pd
import numpy as np
import time
from abc import ABC, abstractmethod
import mlflow
import os
from dotenv import load_dotenv

load_dotenv()

class FraudDetectionModel(ABC):
    @abstractmethod
    def predict_fraud(self, data, threshold=0.5):
        pass

    @abstractmethod
    def get_latest_model(self):
        pass
    
    @abstractmethod
    def reload_model(self) -> None:
       pass

class XGBoostModel(FraudDetectionModel):
    def __init__(self):
        self.mlflow = mlflow
        _uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        self.mlflow.set_tracking_uri(_uri)
        self.mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT", "fraud_detection"))
        self.mlflow_client = self.mlflow.MlflowClient(tracking_uri=_uri)
        self.model = self.get_latest_model()

    def predict_fraud(self, data, threshold=0.5):
        """
        Predicts fraud for a transaction.
        
        Args:
            data: Transaction data dictionary
            threshold: Decision threshold (default 0.5)
        
        Returns:
            Response with binary prediction (0/1) and probability
        """
        data_to_predict = pd.DataFrame([data]).drop(columns=["TransactionID"])
        start_time = time.time() * 1000 
        raw_prediction = self.model.predict(xgb.DMatrix(data_to_predict))[0]
        end_time = time.time() * 1000 
        
        if raw_prediction > 1.0 or raw_prediction < 0.0:
            probability = 1 / (1 + np.exp(-raw_prediction))
        else:
            probability = raw_prediction 
          
        binary_prediction = 1 if probability >= threshold else 0
        
        return Response(
            prediction=binary_prediction,
            probability=round(float(probability), 3),
            processing_time=round(end_time - start_time, 4) 
        )
    
    def get_latest_model(self):
        """Load latest model from MLflow Production; fallback to local file if MLflow fails."""
        try:
            model = mlflow.xgboost.load_model("models:/fraud_detection_model/Production")
            self.model = model
            print("Model loaded from MLflow Production, type:", type(model))
            return model
        except Exception as e:
            print("MLflow load failed, trying backup file:", e)
            try:
                data_dir = os.getenv("DATA_DIR", "data")
                fallback_path = os.path.join(data_dir, "models", "latest_model.json")
                model = xgb.Booster()
                model.load_model(fallback_path)
                self.model = model
                print("Model loaded from backup file, type:", type(model))
                return model
            except Exception as e2:
                print("Backup model load also failed:", e2)
                if self.model is not None:
                    print("Keeping previous model in memory.")
                    return self.model
                raise RuntimeError("No model available and load failed") from e2

    def reload_model(self) -> None:
        """
        Reload the latest model (from MLflow or backup) into this wrapper.
        Call this after retraining so the data stream uses the new model.
        On failure, keeps the current model if one was already loaded.
        """
        try:
            self.get_latest_model()
        except RuntimeError as e:
            print("reload_model failed, keeping current model:", e)

class Response:
    def __init__(self, prediction: int, probability: float, processing_time: float):
        self.prediction = int(prediction)  
        self.probability = float(probability)
        self.processing_time = processing_time
    
    def to_dict(self):
        return {
            "prediction": self.prediction,
            "probability": self.probability,
            "processing_time": self.processing_time
        }   