# 🎬 MovieRecs: Movie Recommender System

![Python](https://img.shields.io/badge/Python-3.10-blue) ![Docker](https://img.shields.io/badge/Docker-Compose-orange) ![FastAPI](https://img.shields.io/badge/FastAPI-0.128-green) ![Airflow](https://img.shields.io/badge/Airflow-2.8.1-red) ![Grafana](https://img.shields.io/badge/Grafana-Monitoring-orange) ![Kafka](https://img.shields.io/badge/Kafka-7.5-yellow) ![ClickHouse](https://img.shields.io/badge/ClickHouse-DB-purple) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-DB-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-1.52.2-red)

by Nikita Artamonov

**MovieRecs** is a MLOps Movie Recommender System project. It implements data ingestion, real-time inference and feedback loop, scheduled model retraining and monitoring.

The project one-pager is available [here](docs/one_pager.md).

---

## 💼 Problem Statement & Business Value

### The Problem
Users may **struggle selecting content** on streaming platforms due to the overwhelming number of choices, thus spending excessive time on content discovery. New users may abandon the platform without watching a single movie due to the lack of handling the  **Cold Start** problem. These issues may lead to **increased Churn Rate** and **lost revenue**.

### The Solution
**MovieRecs** is a hybrid recommendation system that:
1.  **Personalizes Experience:** Uses iALS to recommend movies based on user preferences.
2.  **Handles Cold Start:** Instantly falls back to a popularity-based model for new users.
3.  **Adapts via Feedback:** Captures user interactions (likes) to continuously refine the system.

### Business Value
*   **Reduction** in content discovery time.
*   **Increased CTR** (Click-Through Rate) in recommendation feed.
*   **Higher Retention:** keeps users engaged by showing relevant content immediately.

---

## 📐 Project Architecture

![Architecture Diagram](docs/architecture.png)

**NB!** Observability components are omitted for readability.

---

## 🏗 Tech Stack

*   **ML Core:** `Rectools`, `Implicit`. iALS + Popularity-based model.
*   **API Service:** `FastAPI`. Supports **recommendation generation** and **model reload**.
*   **Streaming:** `Kafka`, `Zookeeper`.  Collecting real-time feedback.
*   **Storage:**
    *   `ClickHouse`: Storing interaction events for training.
    *   `PostgreSQL`: Metadata storage (Titles, Genres, etc.).
*   **Orchestration:** `Apache Airflow`. Scheduled daily retraining.
*   **Observability:**
    *   `Grafana`.
    *   `Prometheus`.
    *   `Loki`.
    *   `Promtail`.
*   **UI:** `Streamlit`. Interactive interface for demonstration and feedback collection.
*   **Containerization:** `Docker` & `Docker Compose`. Project assembling and deployment.

---

## 📂 Repository Structure

```text
MovieRecs/
├── configs/                 # Configuration files for monitoring stack       
│   ├── grafana/             # Dashboards & Datasources provisioning
│   ├── loki/
│   ├── prometheus/
│   └── promtail/
│
├── data/
│   ├── raw/                 # Raw MovieLens dataset (.dat)
│   ├── images/              # Movie poster images (.jpg)
│   ├── clickhouse/
│   └── postgres/
│
├── models/                  # Trained ML models (.pkl)
├── logs/
│
├── src/
│   ├── airflow_dags/        # Scheduled retraining pipelines (DAGs)
│   ├── database/            # SQL init scripts (init_pg.sql, init_ch.sql)
│   ├── etl/                 # Initial data loader & Kafka consumer
│   ├── service/             # FastAPI Inference Service
│   ├── ui/                  # Streamlit UI
│   ├── utils/               # Logger
│   └── training/            # Initial models training notebook
│
├── docs/                    # One-pager & architecture diagram
├── docker-compose.yml       # Orchestration of services
├── Dockerfile               # Main Dockerfile
├── Dockerfile.airflow       # Dockerfile for Airflow
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🚀 Start Guide

### Launch the System
Run the entire stack with a single command:

```bash
docker-compose up -d --build
```

### Initialization Process
1.  **Databases** (PostgreSQL, ClickHouse) will start and initialize schemas.
2.  **Data Loader** container will start, parse the `.dat` files, load them into DBs, and exit.
3.  **Kafka** will start and create the `interactions` topic.
4.  **ML Service** & **Kafka Consumer** & **Streamlit UI** will start.
5.  **Airflow** will start and launch its webserver and scheduler.
6.  **Prometheus**, **Loki**, **Promtail** and **Grafana** will start for monitoring and visualization.

---

## 🖥️ Access Points

Once running, access the services via your browser:

| Service | URL | Credentials (if any) | Description |
| :--- | :--- | :--- | :--- |
| **User Interface** | `http://localhost:8501` | - | Streamlit App to browse movies |
| **Grafana** | `http://localhost:3000` | `admin` / `admin` | Monitoring Dashboards |
| **Airflow** | `http://localhost:8080` | `admin` / `admin` | Retraining Orchestration |

**NB!** It may take a little longer for Airflow webserver to become accessible.

---

## 🛠️ Usage Scenarios

### 1. Getting Recommendations (Inference)
1.  Go to the **Streamlit UI** (`localhost:8501`).
2.  Enter a User ID (e.g., `1`).
3.  Click **"Get Recommendations"**.
4.  *Under the hood:* The App calls the FastAPI service, which loads the iALS model (or Popular model for new users) and returns IDs. PostgreSQL provides titles and genres, movie posters are fetched from the `data/images` directory.

### 2. The Feedback Loop (Retraining)
1.  In the UI, click **"❤️ Like"** on any movie.
2.  *Under the hood:* The event is sent to **Kafka**.
3.  The **Consumer** service reads the event and inserts it into **ClickHouse**.
4.  Check **Grafana** (`localhost:3000`) -> "MovieRecs Monitoring". You will see the "Likes per Minute" spike.

### 3. Triggering Retraining
1.  Go to **Airflow** (`localhost:8080`).
2.  Enable the `recsys_training_pipeline` DAG.
3.  Trigger it manually (Play button).
4.  *Under the hood:* Airflow extracts data from ClickHouse, trains new models, saves `.pkl` files, and calls `/reload` on the ML Service.
5.  The ML Service reloads the models.

---

## 📊 Monitoring

The project implements a dashboard via **Grafana**, that includes the following graphs:

1.  **Requests per Second**
2.  **Average Latency** 
3.  **Error Logs**
4.  **Likes per Minute**

To view the dashboard, log in to Grafana and go to **Open Menu -> Dashboards -> MovieRecs Monitoring**.

---
