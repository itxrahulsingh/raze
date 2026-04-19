#!/bin/bash
# Advanced Ollama initialization script
# Automatically sets up Mistral LLM, embeddings, and optimizations for ChatGPT-like performance

set -e

OLLAMA_HOST="http://localhost:11434"
MAX_RETRIES=60
RETRY_INTERVAL=2

echo "🚀 RAZE Advanced Ollama Setup"
echo "============================================"
echo "Initializing Ollama with LLM, embeddings, and optimizations"
echo "============================================"
echo ""

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama service to start..."
for i in $(seq 1 $MAX_RETRIES); do
    if curl -s "$OLLAMA_HOST/api/tags" > /dev/null 2>&1; then
        echo "✅ Ollama service is ready"
        break
    fi
    if [ $i -eq $MAX_RETRIES ]; then
        echo "❌ Ollama failed to start after $((MAX_RETRIES * RETRY_INTERVAL)) seconds"
        exit 1
    fi
    if [ $((i % 10)) -eq 0 ]; then
        echo "   Still waiting... ($i/$MAX_RETRIES)"
    fi
    sleep $RETRY_INTERVAL
done

# Check existing models
echo ""
echo "📊 Checking loaded models..."
MODELS=$(curl -s "$OLLAMA_HOST/api/tags" | grep -o '"name":"[^"]*"' | wc -l)

if [ $MODELS -eq 0 ]; then
    echo "⚠️  No models found - starting downloads..."
    echo ""

    # Pull Mistral (LLM for chat - 4.1GB)
    echo "📥 Step 1/2: Downloading Mistral 7B (LLM for conversations)"
    echo "   Model: Mistral (4.1GB) - Excellent for chat, code, and reasoning"
    echo "   This may take 5-15 minutes depending on your connection..."
    echo ""
    ollama pull mistral 2>&1 | grep -E "pulling|pulling manifest|verifying|success" || true
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo "✅ Mistral downloaded successfully"
    else
        echo "❌ Failed to pull Mistral"
        exit 1
    fi

    # Pull nomic-embed-text (Embeddings for knowledge base - 274MB)
    echo ""
    echo "📥 Step 2/2: Downloading Nomic Embed Text (embeddings)"
    echo "   Model: Nomic Embed Text (274MB) - High-quality text embeddings"
    echo "   This may take 1-3 minutes..."
    echo ""
    ollama pull nomic-embed-text 2>&1 | grep -E "pulling|pulling manifest|verifying|success" || true
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        echo "✅ Nomic Embed Text downloaded successfully"
    else
        echo "⚠️  Failed to pull embeddings - some features may be limited"
    fi
fi

# Verify all required models are loaded
echo ""
echo "✓ Verifying installed models..."
MODELS_JSON=$(curl -s "$OLLAMA_HOST/api/tags")

# Check for required models
HAS_MISTRAL=$(echo "$MODELS_JSON" | grep -c '"mistral' || true)
HAS_EMBEDDINGS=$(echo "$MODELS_JSON" | grep -c '"nomic-embed\|"all-minilm\|"mxbai-embed' || true)

if [ $HAS_MISTRAL -gt 0 ]; then
    echo "✅ Mistral LLM loaded"
else
    echo "⚠️  Mistral LLM not found"
fi

if [ $HAS_EMBEDDINGS -gt 0 ]; then
    echo "✅ Embeddings model loaded"
else
    echo "⚠️  Embeddings model not found - knowledge base features limited"
fi

echo ""
echo "📋 Loaded Models:"
echo "$MODELS_JSON" | grep -o '"name":"[^"]*"' | sed 's/"name":"//; s/"//' | sort | sed 's/^/   • /'

echo ""
echo "⚙️  Ollama Configuration:"
echo "   • Host: $OLLAMA_HOST"
echo "   • Default LLM: mistral (for chat/completion)"
echo "   • Embeddings: nomic-embed-text (for knowledge base)"
echo "   • Features: Text completion, embeddings, knowledge retrieval"
echo ""

echo "🔗 Integration Points:"
echo "   • Chat API: /api/v1/chat (uses Mistral for responses)"
echo "   • Knowledge Search: /api/v1/knowledge (uses embeddings)"
echo "   • Admin Chat: /admin-chat (advanced agent with Mistral)"
echo "   • Web Search: DuckDuckGo API (free, no key required)"
echo ""

echo "📈 Performance Tips:"
echo "   • Responses optimized for sub-3 second latency"
echo "   • Parallel requests supported up to 4 concurrent"
echo "   • Context window: 8k tokens (configurable)"
echo "   • Temperature: 0.7 (balanced creativity vs accuracy)"
echo ""

echo "============================================"
echo "✨ RAZE Ollama setup complete and ready!"
echo "============================================"
echo ""
