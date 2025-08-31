# LearnWords 📚

<div align="center">

[![CI](https://github.com/learnwords/learnwords/workflows/CI/badge.svg)](https://github.com/learnwords/learnwords/actions)
[![codecov](https://codecov.io/gh/learnwords/learnwords/branch/main/graph/badge.svg)](https://codecov.io/gh/learnwords/learnwords)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-supported-blue.svg)](https://www.docker.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

*AI-powered lesson plan generator for educators worldwide* 🎓

[**Documentation**](https://learnwords.readthedocs.io) | [**Demo**](https://demo.learnwords.dev) | [**API Docs**](https://api.learnwords.dev/docs) | [**Contributing**](CONTRIBUTING.md)

</div>

## ✨ Features

- 🤖 **Multiple AI Providers** - Support for Google Gemini, OpenAI GPT, and Anthropic Claude
- 📄 **Document Processing** - Upload and analyze educational materials (PDF, images, documents)
- 🎯 **Personalized Lesson Plans** - Generate customized lesson plans based on grade level, subject, and teaching style
- ☁️ **Cloud Storage** - Integrated with Cloudflare R2 and AWS S3 for scalable file storage
- ⚡ **Real-time Updates** - WebSocket support for live progress tracking
- 📤 **Export Options** - Multiple export formats for lesson plans
- 🔒 **Secure & Scalable** - Enterprise-ready with authentication, rate limiting, and monitoring
- 🌐 **API-First** - Comprehensive REST API with OpenAPI documentation
- 🐳 **Docker Ready** - One-command deployment with Docker Compose

## 🚀 Quick Start

### Prerequisites

- Python 3.11+ or Docker
- PostgreSQL 15+ and Redis 7+ (or use Docker Compose)

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/learnwords/learnwords.git
cd learnwords

# Copy environment configuration
cp env.example .env

# Edit configuration (add your AI API keys)
nano .env

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

### Option 2: Local Development

```bash
# Clone and setup
git clone https://github.com/learnwords/learnwords.git
cd learnwords

# Install dependencies
pip install -e ".[dev]"

# Setup environment
cp env.example .env
# Edit .env with your configuration

# Initialize database
learnwords init-db

# Start the server
learnwords serve
```

### Access the Application

- **Web Interface**: http://localhost:18773
- **API Documentation**: http://localhost:18773/api/docs
- **Health Check**: http://localhost:18773/health

## 📖 Documentation

### Quick Examples

#### Generate a Lesson Plan

```python
import httpx

# Upload a document
with open("math_textbook.pdf", "rb") as f:
    upload_response = httpx.post(
        "http://localhost:18773/api/v1/documents/upload",
        files={"file": f},
        data={"title": "Math Textbook Chapter 1"}
    )
document_id = upload_response.json()["id"]

# Create lesson plan
lesson_plan_data = {
    "document_id": document_id,
    "grade_level": "高中",
    "subject": "数学",
    "duration_minutes": 45,
    "learning_objectives": ["理解二次方程", "掌握求解方法"],
    "pedagogical_style": "启发式"
}

response = httpx.post(
    "http://localhost:18773/api/v1/lesson-plans/",
    json=lesson_plan_data
)
```

#### Using the CLI

```bash
# Check application health
learnwords health

# Create a new user
learnwords create-user --email teacher@school.edu --username teacher

# Start background worker
learnwords worker

# Show configuration
learnwords config
```

### API Reference

The complete API documentation is available at `/api/docs` when running the application, or online at [api.learnwords.dev/docs](https://api.learnwords.dev/docs).

Key endpoints:
- **Authentication**: `POST /api/v1/auth/{register,login}`
- **Documents**: `GET|POST /api/v1/documents/`
- **Lesson Plans**: `GET|POST /api/v1/lesson-plans/`
- **AI Management**: `GET /api/v1/ai/providers`

## 🏗️ Architecture

LearnWords follows a modern, scalable architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │   Mobile App    │    │  3rd Party API  │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼───────────────┐
                    │      Nginx Load Balancer    │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────▼───────────────┐
                    │     FastAPI Application     │
                    │   (Multiple Instances)      │
                    └─────────────┬───────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
┌─────────▼───────┐   ┌───────────▼──────────┐   ┌────────▼────────┐
│   PostgreSQL    │   │      Redis Cache     │   │  Celery Workers │
│   (Read/Write)  │   │    (Session/Tasks)   │   │ (Background)    │
└─────────────────┘   └──────────────────────┘   └─────────────────┘
          │                       │                       │
          │                       │                       │
┌─────────▼───────┐   ┌───────────▼──────────┐   ┌────────▼────────┐
│   File Storage  │   │    AI Providers      │   │   Monitoring    │
│ (R2/S3/Local)   │   │ (Gemini/GPT/Claude)  │   │ (Prometheus)    │
└─────────────────┘   └──────────────────────┘   └─────────────────┘
```

### Key Components

- **FastAPI Application**: Modern Python web framework with automatic OpenAPI docs
- **PostgreSQL**: Primary database with read replica support
- **Redis**: Caching and task queue backend
- **Celery**: Distributed task processing for AI operations
- **Multiple AI Providers**: Intelligent fallback and load balancing
- **Cloud Storage**: Scalable file storage with CDN support

## 🛠️ Development

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Node.js 18+ (for documentation)

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/learnwords/learnwords.git
cd learnwords

# Install with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Setup test database
createdb learnwords_test
learnwords init-db

# Run tests
pytest

# Start development server
learnwords serve --reload
```

### Code Quality

We maintain high code quality standards:

```bash
# Format code
black .
ruff --fix .

# Type checking
mypy app

# Security scanning
bandit -r app

# Run all checks
pre-commit run --all-files
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test types
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m e2e           # End-to-end tests only
```

## 🔧 Configuration

### Environment Variables

Key configuration options:

```bash
# Application
DEBUG=false
SECRET_KEY=your-secret-key
APP_PORT=18773

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/learnwords
REDIS_URL=redis://localhost:6379

# AI Providers
AI_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-claude-key

# Storage
STORAGE_BACKEND=r2
R2_ACCESS_KEY_ID=your-r2-key
R2_SECRET_ACCESS_KEY=your-r2-secret
R2_BUCKET_NAME=your-bucket

# Performance
WORKER_CONCURRENCY=2
CACHE_TTL=3600
```

See [`env.example`](env.example) for complete configuration options.

### Docker Deployment

Production deployment with monitoring:

```bash
# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.optimized.yml up -d

# With monitoring stack
docker-compose --profile monitoring --profile logging up -d

# Scale workers
docker-compose up -d --scale worker=4
```

## 📊 Monitoring

LearnWords includes comprehensive monitoring:

- **Metrics**: Prometheus + Grafana dashboards
- **Logging**: Structured logs with ELK stack
- **Health Checks**: Application and dependency health endpoints
- **Alerting**: Configurable alerts for performance and errors

Access monitoring:
- **Grafana**: http://localhost:19091 (admin/admin)
- **Prometheus**: http://localhost:19090
- **Kibana**: http://localhost:19292

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Contribution Steps

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for your changes
5. Ensure all tests pass (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Guidelines

- Write tests for new features
- Follow the code style (Black + Ruff)
- Update documentation as needed
- Add type hints to new code
- Keep security in mind

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **AI Providers**: Google Gemini, OpenAI, Anthropic for powering our AI features
- **Open Source**: Built on amazing open-source projects like FastAPI, SQLAlchemy, and many others
- **Community**: Thanks to all contributors and users

## 📞 Support

- **Documentation**: [learnwords.readthedocs.io](https://learnwords.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/learnwords/learnwords/issues)
- **Discussions**: [GitHub Discussions](https://github.com/learnwords/learnwords/discussions)
- **Email**: support@learnwords.dev

## 🗺️ Roadmap

- [ ] **Q1 2024**: Multi-language support
- [ ] **Q2 2024**: Advanced analytics dashboard
- [ ] **Q3 2024**: Mobile app
- [ ] **Q4 2024**: Collaborative features

---

<div align="center">

**[⭐ Star us on GitHub](https://github.com/learnwords/learnwords)** • **[🐦 Follow on Twitter](https://twitter.com/learnwords)** • **[💬 Join Discord](https://discord.gg/learnwords)**

Made with ❤️ by the LearnWords team

</div>