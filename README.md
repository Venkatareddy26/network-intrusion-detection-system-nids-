# Network Intrusion Detection System (NIDS)

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)

Production-grade Network Intrusion Detection System with XGBoost ML classifier, SHAP explainability, and real-time alerting dashboard.

## 🎯 Overview

NIDS is an AI-powered network security solution that detects and classifies cyber attacks in real-time:
- **Normal Traffic**
- **DoS (Denial of Service)**
- **Port Scan**
- **Brute Force**
- **Data Exfiltration**

### Key Features

- ✅ **XGBoost Classifier** with SMOTE for handling class imbalance
- ✅ **SHAP Explainability** - Understand why each alert was triggered
- ✅ **Real-time Detection** - < 50ms inference latency
- ✅ **Production-Ready API** - FastAPI with authentication, rate limiting, monitoring
- ✅ **Live Dashboard** - Streamlit-based visualization
- ✅ **Docker & Kubernetes** - Ready for cloud deployment
- ✅ **Comprehensive Testing** - Unit and integration tests
- ✅ **Security Hardened** - Input validation, rate limiting, audit logging

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or 3.11
- Docker & Docker Compose (for containerized deployment)
- 4GB RAM minimum
- CICIDS2017 dataset (for training)

### Installation

```bash
# Clone repository
git clone https://github.com/Venkatareddy26/network-intrusion-detection-system-nids-.git
cd network-intrusion-detection-system-nids-

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration
```

### Training the Model

```bash
# Download CICIDS2017 dataset and place in data/CICIDS2017.csv
# Then train the model
python train_model.py

# Model will be saved to models/nids_model.pkl
```

### Running Locally

```bash
# Terminal 1: Start API server
python -m uvicorn src.nids.api.main_v2:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start dashboard
streamlit run src/nids/dashboard/app.py

# Access:
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Dashboard: http://localhost:8501
```

### Running with Docker

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Access:
# - API: http://localhost:8000
# - Dashboard: http://localhost:8501
# - Grafana: http://localhost:3000 (admin/admin)
# - Prometheus: http://localhost:9090
```

## 📊 API Usage

### Health Check

```bash
curl http://localhost:8000/health
```

### Predict Attack

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "features": {
      "flow_duration": 1000.0,
      "total_fwd_packets": 10,
      "total_bwd_packets": 5,
      "total_length_fwd_packets": 5000.0,
      "total_length_bwd_packets": 2500.0,
      "fwd_packet_length_mean": 500.0,
      "fwd_packet_length_std": 100.0,
      "bwd_packet_length_mean": 500.0,
      "bwd_packet_length_std": 100.0,
      "flow_bytes_per_sec": 7500.0,
      "flow_packets_per_sec": 15.0,
      "flow_iat_mean": 100.0,
      "flow_iat_std": 50.0,
      "flow_iat_max": 500.0,
      "fwd_iat_total": 1000.0,
      "fwd_iat_mean": 100.0,
      "fwd_iat_std": 50.0,
      "bwd_iat_total": 500.0,
      "bwd_iat_mean": 100.0,
      "bwd_iat_std": 50.0,
      "fwd_packets_per_sec": 10.0,
      "bwd_packets_per_sec": 5.0,
      "down_up_ratio": 0.5,
      "avg_packet_size": 500.0,
      "avg_fwd_segment_size": 500.0,
      "avg_bwd_segment_size": 500.0,
      "subflow_fwd_packets": 10,
      "subflow_bwd_packets": 5,
      "subflow_fwd_bytes": 5000.0,
      "subflow_bwd_bytes": 2500.0
    },
    "src_ip": "192.168.1.100",
    "dst_ip": "10.0.0.1"
  }'
```

### Get Metrics

```bash
curl http://localhost:8000/metrics
```

### Get Recent Alerts

```bash
curl http://localhost:8000/alerts?limit=10
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ Web UI   │  │Dashboard │  │ External │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└───────┼─────────────┼─────────────┼────────────────────────┘
        │             │             │
┌───────▼─────────────▼─────────────▼────────────────────────┐
│              FastAPI Application                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Middleware: Auth | Rate Limit | Logging | CORS       │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Routes: /predict | /health | /metrics | /alerts      │  │
│  └──────────────────────────────────────────────────────┘  │
└───────┬─────────────────────────────────────────────────────┘
        │
┌───────▼─────────────────────────────────────────────────────┐
│                   ML Pipeline                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ XGBoost  │→ │  SHAP    │→ │  Alert   │                  │
│  │Classifier│  │Explainer │  │  Queue   │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## 🔒 Security Features

### Authentication
- API key-based authentication
- Configurable per-client keys
- Header-based (X-API-Key)

### Rate Limiting
- Per-IP tracking
- 1000 requests/minute default
- Configurable limits

### Input Validation
- Pydantic schema validation
- IP address format checks
- Feature range validation
- NaN/Inf detection
- XSS/SQL injection prevention

### Monitoring
- Request logging with unique IDs
- Error tracking
- Performance metrics
- Audit trails

## 📈 Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Macro F1 Score | > 0.97 | ⏳ Pending real data training |
| Inference Latency (p95) | < 50ms | ✅ Optimized |
| False Positive Rate | < 2% | ⏳ Pending benchmarking |
| Throughput | 100K flows/sec | ✅ Batch processing ready |
| API Uptime | > 99.9% | ✅ Health checks enabled |

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api.py -v

# Run fast tests only
pytest tests/ -v -m "not slow"
```

