#!/usr/bin/env bash
# Setup for the Petri Bloom hiring-bias project, tuned for a 16GB Apple
# Silicon Mac running everything locally through Ollama (no API charges).
set -euo pipefail

echo "== 1. Ollama =="
if ! command -v ollama >/dev/null 2>&1; then
  echo "Installing Ollama via Homebrew..."
  brew install ollama
else
  echo "Ollama already installed."
fi

# Make sure the Ollama server is running before we pull/use models.
if ! pgrep -x "ollama" >/dev/null 2>&1; then
  echo "Starting Ollama server in the background..."
  ollama serve >/tmp/ollama.log 2>&1 &
  sleep 3
fi

echo "== 2. Pull models sized for 16GB unified memory =="
# ~5GB resident each at Q4 quantization - safe to run one at a time.
ollama pull llama3.1:8b        # auditor / target
ollama pull qwen2.5:7b         # alternate target, for comparing models
# ~9GB resident at Q4 - fine alone, do not run concurrently with another model.
ollama pull qwen2.5:14b        # judge (stronger scoring than the 7-8B models)

echo "== 3. Python environment =="
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install petri-bloom

echo "== 4. Memory-safe environment variables =="
cat <<'EOF' >> .venv/bin/activate

# --- Petri Bloom / Ollama client settings (16GB Mac) ---
export OLLAMA_BASE_URL=http://localhost:11434/v1
EOF

# NOTE: OLLAMA_MAX_LOADED_MODELS / OLLAMA_NUM_PARALLEL / OLLAMA_CONTEXT_LENGTH
# do nothing if just exported in this shell: the Ollama server that answers
# requests is the menu-bar Ollama.app (started at login), a separate process
# that does NOT inherit env vars from a terminal you source this script in.
# They must be set at the launchd level so the GUI app's server picks them up,
# and the app must be restarted for the change to take effect.
echo "== 5. Apply memory-safe settings to the running Ollama server =="
launchctl setenv OLLAMA_MAX_LOADED_MODELS 1   # never keep two models resident at once
launchctl setenv OLLAMA_NUM_PARALLEL 1        # serialize requests instead of batching
launchctl setenv OLLAMA_CONTEXT_LENGTH 8192   # enough for a ~15-turn auditor conversation
# The desktop app also stores its own context_length in
# ~/Library/Application Support/Ollama/db.sqlite (settings table), which
# overrides the launchd env var for that one setting - keep both in sync.
if command -v sqlite3 >/dev/null 2>&1 && [ -f "$HOME/Library/Application Support/Ollama/db.sqlite" ]; then
  osascript -e 'tell application "Ollama" to quit' >/dev/null 2>&1 || killall Ollama >/dev/null 2>&1 || true
  sleep 1
  sqlite3 "$HOME/Library/Application Support/Ollama/db.sqlite" \
    "UPDATE settings SET context_length = 8192 WHERE id = 1;" || true
fi
killall Ollama >/dev/null 2>&1 || true
sleep 1
open -a Ollama
echo "Restarted Ollama.app with memory-safe launchd env vars applied."
echo "NOTE: launchctl setenv does not persist across reboot/logout - rerun"
echo "this script (or the launchctl/open lines above) after restarting your Mac."

echo ""
echo "Setup complete. Next steps:"
echo "  source .venv/bin/activate"
echo "  bloom scenarios ./hiring_bias --model-role scenarios=ollama/llama3.1:8b"
echo "  inspect eval petri_bloom/bloom_audit -T behavior=./hiring_bias \\"
echo "    --model-role auditor=ollama/llama3.1:8b \\"
echo "    --model-role target=ollama/qwen2.5:7b \\"
echo "    --model-role judge=ollama/qwen2.5:14b \\"
echo "    --max-connections 1"
echo "  inspect view"
