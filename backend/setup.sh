#!/bin/bash
# TrustChain Backend Setup Script

echo "🚀 Setting up TrustChain Backend..."
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit .env and add your API keys!"
else
    echo ""
    echo "✓ .env file already exists"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "   - ANTHROPIC_API_KEY (get from https://console.anthropic.com)"
echo "   - OPENAI_API_KEY (get from https://platform.openai.com)"
echo ""
echo "2. Install Ollama for local Llama models:"
echo "   - macOS: brew install ollama"
echo "   - Linux: curl https://ollama.ai/install.sh | sh"
echo "   - Then run: ollama serve"
echo "   - Pull model: ollama pull llama2:13b"
echo ""
echo "3. Test the providers:"
echo "   python test_providers.py"
echo ""
echo "4. Start building the orchestrator service!"
