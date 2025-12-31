import streamlit as st
import requests
import pandas as pd
import psycopg2
import json
import os
from kafka import KafkaProducer
from datetime import datetime
from src.utils.logger import logger

# Configuration
API_URL = "http://ml_service:8000/recommend"
PG_DSN = f"postgresql://{os.getenv('POSTGRES_USER', 'user')}:{os.getenv('POSTGRES_PASSWORD', 'password')}@postgres:5432/{os.getenv('POSTGRES_DB', 'recsys_db')}"
KAFKA_BOOTSTRAP_SERVERS = ['kafka:9092']
TOPIC_NAME = "interactions"
IMAGES_DIR = "/app/data/images"

# Utils functions

@st.cache_resource
def get_db_connection():
    return psycopg2.connect(PG_DSN)

@st.cache_resource
def get_kafka_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

def get_movie_details(movie_ids):
    """Fetches titles and genres from Postgres."""
    conn = get_db_connection()
    if not movie_ids:
        return pd.DataFrame()
    
    query = "SELECT movie_id, title, genres FROM movies WHERE movie_id IN %s"
    df = pd.read_sql(query, conn, params=(tuple(movie_ids),))
    # Sort to match the order of movie_ids from the recommendation
    df = df.set_index('movie_id').reindex(movie_ids).reset_index()
    return df

def send_feedback(user_id, movie_id, movie_title):
    """Sends a 'like' event to Kafka."""
    try:
        producer = get_kafka_producer()
        event = {
            "user_id": int(user_id),
            "movie_id": int(movie_id),
            "rating": 1, 
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        producer.send(TOPIC_NAME, value=event)
        producer.flush()
        logger.info(f"Feedback sent: {event}")
        st.toast(f"The movie {movie_title} has been liked! Enjoy watching it! 👍", icon="✅")
    except Exception as e:
        logger.error(f"Failed to send feedback: {e}")
        st.error("Feedback sending error")

# UI Layout

st.set_page_config(page_title="MovieRecs RecSys", layout="wide")
st.title("🎬 MovieRecs: Personal Movie Recommendations")

# Sidebar
with st.sidebar:
    st.header("User Control")
    if 'user_id' not in st.session_state:
        st.session_state.user_id = 1
        
    user_id = st.number_input("User ID", min_value=1, value=st.session_state.user_id, step=1, key='user_input')
    k_recs = st.slider("Number of recommendations", 1, 20, 8)
    
    if st.button("🔄 Reload Models"):
        try:
            resp = requests.post("http://ml_service:8000/reload")
            if resp.status_code == 200:
                st.success("Models reloaded!")
        except Exception as e:
            st.error(f"Error: {e}")


# Fetch data
if st.button("🚀 Get Recommendations", type="primary"):
    with st.spinner('Asking AI...'):
        try:
            # Request recommendations from ML service
            payload = {"user_id": user_id, "k": k_recs}
            response = requests.post(API_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            
            recs_ids = data['recs']
            model_type = data['model_type']
            
            # Fetch movie details from Postgres
            movies_df = get_movie_details(recs_ids)
            
            # Store in session state
            st.session_state['recs_df'] = movies_df
            st.session_state['model_type'] = model_type
            st.session_state['current_user'] = user_id
            
        except requests.exceptions.ConnectionError:
            st.error("ML Service unavailable. Is it running?")
        except Exception as e:
            st.error(f"Error: {e}")


# Display data
if 'recs_df' in st.session_state and not st.session_state['recs_df'].empty:
    
    model_type = st.session_state.get('model_type', 'unknown')
    st.success(f"Used Model: **{model_type}** for User {st.session_state['current_user']}")
    
    movies_df = st.session_state['recs_df']
    
    cols_per_row = 4
    rows = [movies_df.iloc[i:i+cols_per_row] for i in range(0, len(movies_df), cols_per_row)]
    
    for row in rows:
        cols = st.columns(cols_per_row)
        for index, (col, movie) in enumerate(zip(cols, row.itertuples())):
            with col:
                # Picture
                img_path = os.path.join(IMAGES_DIR, f"{movie.movie_id}.jpg")
                if os.path.exists(img_path):
                    st.image(img_path, use_container_width=True)
                
                st.subheader(movie.title)
                st.caption(movie.genres)
                
                # Like Button
                st.button(
                    "❤️ Like", 
                    key=f"btn_{movie.movie_id}",
                    on_click=send_feedback,
                    args=(st.session_state['current_user'], movie.movie_id, movie.title)
                )
