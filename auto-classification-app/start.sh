#!/usr/bin/env bash

# Auto-Classification App - One-Command Start Script
# Usage: ./start.sh

set -e

# --- Configuration ---
OM_DIR="../openmetadata-docker"
BACKEND_DIR="backend"
FRONTEND_DIR="frontend"
ENV_FILE=".env"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# --- Check Environment Mode ---
# Load .env if exists
if [ -f "$ENV_FILE" ]; then
    log "Loading configuration from $ENV_FILE..."
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

MODE="LOCAL"
if [ -n "$OPENMETADATA_HOST" ]; then
    MODE="CLOUD"
    OM_HOST="$OPENMETADATA_HOST"
    log "Detected Cloud/External configuration (Host: $OM_HOST)"
    log "Skipping Docker infrastructure setup."
else
    OM_HOST="http://localhost:8585"
    log "No external configuration detected. Using Local Docker Mode."
fi

# --- LOCAL MODE STEPS ---
# --- 2. Docker/Podman Detection (Global) ---
# Check for podman or docker
if command -v podman >/dev/null 2>&1; then
    log "Using Podman..."
    systemctl --user start podman.socket || true
    DOCKER_CMD="podman"
    # Podman compose often expects docker-compose compat
    if command -v podman-compose >/dev/null 2>&1; then
        COMPOSE_CMD="podman-compose"
    else
        # Fallback to docker compose command mapped to podman socket
        export DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"
        COMPOSE_CMD="docker compose"
    fi
else
    log "Using Docker..."
    COMPOSE_CMD="docker compose"
fi

# --- 3. Infrastructure Setup ---
if [ "$MODE" == "LOCAL" ]; then
    # --- Checks ---
    if [ ! -d "$OM_DIR" ]; then
        error "OpenMetadata directory not found at $OM_DIR. Please ensure the repository is fully checked out."
    fi

    # Key Generation
    log "Checking security keys..."
    KEYS_DIR="$OM_DIR/conf"
    mkdir -p "$KEYS_DIR"
    if [ ! -f "$KEYS_DIR/private.pem" ]; then
        warn "Keys not found. Generating new security keys..."
        openssl genrsa -out "$KEYS_DIR/private.pem" 2048
        openssl pkcs8 -topk8 -inform PEM -outform DER -in "$KEYS_DIR/private.pem" -out "$KEYS_DIR/private_key.der" -nocrypt
        openssl rsa -in "$KEYS_DIR/private.pem" -pubout -outform DER -out "$KEYS_DIR/public_key.der"
        success "Keys generated."
    else
        success "Keys already present."
    fi

    log "Starting FULL OpenMetadata Infrastructure..."
    log "Ensuring clean state..."
    $COMPOSE_CMD -f "$OM_DIR/docker-compose-postgres.yml" down --remove-orphans || true
    podman network rm openmetadata-docker_app_net 2>/dev/null || true

    $COMPOSE_CMD -f "$OM_DIR/docker-compose-postgres.yml" up -d

    # Wait for OM
    log "Waiting for OpenMetadata to be ready (this may take a few minutes)..."
    spin='-\|/'
    i=0
    while ! curl -s "$OM_HOST/api/v1/system/config/auth" > /dev/null; do
        i=$(( (i+1) %4 ))
        printf "\r${spin:$i:1} Waiting for $OM_HOST..."
        sleep 2
    done
    printf "\r"
    success "OpenMetadata is online!"

else
    # CLOUD MODE - Hybrid Setup
    log "Starting Hybrid Infrastructure (AI Layer Only)..."
    log "Ensuring MinIO and ChromaDB are running..."
    
    # Clean up stale web/db containers if any
    $COMPOSE_CMD -f "$OM_DIR/docker-compose-postgres.yml" down --remove-orphans || true
    # Ensure clean state for network
    podman network rm openmetadata-docker_app_net 2>/dev/null || true

    # Only bring up the AI services
    $COMPOSE_CMD -f "$OM_DIR/docker-compose-postgres.yml" up -d minio chromadb
    success "AI Layer Infrastructure (MinIO + ChromaDB) is online!"
fi

# --- 3.1 Start External Data Sources (Postgres/MySQL for Auto-Ingestion Testing) ---
if [ -f "docker-compose-sources.yaml" ]; then
    log "Starting Sample Data Sources (Postgres, MySQL)..."
    $COMPOSE_CMD -f "docker-compose-sources.yaml" up -d
    success "Sample Data Sources online."
fi

# --- 4. Backend Setup ---
log "Setting up Backend..."
cd "$BACKEND_DIR"

# Venv Setup
if [ ! -d "venv" ]; then
    log "Creating Python virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate

# Install Deps
log "Installing/Updating backend dependencies..."
# Robustly Check Torch
if ! python3 -c "import torch; print(torch.__version__)" >/dev/null 2>&1; then
    log "Torch is missing or broken. Installing PyTorch (CPU version)..."
    pip uninstall -y torch torchvision torchaudio 2>/dev/null || true
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

if ! pip freeze | grep -q openmetadata-ingestion; then
    pip install -r requirements.txt
else
    log "Dependencies already installed. Skipping pip install."
fi

# Check for spacy model
if ! python3 -c "import spacy; spacy.load('en_core_web_lg')" >/dev/null 2>&1; then
    python -m spacy download en_core_web_lg
else
    log "Spacy model 'en_core_web_lg' already present."
fi

# --- Inject Token ONLY if LOCAL ---
if [ "$MODE" == "LOCAL" ]; then
    log "Managing Ingestion Token..."
    TOKEN=$(python3 generate_token.py)
    if [ -z "$TOKEN" ]; then
        error "Failed to generate token."
    fi

    CLIENT_FILE="app/integration/om_client.py"
    if [ -f "$CLIENT_FILE" ]; then
        python3 -c "
import sys
import re
token = '$TOKEN'
path = '$CLIENT_FILE'

with open(path, 'r') as f:
    content = f.read()

# Update the default value in os.getenv
# Pattern: os.getenv(\"OPENMETADATA_TOKEN\", \"<OLD_TOKEN>\")
new_content = re.sub(
    r'os\.getenv\(\"OPENMETADATA_TOKEN\", \".*?\"\)', 
    f'os.getenv(\"OPENMETADATA_TOKEN\", \"{token}\")', 
    content
)

# Fallback for legacy format if regex didn't match (for safety)
if new_content == content:
     new_content = re.sub(r'jwtToken=\".*?\"', f'jwtToken=\"{token}\"', content)

with open(path, 'w') as f:
    f.write(new_content)
"
        success "Ingestion Token injected into $CLIENT_FILE (Default Fallback)"
    else
        warn "Could not find $CLIENT_FILE to inject token."
    fi
else
    log "Skipping Token Injection (Using Environment Variables)."
fi
cd ..

# --- 5. Frontend Setup ---
log "Setting up Frontend..."
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
    log "Installing frontend dependencies..."
    npm install --silent
fi
cd ..

# --- 6. Start Services ---
log "Starting Development Servers..."
log "Backend: http://localhost:8000"
log "Frontend: http://localhost:3000"
log "OpenMetadata: $OM_HOST"
log "Press Ctrl+C to stop everything."

# Clean exit handler
trap 'kill $(jobs -p); echo -e "\nServers stopped."; exit' SIGINT SIGTERM

# Start Backend (background)
cd "$BACKEND_DIR"
source venv/bin/activate
uvicorn app.main:app --reload --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Start Frontend (background)
cd "$FRONTEND_DIR"
npm run dev -- --host --port 3000 > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Stream logs (optional, or just wait)
# We wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID
