<!-- Improved compatibility of back to top link -->
<a id="readme-top"></a>

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]

<br />
<div align="center">
  <a href="https://github.com/Mielone2Good/real-time-fraud-detection-mlops">
    <img src="https://upload.wikimedia.org/wikipedia/commons/9/93/Amazon_Web_Services_Logo.svg" alt="AWS Logo" height="80">
  </a>

  <h3 align="center">Real-Time Fraud Detection System (E2E, MLOps)</h3>

  <p align="center">
    Production-style streaming fraud detection system with automated retraining and model registry.
    <br />
    <a href="https://github.com/Mielone2Good/real-time-fraud-detection-mlops"><strong>Explore the code »</strong></a>
    <br />
    <br />
    <a href="https://github.com/Mielone2Good/real-time-fraud-detection-mlops/issues/new?labels=bug">Report Bug</a>
    ·
    <a href="https://github.com/Mielone2Good/real-time-fraud-detection-mlops/issues/new?labels=enhancement">Request Feature</a>
  </p>

  <br />

  <!-- HERO METRICS -->
  <p align="center">
    <strong>⚡ ~303 tx/sec</strong> ·
    <strong>⏱️ ~1.9 ms avg prediction</strong> ·
    <strong>🔁 Auto-retraining</strong> ·
    <strong>☁️ Deployed on AWS EC2</strong>
  </p>
</div>



## 🖼️ System Overview (At a Glance)

<!-- TU DAJESZ DIAGRAM AWS + DOCKER NA SAMEJ GÓRZE -->
<img width="1050" alt="Architecture Overview" src="PUT_ARCHITECTURE_DIAGRAM_HERE" />

Kafka → Fraud Detection Service → PostgreSQL  
↘ MLflow (Model Registry)  
↘ Streamlit Dashboard



## 📌 About The Project

An **end-to-end, production-style fraud detection system** processing credit card transactions in real time.

Transactions are streamed through Kafka, scored by an **XGBoost model**, stored in PostgreSQL, monitored via dashboards, and **automatically retrained** once enough labeled data is available.  
The entire stack is containerized with Docker and deployed on **AWS EC2**.

Focus: **real systems, real trade-offs, real MLOps** — not notebook-only ML.



## 🧠 Fraud Detection Logic (High-Level)

Incoming transactions are scored with a probabilistic fraud model.  
Predictions, probabilities, and metadata are persisted for monitoring and retraining.

The model is trained on a **highly imbalanced dataset**, optimized for **precision and recall** instead of raw accuracy.

Key principles:
- Streaming inference (Kafka consumer)
- Cost-aware evaluation metrics
- Continuous model improvement via retraining



## 🗺️ Architecture Overview

<!-- TU MOŻESZ DAĆ DRUGI, BARDZIEJ TECHNICZNY DIAGRAM -->
<img width="1050" alt="Detailed Architecture" src="PUT_DETAILED_ARCHITECTURE_IMAGE_HERE" />

- Kafka (Redpanda) for event streaming  
- XGBoost-based fraud detection service  
- PostgreSQL for predictions and labels  
- MLflow for experiments and model registry  
- Streamlit for real-time monitoring  



## ⚙️ Core Components

### Infrastructure & Services
| Component | Purpose |
|-|--|
| **Kafka (Redpanda)** | Real-time transaction streaming |
| **Fraud Detection Service** | XGBoost inference + Kafka consumer |
| **PostgreSQL** | Transaction storage & ground-truth labels |
| **MLflow** | Experiment tracking & model registry |
| **FastAPI** | Manual retraining & health endpoints |
| **Streamlit** | Live monitoring dashboard |
| **Docker** | Fully containerized system |
| **AWS EC2** | Production-like deployment |



## 🐳 Docker Deployment

<!-- SCREEN Z DOCKER DESKTOP / docker compose -->
<img width="1050" alt="Docker Compose Layout" src="PUT_DOCKER_LAYOUT_IMAGE_HERE" />

- Single `docker compose up` spins up the full stack
- Stateless services, reproducible environment
- Clear separation between inference, retraining, and monitoring



## 🚀 Performance

**Streaming test results:**
- ⚡ **Throughput**: ~303 transactions/sec  
- ⏱️ **Avg processing time**: **1.92 ms**  
- 🧾 **Transactions processed**: 9,692  
- 🚨 **Fraud detected**: 1,529 (**15.78%**)

**Retraining metrics:**
- Precision: **1.00**
- Recall: **0.95**
- F1-score: **0.97**
- Average Precision: **0.99**



## 🔁 Automated Retraining

- Retraining triggered when **≥500 labeled transactions** are available
- Class imbalance handled via weighting
- New model registered and promoted to **Production** in MLflow
- Inference service **hot-reloads** the model (no downtime)

Manual retraining endpoint:
POST /retrain




## 🧪 MLflow – Model Lifecycle

<!-- SCREEN Z MLFLOW -->
<img width="1050" alt="MLflow Dashboard" src="PUT_MLFLOW_DASHBOARD_IMAGE_HERE" />

- Experiment tracking
- Metric comparison across runs
- Model versioning
- Production stage promotion



## 📊 Monitoring Dashboard

<!-- SCREEN Z STREAMLIT -->
<img width="1050" alt="Streamlit Dashboard" src="PUT_STREAMLIT_DASHBOARD_IMAGE_HERE" />

Live metrics:
- Total transactions
- Fraud rate
- Average fraud probability
- Throughput (tx/sec)
- Inference latency



## 🎥 Demo

<!-- LINK DO FILMIKU -->
**Short system demo:**  
PUT_DEMO_VIDEO_LINK_HERE



## 🧾 Data Storage

### Table: `transactions`
| Column | Type | Description |
|------|------|------------|
| transaction_id | String | Unique transaction ID |
| timestamp | Timestamp | Processing time |
| transaction_data | JSONB | Raw transaction features |
| prediction | Integer | Fraud / Non-fraud |
| probability | Float | Fraud probability |
| processing_time | Float | Inference latency |
| isReallyFraud | Integer | Ground-truth label (optional) |



## 🎯 Use Cases

- Fraud detection systems  
- Real-time ML inference  
- MLOps & retraining pipelines  
- Streaming analytics platforms  



<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/github/contributors/Mielone2Good/real-time-fraud-detection-mlops.svg?style=for-the-badge
[contributors-url]: https://github.com/Mielone2Good/real-time-fraud-detection-mlops/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/Mielone2Good/real-time-fraud-detection-mlops.svg?style=for-the-badge
[forks-url]: https://github.com/Mielone2Good/real-time-fraud-detection-mlops/network/members
[stars-shield]: https://img.shields.io/github/stars/Mielone2Good/real-time-fraud-detection-mlops.svg?style=for-the-badge
[stars-url]: https://github.com/Mielone2Good/real-time-fraud-detection-mlops/stargazers
[issues-shield]: https://img.shields.io/github/issues/Mielone2Good/real-time-fraud-detection-mlops.svg?style=for-the-badge
[issues-url]: https://github.com/Mielone2Good/real-time-fraud-detection-mlops/issues
[license-shield]: https://img.shields.io/github/license/Mielone2Good/real-time-fraud-detection-mlops.svg?style=for-the-badge
[license-url]: https://github.com/Mielone2Good/real-time-fraud-detection-mlops/blob/main/LICENSE
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://www.linkedin.com/in/mikolajjaros/
