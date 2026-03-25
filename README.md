# 🚀 Crypto Pulse

[![CI/CD Pipeline](https://github.com/AadarshDubey/crx/actions/workflows/ci.yml/badge.svg)](https://github.com/AadarshDubey/crx/actions/workflows/ci.yml)
[![Docker Support](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](#-run-with-docker-recommended)

**AI-powered crypto news and sentiment aggregator** — Never miss market-moving information again.

Crypto Pulse scrapes Twitter/X accounts and news sources you care about, analyzes sentiment using AI, and lets you query the data through natural language.

## 🎯 Features

- **Twitter Scraping**: Track specific crypto influencers, analysts, and project accounts
- **News Aggregation**: Fetch from CoinDesk, CoinTelegraph, The Block, and more
- **AI Sentiment Analysis**: Understand market sentiment at a glance
- **Semantic Search**: Find relevant content using natural language queries
- **RAG-powered Chat**: Ask questions about market conditions and get AI answers with sources
- **Real-time Dashboard**: Beautiful UI to monitor everything
- **🐳 Dockerized Integration**: Fully containerized environment using Docker & Docker Compose
- **🔄 CI/CD Pipeline**: Automated testing and CI/CD workflows building Docker images via GitHub Actions

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Next.js)                            │
│  Dashboard  │  Feed View  │  Search/Query  │  AI Chat Interface        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI/Python)                        │
│  API Routes  │  Scrapers Service  │  GenAI Service  │  Scheduler        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │ PostgreSQL  │ │   Redis     │ │  ChromaDB/  │
            │ (Main DB)   │ │  (Cache)    │ │  Pinecone   │
            └─────────────┘ └─────────────┘ └─────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** (Recommended)
- **Python 3.11+** and **Node.js 20+** (For local development)
- **An LLM API key** (OpenAI or Groq)

---

### 🐳 Run with Docker (Recommended)

The easiest way to get the entire stack (Postgres, Redis, Backend, Frontend) running is via Docker.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/AadarshDubey/crx.git
   cd crx
   ```

2. **Set up Environment Variables:**
   Create a `.env.docker` file in the root directory:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   # GROQ_API_KEY=your_groq_api_key (optional)
   ```

3. **Start the services:**
   ```bash
   docker-compose up -d --build
   ```

4. **Access the application:**
   - **Frontend UI:** http://localhost:3000
   - **Backend API:** http://localhost:8000
   - **API Docs:** http://localhost:8000/docs

---

### 💻 Local Development (Backend + Frontend)

This repo is structured as a single project with:

- `backend/` (FastAPI)
- `frontend/` (Next.js)

```bash
# Backend
cd backend

# Create & activate virtual environment
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS/Linux
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create a backend/.env file (do NOT commit it)
# At minimum set an LLM key and make sure Postgres + Redis are running.
# Example keys:
#   OPENAI_API_KEY=...
#   GROQ_API_KEY=...
#   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/crypto_pulse
#   REDIS_URL=redis://localhost:6379/0

# Run the server
uvicorn app.main:app --reload

# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

```bash
# Frontend
cd ../frontend

npm install

# Copy env example (Windows PowerShell)
# Copy-Item .env.example .env.local

npm run dev

# UI: http://localhost:3000
```

## 📁 Project Structure

```
crypto-pulse/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Configuration settings
│   │   ├── api/routes/          # API endpoints
│   │   │   ├── tweets.py        # Tweet endpoints
│   │   │   ├── news.py          # News endpoints
│   │   │   ├── search.py        # Search endpoints
│   │   │   └── chat.py          # AI chat endpoints
│   │   ├── services/
│   │   │   ├── scrapers/        # Twitter & News scrapers
│   │   │   ├── ai/              # Sentiment, Summarizer, RAG
│   │   │   └── scheduler.py     # Background job scheduler
│   │   ├── models/              # SQLAlchemy models
│   │   ├── database/            # DB connection & vector store
│   │   └── utils/               # Helper functions
│   ├── requirements.txt
├── frontend/
```

## 🔌 API Endpoints

### Tweets
- `GET /api/tweets/` - Get scraped tweets with filters
- `GET /api/tweets/accounts` - List tracked accounts
- `POST /api/tweets/accounts` - Add account to track
- `POST /api/tweets/scrape` - Trigger manual scrape

### News
- `GET /api/news/` - Get news articles
- `GET /api/news/sources` - List news sources
- `GET /api/news/trending/topics` - Get trending topics

### Search
- `GET /api/search/` - Keyword/semantic search
- `POST /api/search/semantic` - AI-powered semantic search

### Chat
- `POST /api/chat/` - Chat with AI about crypto
- `POST /api/chat/stream` - Streaming chat response
- `POST /api/chat/analyze` - Deep analysis of a topic

## 🤖 AI Features

### Sentiment Analysis
Uses GPT-4o-mini with crypto-specific prompting to determine if content is:
- **Bullish** (positive for market)
- **Bearish** (negative for market)  
- **Neutral**

### RAG (Retrieval-Augmented Generation)
1. Your question gets converted to an embedding
2. Similar content is retrieved from the vector database
3. GPT answers based on real scraped data

Example queries:
- "What's the sentiment on Bitcoin today?"
- "Summarize Vitalik's recent tweets"
- "Any regulatory news I should worry about?"

## 🔧 Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `DATABASE_URL` | PostgreSQL connection | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `USE_CHROMA` | Use ChromaDB (local) vs Pinecone | `true` |
| `SCRAPE_INTERVAL_MINUTES` | Auto-scrape frequency | `15` |

## 📊 Adding Twitter Accounts

```python
# Via API
POST /api/tweets/accounts
{
    "handle": "VitalikButerin",
    "category": "founder"
}
```

Categories: `influencer`, `analyst`, `project`, `news`, `whale`, `developer`, `exchange`, `vc`, `general`

## 🤖 CI/CD & Deployment

This project utilizes **GitHub Actions** for robust continuous integration and delivery:
- **Automated Testing:** Runs `pytest` on the backend and `vitest` on the frontend on every push or PR.
- **Docker Image Builds:** Automatically builds production-ready backend and frontend images and pushes them to the **GitHub Container Registry (GHCR)**.

## 🛣️ Roadmap

- [x] Backend API structure
- [x] Twitter scraper (Nitter fallback)
- [x] News scraper (RSS)
- [x] Sentiment analysis
- [x] Vector store integration
- [x] RAG chat
- [x] Frontend UI (Next.js)
- [x] Dockerization & CI/CD Pipeline
- [ ] Real-time WebSocket updates
- [ ] Price alerts integration
- [ ] Telegram/Discord notifications

## 📝 License

MIT

---

Built with ❤️ for the crypto community
