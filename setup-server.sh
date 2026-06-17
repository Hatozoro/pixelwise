# Pull the pinned model artefact
if [ -f .env ]; then
  set -a; source .env; set +a
  if [ -n "${MODEL_REPO:-}" ] && \
     [ -n "${MODEL_VERSION:-}" ]; then
    mkdir -p models/
    rm -rf /tmp/pixelwise-model
    git clone --depth 1 --branch "$MODEL_VERSION" \
      "$MODEL_REPO" /tmp/pixelwise-model
    cp /tmp/pixelwise-model/*.pkl models/
    cp /tmp/pixelwise-model/MODELCARD.md models/
    rm -rf /tmp/pixelwise-model
  fi
fi

# Install, start, and report the systemd unit on prod
if [ -f deploy/pixelwise.service ] && \
   command -v systemctl >/dev/null 2>&1 && \
   id habib >/dev/null 2>&1; then
  sudo cp deploy/pixelwise.service /etc/systemd/system/pixelwise.service
  sudo systemctl daemon-reload
  sudo systemctl enable pixelwise
  sudo systemctl restart pixelwise
  sudo systemctl status pixelwise --no-pager
fi
#!/bin/bash
# 1. Verzeichnis auflösen
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 2. SYSTEM-PAKETE:
sudo apt update && sudo apt install -y python3.14-venv postgresql postgresql-contrib

# 3. MODELL-ARTEFAKT:
if [ -f .env ]; then
  set -a; source .env; set +a
  if [ -n "${MODEL_REPO:-}" ] && \
     [ -n "${MODEL_VERSION:-}" ]; then
    mkdir -p models/
    rm -rf /tmp/pixelwise-model
    git clone --depth 1 --branch "$MODEL_VERSION" \
      "$MODEL_REPO" /tmp/pixelwise-model
    cp /tmp/pixelwise-model/*.pkl models/
    cp /tmp/pixelwise-model/MODELCARD.md models/
    rm -rf /tmp/pixelwise-model
  fi
fi

# 4. SYSTEMD-DIENST
if [ -f deploy/pixelwise.service ] && \
   command -v systemctl >/dev/null 2>&1 && \
   id hatozoro >/dev/null 2>&1; then
  sudo cp deploy/pixelwise.service /etc/systemd/system/pixelwise.service
  sudo systemctl daemon-reload
  sudo systemctl enable pixelwise
  sudo systemctl restart pixelwise
  sudo systemctl status pixelwise --no-pager
fi

# 5. PostgreSQL-Rolle und Datenbank anlegen
if command -v psql >/dev/null 2>&1 && \
   [ -f "$SCRIPT_DIR/.env" ]; then
  set -a; source "$SCRIPT_DIR/.env"; set +a
  sudo -u postgres psql -tAc \
    "SELECT 1 FROM pg_roles WHERE rolname='pixelwise'" \
    | grep -q 1 || \
    sudo -u postgres psql -c \
    "CREATE USER pixelwise WITH PASSWORD '$DB_PASSWORD';"
  sudo -u postgres psql -tAc \
    "SELECT 1 FROM pg_database WHERE datname='pixelwise'" \
    | grep -q 1 || \
    sudo -u postgres createdb -O pixelwise pixelwise
fi
