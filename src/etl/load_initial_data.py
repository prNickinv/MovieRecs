import os
import sys
import time
import pandas as pd
from sqlalchemy import create_engine, text
import clickhouse_connect
from src.utils.logger import logger

# Configuration
# Inner container paths
DATA_DIR = "/app/data/raw"
MOVIES_FILE = os.path.join(DATA_DIR, "movies.dat")
USERS_FILE = os.path.join(DATA_DIR, "users.dat")
RATINGS_FILE = os.path.join(DATA_DIR, "ratings.dat")

# Database Connections
PG_USER = os.getenv("POSTGRES_USER", "user")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
PG_HOST = os.getenv("POSTGRES_HOST", "postgres")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")
PG_DB = os.getenv("POSTGRES_DB", "recsys_db")

CH_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CH_PORT = os.getenv("CLICKHOUSE_PORT", "8123")


def get_pg_engine(retries=10, delay=3):
    db_url = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
    engine = create_engine(db_url)
    
    for i in range(retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except Exception as e:
            logger.error(f"Unexpected error connecting to Postgres: {e}")
            time.sleep(delay)
            
    raise ConnectionError("Could not connect to Postgres after multiple attempts")

def get_clickhouse_client(retries=10, delay=3):
    for i in range(retries):
        try:
            client = clickhouse_connect.get_client(host=CH_HOST, port=int(CH_PORT))
            client.query("SELECT 1")
            return client
        except Exception as e:
            logger.warning(f"ClickHouse not ready yet (Attempt {i+1}/{retries}). Waiting... Error: {e}")
            time.sleep(delay)
    raise ConnectionError("Could not connect to ClickHouse after multiple attempts")


def load_movies_to_postgres():
    engine = get_pg_engine()

    # Check if data already exists
    with engine.connect() as conn:
        result = conn.execute(text("SELECT count(*) FROM movies"))
        count = result.scalar()
        if count > 0:
            logger.info(f"Movies table already has {count} rows. Skipping load.")
            return

    logger.info("Loading Movies to PostgreSQL...")
    if not os.path.exists(MOVIES_FILE):
        logger.error(f"File not found: {MOVIES_FILE}")
        return

    try:
        df = pd.read_csv(
            MOVIES_FILE, sep='::', engine='python', header=None, 
            names=['movie_id', 'title', 'genres'], encoding='latin-1'
        )
        df.to_sql('movies', engine, if_exists='append', index=False)
        logger.info(f"Successfully loaded {len(df)} movies.")
    except Exception as e:
        logger.error(f"Failed to load movies: {e}")
        raise


def load_users_to_postgres():
    engine = get_pg_engine()
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT count(*) FROM users"))
        count = result.scalar()
        if count > 0:
            logger.info(f"Users table already has {count} rows. Skipping load.")
            return

    logger.info("Loading Users to PostgreSQL...")
    if not os.path.exists(USERS_FILE):
        logger.error(f"File not found: {USERS_FILE}")
        return

    try:
        df = pd.read_csv(
            USERS_FILE, sep='::', engine='python', header=None, 
            names=['user_id', 'gender', 'age', 'occupation', 'zip_code'], encoding='latin-1'
        )
        df.to_sql('users', engine, if_exists='append', index=False)
        logger.info(f"Successfully loaded {len(df)} users.")
    except Exception as e:
        logger.error(f"Failed to load users: {e}")
        raise

def load_ratings_to_clickhouse():
    #client = clickhouse_connect.get_client(host=CH_HOST, port=int(CH_PORT))
    client = get_clickhouse_client()
    
    # Check if data already exists
    count = client.query("SELECT count() FROM interactions").result_rows[0][0]
    if count > 0:
        logger.info(f"Interactions table already has {count} rows. Skipping load.")
        return

    logger.info("Loading Ratings to ClickHouse...")
    if not os.path.exists(RATINGS_FILE):
        logger.error(f"File not found: {RATINGS_FILE}")
        return

    try:
        df = pd.read_csv(
            RATINGS_FILE, sep='::', engine='python', header=None, 
            names=['user_id', 'movie_id', 'rating', 'timestamp'], encoding='latin-1'
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df['rating'] = df['rating'].astype(int)

        client.insert_df('interactions', df)
        logger.info(f"Successfully loaded {len(df)} ratings.")
    except Exception as e:
        logger.error(f"Failed to load ratings: {e}")
        sys.exit(1)

def main():
    logger.info("Initializing Data Ingestion Pipeline...")
    load_movies_to_postgres()
    load_users_to_postgres()
    load_ratings_to_clickhouse()
    logger.info("Pipeline finished successfully.")

if __name__ == "__main__":
    main()
