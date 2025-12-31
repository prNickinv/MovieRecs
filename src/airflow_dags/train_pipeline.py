import os
import pickle
import logging
import requests
import pendulum
import pandas as pd
import clickhouse_connect
from airflow.decorators import dag, task
from rectools.dataset import Dataset
from rectools import Columns
from rectools.models import ImplicitALSWrapperModel, PopularModel
from implicit.als import AlternatingLeastSquares


# Path inside the Airflow container
MODELS_DIR = "/opt/airflow/models"
# Path to temporary training data (needed for rectools inference)
DATA_PATH = os.path.join(MODELS_DIR, "train_interactions.parquet")

# Connection configs
CH_HOST = "clickhouse"
ML_SERVICE_URL = "http://ml_service:8000/reload"

logger = logging.getLogger("airflow.task")

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": pendulum.duration(minutes=5),
}

@dag(
    dag_id="recsys_training_pipeline",
    default_args=default_args,
    description="Full training cycle: ClickHouse -> Train -> Reload Service",
    schedule="0 3 * * *",  # Run daily at 03:00 AM
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    tags=["mlops", "recsys"],
)
def train_pipeline():

    @task()
    def extract_data_from_clickhouse() -> str:
        """
        Reads interactions from ClickHouse and saves to Parquet.
        Returns the file path.
        """
        logger.info("Connecting to ClickHouse...")
        client = clickhouse_connect.get_client(host=CH_HOST, port=8123)
        
        query = """
        SELECT 
            user_id, 
            movie_id as item_id, 
            rating as weight, 
            timestamp as datetime 
        FROM interactions
        """
        
        logger.info("Executing query...")
        df = client.query_df(query)
        logger.info(f"Fetched {len(df)} rows.")
        
        # Write to a temporary file first, then rename it to the target path
        temp_path = DATA_PATH + ".tmp"
        logger.info(f"Writing to temporary file: {temp_path}")
        df.to_parquet(temp_path, index=False, engine='pyarrow')
        
        logger.info(f"Moving {temp_path} to {DATA_PATH}")
        os.replace(temp_path, DATA_PATH)
        
        return DATA_PATH

    @task()
    def train_and_save_models(data_path: str):
        """
        Trains iALS and Popular models using Rectools.
        Saves models for future use.
        """
        logger.info(f"Loading data from {data_path}...")
        df = pd.read_parquet(data_path)
        
        # Rectools Dataset preparation
        dataset = Dataset.construct(df)
        logger.info("Rectools Dataset constructed.")
        
        # Train Popular Model
        logger.info("Training Popular Model...")
        pop_model = PopularModel()
        pop_model.fit(dataset)
        
        # Train iALS Model
        logger.info("Training iALS Model...")
        ials_model = ImplicitALSWrapperModel(
            AlternatingLeastSquares(factors=200, alpha=40)
        )
        ials_model.fit(dataset)
        
        # Save models
        logger.info("Saving models...")
        
        pop_model.save(os.path.join(MODELS_DIR, "popular.pkl"))
        ials_model.save(os.path.join(MODELS_DIR, "ials.pkl"))
            
        with open(os.path.join(MODELS_DIR, "dataset.pkl"), "wb") as f:
            pickle.dump(dataset, f)
            
        logger.info("All models saved successfully.")

    @task()
    def notify_inference_service():
        """
        Sends a POST request to the inference service to reload models.
        """
        logger.info(f"Sending reload signal to {ML_SERVICE_URL}...")
        try:
            response = requests.post(ML_SERVICE_URL, timeout=10)
            response.raise_for_status()
            logger.info("Service reloaded successfully!")
        except Exception as e:
            logger.error(f"Failed to reload service: {e}")
            raise

    # Define Task Flow
    data_path = extract_data_from_clickhouse()
    train_task = train_and_save_models(data_path)
    notify_task = notify_inference_service()

    data_path >> train_task >> notify_task

dag = train_pipeline()
