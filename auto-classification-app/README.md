# AutoClassify AI Platform

A modern data governance and discovery platform that automatically classifies datasets using NLP and flows data through a multi-layer AI architecture: **Governance (OpenMetadata)**, **Semantic Search (VectorDB)**, and **Object Storage (MinIO)**.

## 🏗 Architecture
This platform implements the following flow for every uploaded dataset:
1.  **Metadata Layer**: Table schemas and PII tags are pushed to **OpenMetadata** (PostgreSQL-backed).
2.  **AI Layer (Semantic Search)**: Data is indexed in **ChromaDB** using sentence embeddings.
3.  **Raw Object Store**: Original files are archived in **MinIO** for future AI training/retrieval.
4.  **Promptiq AI Engine**: A RAG-based assistant that queries all three layers to answer natural language questions about your data.

---

## 🚀 Quick Start (Setup)

**New Users: Follow these steps exactly to get running in < 5 minutes.**

### 1. Prerequisites
Ensure you have the following installed on your machine:
*   **Docker** (or Podman)
*   **Python 3.12+**
*   **Node.js 18+**

### 2. Environment Setup
The project relies on a `.env` file for configuration. One has been provided, but ensure it exists at `auto-classification-app/.env`.

**Important**: If you want to use the **AWS S3 Integration**, update the following variables in `.env`:
```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
```
*(If you skip this, the S3 Ingestion features will simply fail gracefully).*

### 3. One‑click Start

#### 🍎 macOS / 🐧 Linux
Run the shell script to initialize the environment:
```bash
cd auto-classification-app
./start.sh
```

#### 🪟 Windows
Run the batch file (using Command Prompt or PowerShell):
```cmd
cd auto-classification-app
start.bat
```

Both scripts automatically:
- Generate security keys.
- Start the OpenMetadata stack (Docker) and External Sources.
- Wait for services to be online.
- Configure authentication.
- Launch the Backend (Python) and Frontend (React).

Once running, access the platform at:
- **Frontend UI**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **OpenMetadata UI**: [http://localhost:8585](http://localhost:8585) (admin/admin)
- **MinIO Console**: [http://localhost:9001](http://localhost:9001) (minioadmin/minioadmin)

Stop the servers by pressing `Ctrl+C`.

---

## 🛠 Features & How-To

### ☁️ Ingest from S3 (NEW)
1.  Click the **Cloud Icon ("Ingest from S3")** on the dashboard.
2.  Select your desired Bucket (e.g., `omd-1`).
3.  **Preview Files**: Click on the bucket to see file names and sizes.
4.  **Process All**: Click **"Process All Files"** to securely download, classify, and vector-embed every file in that bucket.
5.  All imported files will appear in the **Dataset List** as governed assets.

### 📂 Upload Local Files
*   Click **"Upload New Dataset"** to drag-and-drop CSV, Excel, PDF, Parquet, or YAML files.
*   The system profiles the data, detects PII (SSN, Emails, Credit Cards), and archives it.

### 🤖 AI Assistant (Promptiq)
*   Go to the **AI Assistant** tab.
*   Ask questions like:
    *   *"Which datasets contain sensitive SSN data?"*
    *   *"Show me all files related to 'webapp' configuration."*
    *   *"What is the schema of the Sales dataset?"*
*   The engine combines **Vector Search** results with **OpenMetadata Tags** to provide a verified response.

---

## 🔧 Troubleshooting

*   **Frontend Error (500)**: If you see an error on the dataset list, try restarting the backend.
*   **S3 Connection Failed**: Verify your AWS Credentials in `.env`.
*   **Docker Issues**: Ensure `docker-compose` is available or alias `docker compose` if using V2.

## 🧹 Maintenance
The project includes a root-level `.gitignore` to keep your workspace clean. Temporary ingestion files (in `backend/uploads`) are automatically ignored.
