# OpenMetadata‑First Architecture – Documentation

## Overview
This repository implements a **metadata‑first data platform** that tightly couples three storage layers:
1. **OpenMetadata (Governance Layer)** – the single source of truth for schema, lineage, and PII tags.
2. **MinIO (Raw Data Lake)** – an S3‑compatible object store for the original CSV/Parquet files.
3. **ChromaDB (AI Vector Store)** – a semantic search engine that powers the PromptIQ AI queries.

The design ensures that data is **governed before it is stored or indexed**, providing security, compliance, and fast AI‑driven retrieval.

---

## 1️⃣ Ingestion Strategy – Bulk Metadata Sync
- **File upload** → FastAPI endpoint `/datasets/upload`.
- **Profiling & Classification** – pandas profiling + custom AI classifier tags each column.
- **Single‑Shot OpenMetadata Call** – `OMClient.ingest_dataset_with_all_metadata` builds a complete `CreateTableRequest` containing:
  - Table name (derived from the filename).
  - All columns with data types (`STRING`, `INT`, `FLOAT`, `BOOLEAN`).
  - PII tags (`PII.Sensitive`, `PII.PersonalData`, etc.) attached to each column.
- **Why it matters** – One API call creates the table *and* all tags atomically, avoiding the 50‑call “column‑by‑column” pattern that caused performance bottlenecks.

---

## 2️⃣ Three‑Layer AI Architecture
| Layer | Technology | Role |
|-------|------------|------|
| **Governance** | **OpenMetadata** (PostgreSQL + Elasticsearch) | Stores schema, lineage, and classification metadata. |
| **Storage** | **MinIO** (S3‑compatible) | Holds the raw uploaded files in the `raw-data` bucket (public for easy downstream access). |
| **AI** | **ChromaDB** (vector DB) | Indexes textual representations of each row for semantic search used by PromptIQ. |

When a user asks a question, PromptIQ:
1. Performs a **semantic search** in ChromaDB.
2. Retrieves the **source dataset** name from the vector metadata.
3. Pulls **OpenMetadata tags** for that dataset to enrich the answer (e.g., indicating PII). 
4. Returns a concise, context‑aware response.

---

## 3️⃣ Asynchronous Processing & Real‑Time Feedback
- **FastAPI BackgroundTasks** handle heavy I/O after the initial request returns.
- **Steps executed asynchronously**:
  1. Upload file to MinIO.
  2. Build the ChromaDB vector index.
- **WebSocket (`IngestionProgress.jsx`)** streams live status updates (`Archiving raw data…`, `Building semantic index…`, `Success!`) so the UI never appears stuck.

---

## 4️⃣ Container Network Security
- **Static RSA keys** (`public_key.der`, `private_key.der`) are generated once and mounted into the OpenMetadata container (`/opt/openmetadata/conf`). This prevents JWT token invalidation on container restarts.
- **Internal JWKS endpoint** – the OpenMetadata service now references `http://openmetadata-server:8585/api/v1/system/config/jwks` instead of `localhost`. This allows the server to verify its own tokens when running inside Docker/Podman networks.
- **CORS** – FastAPI now explicitly allows `http://localhost:3000` (the React frontend) to avoid browser‑side errors.

---

## 5️⃣ Running the Stack
```bash
# 1️⃣ Start OpenMetadata infrastructure (Postgres, Elasticsearch, MinIO, ChromaDB)
cd /home/ubuntu/OMD/openmetadata-docker
podman compose up -d   # or docker compose up -d

# 2️⃣ Generate and mount RSA keys (run once)
mkdir -p conf && openssl genpkey -algorithm RSA -out conf/private_key.der -pkeyopt rsa_keygen_bits:2048
openssl rsa -pubout -in conf/private_key.der -out conf/public_key.der

# 3️⃣ Start the backend & frontend
cd /home/ubuntu/OMD/auto-classification-app
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
uvicorn backend/app.main:app --reload   # backend on http://localhost:8000
npm run dev -- --host --port 3000      # frontend on http://localhost:3000
```
The UI will show the upload form, and after a file is uploaded you will see real‑time progress via the WebSocket.

---

## 6️⃣ Key Files to Review
- `backend/app/integration/om_client.py` – OpenMetadata SDK wrapper and bulk ingestion logic.
- `backend/app/api/endpoints.py` – FastAPI routes, background ingestion, and WebSocket updates.
- `frontend/src/components/IngestionProgress.jsx` – WebSocket handling and UI feedback.
- `openmetadata-docker/docker-compose-postgres.yml` – Service definitions, key volume mounts, and environment variables.

---

## 7️⃣ Extending the Platform
1. **Add new classifiers** – plug into `backend/app/core/classifier.py`.
2. **Custom vector embeddings** – replace the default embedding model in `backend/app/integration/vector_client.py`.
3. **Fine‑grained policies** – define additional OpenMetadata tag schemas and enforce them in `om_client.apply_column_tags`.

---

*This documentation lives in its own file (`OPENMETADATA_README.md`) so the main project README can stay focused on quick‑start instructions.*
