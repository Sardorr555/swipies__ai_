# Swipies AI

**Swipies AI** is an advanced AI platform that fuses Retrieval-Augmented Generation (RAG), autonomous Agent workflows, automated web crawling, and deep document intelligence.

Designed for modern enterprise AI applications, Swipies AI transforms unstructured documents, web pages, and complex data sources into production-ready AI assistants, automated intelligence pipelines, and actionable insights.

---

## 🌟 Key Features

- 🧠 **Retrieval-Augmented Generation (RAG)**: High-precision retrieval engine with deep document parsing (PDFs, spreadsheets, DOCX, presentation slides, OCR).
- 🤖 **Autonomous AI Agents**: Flexible agentic workflows supporting Model Context Protocol (MCP), tool execution, and multi-turn reasoning.
- 🌐 **Web Intelligence & Crawler**: Automated web scraping, deduplication, and structured content extraction for dynamic knowledge bases.
- 📊 **Analytics & ROI Dashboards**: Real-time tracking of AI performance, PR awards/intelligence, ROI metrics, and knowledge base coverage.
- 💬 **Multi-Channel Delivery**: Support for web search, embeddable chat widgets, and multi-channel messaging integrations.
- ⚡ **High-Performance Architecture**: Built with a fast Python backend core and a modern, responsive React/TypeScript frontend.

---

## 🏗️ Tech Stack

- **Backend**: Python 3.10+, FastAPI / Flask, `uv` dependency manager
- **Frontend**: TypeScript, React, UmiJS / Vite, TailwindCSS
- **Database & Search**: Vector Search Engine (Infinity / Elasticsearch), MySQL, Redis, MinIO

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.10+ (Python 3.13 recommended)
- Node.js 18+ and `npm`
- Docker & Docker Compose

### 1. Environment Setup (Backend)
```bash
# Install dependencies using uv
uv sync --python 3.13 --all-extras

# Download required model files & dependencies
uv run python3 ragflow_deps/download_deps.py
```

### 2. Frontend Development Server
```bash
cd web
npm install
npm run dev
```
The web application runs locally at `http://localhost:8000`.

### 3. Full Stack Docker Deployment
```bash
cd docker
docker compose up -d
```

---

## 📄 License

Copyright (c) 2026 **Swipies AI**. All rights reserved.
