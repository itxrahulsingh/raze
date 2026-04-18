#!/bin/bash
# Ollama initialization script - pulls models on startup
# This ensures models are always available

set -e

OLLAMA_HOST="http://localhost:11434"
MAX_RETRIES=30
RETRY_INTERVAL=2

echo "🤖 Ollama Model Initialization"
echo "=============================="

# Wait for Ollama to be ready
echo "Waiting for Ollama to be ready..."
for i in $(seq 1 $MAX_RETRIES); do
    if curl -s "$OLLAMA_HOST/api/tags" > /dev/null 2>&1; then
        echo "✅ Ollama is ready"
        break
    fi
    if [ $i -eq $MAX_RETRIES ]; then
        echo "❌ Ollama failed to start after $((MAX_RETRIES * RETRY_INTERVAL)) seconds"
        exit 1
    fi
    echo "  Attempt $i/$MAX_RETRIES... waiting..."
    sleep $RETRY_INTERVAL
done

# Check if models are already loaded
echo ""
echo "Checking for existing models..."
MODELS=$(curl -s "$OLLAMA_HOST/api/tags" | grep -o '"name":"[^"]*"' | wc -l)

if [ $MODELS -gt 0 ]; then
    echo "✅ Found $MODELS model(s) already loaded"
    curl -s "$OLLAMA_HOST/api/tags" | grep -o '"name":"[^"]*"' | sed 's/"name":"//; s/"//' | sed 's/^/   ✓ /'
else
    echo "📥 No models found - pulling default models..."

    # Pull mistral (excellent balance of speed and quality)
    echo ""
    echo "📦 Pulling mistral (this may take 5-10 minutes)..."
    ollama pull mistral
    if [ $? -eq 0 ]; then
        echo "✅ Mistral downloaded successfully"
    else
        echo "⚠️  Failed to pull mistral - continuing anyway"
    fi

    # Verify models are loaded
    echo ""
    echo "Verifying models..."
    MODELS=$(curl -s "$OLLAMA_HOST/api/tags" | grep -o '"name":"[^"]*"' | wc -l)
    echo "✅ Found $MODELS model(s) loaded:"
    curl -s "$OLLAMA_HOST/api/tags" | grep -o '"name":"[^"]*"' | sed 's/"name":"//; s/"//' | sed 's/^/   ✓ /'
fi

echo ""
echo "=============================="
echo "🎉 Ollama initialization complete!"
echo "=============================="