## 📦 Project Structure

```
nids/
├── src/nids/
│   ├── api/              # FastAPI application
│   │   ├── main_v2.py    # Production API
│   │   └── middleware.py # Security middleware
│   ├── dashboard/        # Streamlit dashboard
│   ├── data/             # Data loading & features
│   ├── models/           # ML models
│   │   ├── classifier.py # XGBoost classifier
│   │   └── explainer.py  # SHAP explainer
│   ├── pipeline/         # Real-time pipeline
│   └── utils/            # Utilities
│       ├── exceptions.py # Custom exceptions
│       ├── logging.py    # Logging setup
│       ├── metrics.py    # Performance metrics
│       └── validators.py # Input validation
├── tests/                # Test suite
├── k8s/                  # Kubernetes manifests
├── monitoring/           # Prometheus config
├── config.py             # Configuration management
├── train_model.py        # Model training script
├── Dockerfile            # Production Docker image
├── docker-compose.yml    # Full stack deployment
└── requirements.txt      # Python dependencies
```

## 🚢 Deployment

### Docker Compose (Recommended for Testing)

```bash
docker-compose up -d
```

Includes:
- NIDS API
- Streamlit Dashboard
- PostgreSQL Database
- Prometheus Monitoring
- Grafana Dashboards

### Kubernetes (Production)

```bash
# Create namespace
kubectl create namespace nids

# Apply manifests
kubectl apply -f k8s/

# Check status
kubectl get pods -n nids

# View logs
kubectl logs -f deployment/nids-api -n nids
```

### Cloud Platforms

- **AWS**: ECS, EKS, or EC2
- **Azure**: AKS or Container Instances
- **GCP**: GKE or Cloud Run

## 🛠️ Configuration

Key environment variables in `.env`:

```bash
# Application
APP_ENV=production
DEBUG=false

# Security
SECRET_KEY=your-secret-key-here
REQUIRE_API_KEY=true
API_KEYS=key1,key2,key3

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Model
MODEL_PATH=models/nids_model.pkl
INFERENCE_TIMEOUT_MS=100

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Database
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nids
```

## 📊 Monitoring

### Prometheus Metrics

- `nids_requests_total` - Total API requests
- `nids_inference_time_ms` - Inference latency
- `nids_errors_total` - Error count
- `nids_attacks_detected` - Attacks by type

### Grafana Dashboards

Access at `http://localhost:3000` (default: admin/admin)

Pre-configured dashboards:
- System performance
- Attack distribution
- API metrics
- Error rates

### Logs

Structured JSON logging to:
- Console (stdout)
- File: `logs/nids.log` (rotated)

## 🎓 Dataset

This system is designed for the **CICIDS2017** dataset:
- 2.8 million labeled network flows
- 15 attack categories
- Download: [UNB CICIDS2017](https://www.unb.ca/cic/datasets/ids-2017.html)

Alternative datasets:
- NSL-KDD
- UNSW-NB15

## 💼 Commercial Use

### Target Market
- Government agencies (CERT-In compliance)
- Banks and financial institutions (RBI guidelines)
- Healthcare organizations (HIPAA/DPDPA)
- Educational institutions

### Pricing
- Small deployments: ₹10L/year
- Medium enterprises: ₹25L/year
- Large enterprises: ₹50L/year

Includes:
- On-premise deployment
- Custom model training
- 24/7 support
- Compliance documentation

## 🤝 Contributing

This is a proprietary project. For collaboration inquiries, contact the maintainers.

## 📄 License

Proprietary - All Rights Reserved

## 👥 Authors

- **Venkata Reddy** - [GitHub](https://github.com/Venkatareddy26)

## 📞 Support

For issues and questions:
- GitHub Issues: [Create Issue](https://github.com/Venkatareddy26/network-intrusion-detection-system-nids-/issues)
- Email: support@example.com

## 🙏 Acknowledgments

- CICIDS2017 dataset by Canadian Institute for Cybersecurity
- XGBoost team for the ML framework
- SHAP library for explainability
- FastAPI and Streamlit communities

## 📚 Documentation

- [Security Policy](SECURITY.md)
- [API Documentation](http://localhost:8000/docs) (when running)
- [Docker Hub](https://hub.docker.com/)

## 🔄 Roadmap

- [ ] LSTM layer for sequential attack detection
- [ ] Threat intelligence integration
- [ ] Multi-tenancy support
- [ ] Mobile dashboard
- [ ] Real-time Kafka streaming
- [ ] GPU acceleration
- [ ] Federated learning

---

**Built with ❤️ for cybersecurity**
