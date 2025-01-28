# Automatic Speech Recognition (ASR) System for Preference Grammar (PG)

## Overview

This project implements a scalable and efficient **Automatic Speech Recognition (ASR)** system using a **CNN-RNN hybrid architecture**. The system is designed to process and transcribe speech data in Nigerian English and other English variants. It includes model development, deployment, API management, and monitoring to support a robust, production-ready ASR solution. 

This project provides the code implementation of a ([research on Preference Grammar](https://www.researchgate.net/publication/365805517_New_Norms_in_English_Teaching_and_Learning_The_Preference_Grammar_Approach?_sg%5B0%5D=0J7PX1jGH0eiGKf-HwAowaO64krruhbJnpAjB25PcXNb9Zxtw0vgkNyIgf_iKLarogPkeT0DkX1Y-TiYyWPujAyapnJ_0wWLKsSXmu5k.gef2Mzc-Yn25tLCp-fOhW0yn6xN3-7f41smQnChkMhyolECkWyDgxnc3sFCcP-sLUcHUw24d0a3vkfPcvxvBqQ&_tp=eyJjb250ZXh0Ijp7ImZpcnN0UGFnZSI6Il9kaXJlY3QiLCJwYWdlIjoicHJvZmlsZSIsInByZXZpb3VzUGFnZSI6InByb2ZpbGUiLCJwb3NpdGlvbiI6InBhZ2VDb250ZW50In19))

---

## Features

- **ASR Model:** CNN-RNN hybrid architecture for accurate transcription.
- **Scalable Infrastructure:** Leveraging AWS services (S3, Elastic Beanstalk, SageMaker) for model deployment and storage.
- **API Management:** Node.js backend for seamless interaction between users and the model.
- **Storage:** Structured and unstructured data storage with PostgreSQL (AWS RDS) and MongoDB.
- **Monitoring & Logging:** Comprehensive monitoring using Prometheus, Grafana, and the ELK stack.
- **Containerization:** Dockerized components for easy deployment and portability.
- **Interoperability:** Optional ONNX format support for serving models across different frameworks.

---

## Tech Stack

### Model Development
- **Programming Language:** Python
- **Architecture:** CNN-RNN hybrid for ASR
- **Frameworks/Libraries:** TensorFlow, PyTorch
- **Feature Extraction:** MFCC

### API Management
- **Backend:** Node.js with Express.js (TypeScript)
- **API Interaction:** RESTful endpoints for uploading audio and retrieving transcriptions

### Deployment
- **Model Serving:** 
  - AWS SageMaker or Elastic Beanstalk
  - TensorFlow Serving or TorchServe
  - ONNX Runtime (optional for framework interoperability)
- **Containerization:** Docker for creating isolated environments

### Storage
- **Audio & Artifacts:** AWS S3 (optional: Azure Blob Storage for ML experiments)
- **Relational Database:** PostgreSQL (AWS RDS) for structured metadata
- **NoSQL Database:** MongoDB for unstructured metadata
- **Message Queue:** AWS Elasticache (Redis) for processing audio tasks

### Monitoring & Logging
- **Monitoring:** AWS CloudWatch, Prometheus, Grafana
- **Logging:** ELK stack (Elasticsearch, Logstash, Kibana)

### Model Training
- **Primary Platform:** Google Colab (with GPU/TPU support)
- **Scalable Training:** AWS EC2 GPU instances or AWS SageMaker

---
## Repo Structure

project-root/
├── server/                 # Backend server folder
│   ├── Dockerfile          # Dockerfile for the server
│   ├── package.json        # Node.js dependencies for the server
│   ├── src/                # Server source code
│   │   ├── index.ts        # Main server entry point
│   │   ├── routes/         # API route handlers
│   │   ├── controllers/    # Controller logic
│   │   ├── middleware/     # Middleware logic (e.g., authentication)
│   │   └── utils/          # Utility functions
│   └── tests/              # Server-specific tests
│       └── test_server.ts  # Example test
│
├── model/                  # Model development folder
│   ├── Dockerfile          # Dockerfile for the model
│   ├── requirements.txt    # Python dependencies
│   ├── app.py              # Python app entry point
│   ├── src/                # Model source code
│   │   ├── training/       # Training scripts and configs
│   │   ├── inference.py    # Model inference script
│   │   ├── preprocess.py   # Data preprocessing logic
│   │   └── utils.py        # Helper functions
│   └── tests/              # Model-specific tests
│       └── test_model.py   # Example test
│
├── shared/                 # Shared libraries or utilities
│   ├── config/             # Shared configuration files
│   │   └── settings.yaml   # Application-wide settings
│   └── utils/              # Shared utility functions
│       └── logger.py       # Example logger utility
│
├── docker-compose.yml      # For orchestrating multiple services
├── .env                    # Environment variables
├── .gitignore              # Git ignore file
└── README.md               # Project overview and documentation

## Project Setup

### Prerequisites

1. **Python** (>= 3.8)
2. **Node.js** (>= 18.x) with npm/yarn
3. **Docker** (latest version)
4. **AWS Account** with necessary services enabled
5. **Google Colab Account** for initial model training

---

## Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/Oluwademiladeogo/ASR-PG
cd ASR-PG
```

### Step 2: Install Dependencies
#### Backend (Node.js):
```bash
cd backend
npm install
```

#### Model Development (Python):
```bash
cd model
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Create a `.env` file in both the `backend` and `model` directories with the following:
```env
# General Configuration
NODE_ENV=development
PORT=3000

# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
S3_BUCKET_NAME=your_bucket_name

# Database Configuration
POSTGRES_USER=your_postgres_user
POSTGRES_PASSWORD=your_postgres_password
POSTGRES_DB=your_database_name
MONGO_URI=your_mongo_uri
```

### Step 4: Docker Setup
Build and run Docker containers:
```bash
docker-compose up --build
```

---

## Usage

### API Endpoints
#### Upload Audio
**POST** `/api/audio/upload`  
Upload an audio file for transcription.

**Body:** Multipart/form-data  
- `file`: Audio file in `.wav` or `.mp3` format

#### Get Transcription
**GET** `/api/audio/transcription/:id`  
Retrieve the transcription for the uploaded audio file.

---

## Development Workflow

### Feature Development
1. **Create a Branch:**
   ```bash
   git checkout -b feature/<feature-name>
   ```
2. **Commit Changes:**
   ```bash
   git add .
   git commit -m "Add feature: <feature-description>"
   ```
3. **Push to Remote:**
   ```bash
   git push origin feature/<feature-name>
   ```
4. **Create Pull Request** on GitHub.

### CI/CD Integration
- **GitHub Actions** for automated testing, linting, and deployments.
- **Dockerized Pipelines** for seamless integration.

---

## Monitoring and Logging

### Prometheus and Grafana
- **Prometheus:** Collects metrics from the API and model server.
- **Grafana:** Visualizes metrics in customizable dashboards.

### ELK Stack
- **Elasticsearch:** Centralized log storage.
- **Logstash:** Processes and transforms logs.
- **Kibana:** Visualizes logs for debugging and insights.

---

## Roadmap

### Phase 1: Setup
- Initialize GitHub repository and CI/CD pipelines
- Configure Docker environment
- Gather and preprocess datasets

### Phase 2: Model Development
- Implement CNN-RNN architecture
- Extract speech features (MFCC)
- Train and evaluate the model on Nigerian English datasets

### Phase 3: Deployment
- Dockerize the model and API
- Deploy model to AWS SageMaker or Elastic Beanstalk
- Implement TensorFlow Serving or TorchServe

### Phase 4: API Development
- Create RESTful endpoints
- Integrate API with model server
- Implement error handling and validation

### Phase 5: Storage and Monitoring
- Configure AWS S3, RDS, and MongoDB
- Set up Redis for queuing
- Integrate Prometheus, Grafana, and ELK stack

### Phase 6: Testing and Optimization
- Write unit and system tests
- Perform stress and load testing
- Optimize model and API performance

---

## Contributing

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Submit a pull request with a detailed description.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## Contact

For questions or collaboration:
- **Email:** bickerstethdemilade@gmail.com
- **GitHub:** [Oluwademiladeogo](https://github.com/Oluwademiladeogo)

--- 