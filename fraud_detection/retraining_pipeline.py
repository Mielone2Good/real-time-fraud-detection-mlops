import mlflow
import mlflow.xgboost
import os
import tempfile
from dotenv import load_dotenv
from sklearn.metrics import accuracy_score
import xgboost as xgb
from sklearn.model_selection import train_test_split
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import f1_score, roc_curve, precision_score, recall_score
from sklearn.metrics import average_precision_score
from fraud_detection.data_manager import DataService, PostgresDataService
import threading

load_dotenv()
RETRAINING_MIN_SAMPLES = 500


class RetrainingPipeline:
    def __init__(self, data_service: DataService):
        self.mlflow = mlflow
        self.mlflow_client = self.mlflow.MlflowClient(
            tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        )
        self.data_service = data_service
        self.mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
        self.mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT", "fraud_detection"))
        self.params = {
            'objective': 'binary:logistic',
            'max_depth': 6,
            'learning_rate': 0.05,
            'eval_metric': 'aucpr',
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 3
        }
        self._retraining_lock = threading.Lock()
        self._retraining_in_progress = False

    def _get_training_data(self) -> tuple[xgb.DMatrix, xgb.DMatrix]:
        """
        Gets the training data from the data service.
        
        Returns Tuple containing the training and test data.
        """
        transactions = self.data_service.get_transactions()
        transactions = [t for t in transactions if t.get("isreallyfraud") is not None]
        
        if not transactions:
            raise ValueError("No transactions with isreallyfraud labels found")
        
        df = pd.DataFrame(transactions)
        
        if 'transaction_data' in df.columns:
            transaction_data_df = pd.json_normalize(df['transaction_data'])
            df = pd.concat([df, transaction_data_df], axis=1)
            df = df.drop(columns=['transaction_data'])
        
        cols_to_drop = ["transaction_id", "timestamp", "prediction", "probability", "processing_time"]
        existing_cols = [col for col in cols_to_drop if col in df.columns]
        df = df.drop(columns=existing_cols, errors='ignore')
        
        if "isreallyfraud" not in df.columns:
            raise ValueError("isreallyfraud column not found in data")
        
        X = df.drop(columns=["isreallyfraud"])
        y = df["isreallyfraud"]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        xgb_train = xgb.DMatrix(X_train, y_train, enable_categorical=True)
        xgb_test = xgb.DMatrix(X_test, y_test, enable_categorical=True)
        return xgb_train, xgb_test, y_test
       
    
    def should_retrain(self) -> bool:
        """
        Checks if retraining is needed (enough labeled data and no retraining in progress).
        Does not start retraining; use run_retraining() for that.
        
        Returns:
            bool: True if we have enough data to retrain and no retraining is running.
        """
        with self._retraining_lock:
            if self._retraining_in_progress:
                return False
        transactions = self.data_service.get_transactions()
        labeled = [row for row in transactions if row.get("isreallyfraud") is not None]
        if len(labeled) < RETRAINING_MIN_SAMPLES:
            return False
        return True

    def get_labeled_count(self) -> int:
        """Returns the number of transactions that have isreallyfraud set."""
        transactions = self.data_service.get_transactions()
        return sum(1 for row in transactions if row.get("isreallyfraud") is not None)

    def request_retraining(self) -> bool:
        """
        Alias for should_retrain() for backward compatibility.
        Returns True if retraining should be run (enough data, not already running).
        """
        return self.should_retrain()

    def run_retraining(self) -> dict:
        """
        Runs retraining synchronously. Call this from a thread or via
        run_in_executor() so the event loop is not blocked.
        When this returns, the new model is in MLflow Production, the caller
        should then reload the model
        """
        with self._retraining_lock:
            if self._retraining_in_progress:
                return {"success": False, "error": "Retraining already in progress"}
            self._retraining_in_progress = True
        print("Attempting retraining...")
        try:
            result = self._retrain_model()
            return result
        except Exception as e:
            print(f"Retraining failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            with self._retraining_lock:
                self._retraining_in_progress = False
    
    def _retrain_model(self) -> dict:
        """
        Retrains the model and saves it to MLflow.
        
        Returns:
            dict: Dictionary containing the success status and the run ID.
        """
        xgb_train, xgb_test, y_test = self._get_training_data()
        y_test_labels = y_test
        
        xgb_train_labels = xgb_train.get_label()
        self.params['scale_pos_weight'] = len(xgb_train_labels[xgb_train_labels==0]) / len(xgb_train_labels[xgb_train_labels==1])
        
        with self.mlflow.start_run() as run:
            print("Training model...")
            run_id = run.info.run_id
            self.mlflow.log_params(self.params)
            model = xgb.train(
                params=self.params,
                dtrain=xgb_train,
                num_boost_round=500,
                evals=[(xgb_train, 'train'), (xgb_test, 'eval')],
                early_stopping_rounds=20,
                verbose_eval=10
            )
            print("Model trained successfully")
            predictions = (model.predict(xgb_test) > 0.5).astype(int)
            self.mlflow.log_metrics({
                'accuracy': accuracy_score(y_test_labels, predictions),
                'f1_score': f1_score(y_test_labels, predictions),
                'precision': precision_score(y_test_labels, predictions),
                'recall': recall_score(y_test_labels, predictions),
                'average_precision': average_precision_score(y_test_labels, model.predict(xgb_test))
            })
            with tempfile.TemporaryDirectory() as tmp_dir:
                model_path = os.path.join(tmp_dir, "model")
                mlflow.xgboost.save_model(xgb_model=model, path=model_path)
                mlflow.log_artifacts(model_path, artifact_path="model")
            print("Model saved to MLflow successfully")
            
            try:
                self._register_to_production(run_id)
                print("Model registered to production successfully")
            except Exception as e:
                print(f"Warning: Could not register model: {e}")

        return {"success": True, "run_id": run_id}
        
    def _register_to_production(self, run_id: str) -> None:
        model_uri = f"runs:/{run_id}/model"
        model_version = self.mlflow.register_model(
            model_uri=model_uri,
            name="fraud_detection_model"
        )
        self.mlflow_client.transition_model_version_stage(
            name="fraud_detection_model",
            version=model_version.version,
            stage="Production"
        )
        
        
if __name__ == "__main__":
    postgres_data_service = PostgresDataService()
    
    retraining_pipeline = RetrainingPipeline(data_service=postgres_data_service)
    status = retraining_pipeline.retrain_model()
    
    print(status)
    postgres_data_service.close()