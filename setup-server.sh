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
   id hatozoro >/dev/null 2>&1; then
  sudo cp deploy/pixelwise.service /etc/systemd/system/pixelwise.service
  sudo systemctl daemon-reload
  sudo systemctl enable pixelwise
  sudo systemctl restart pixelwise
  sudo systemctl status pixelwise --no-pager
fi
