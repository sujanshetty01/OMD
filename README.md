# AutoClassify AI Platform

This is the root workspace for the Auto-Classification application.

## 📂 Repository Structure

*   **/auto-classification-app**: The main application code (Frontend + Backend).
    *   **Frontend**: React + Vite application (Port 3000).
    *   **Backend**: FastAPI Python application (Port 8000).
    *   **Docker Config**: `docker-compose.yaml` for OpenMetadata and `docker-compose-sources.yaml` for Postgres/MinIO.
*   **/openmetadata-docker**: Configuration for the OpenMetadata Docker instance.

## 🚀 Quick Start
To get started immediately, navigate to the application directory and run the helper script:

```bash
cd auto-classification-app
./start.sh
```

For detailed instructions, architecture diagrams, and feature guides, please refer to the main documentation:
[**auto-classification-app/README.md**](./auto-classification-app/README.md)
