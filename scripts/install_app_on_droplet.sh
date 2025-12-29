#!/bin/bash
# Application installation script - Run this ON the Droplet as 'mentraflow' user
# After code is uploaded/cloned

set -e

APP_DIR="/home/mentraflow/mentraflow-backend"

echo "📦 Installing MentraFlow application..."

cd $APP_DIR

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "   Please create .env file with your configuration"
    echo "   You can copy from env.production.example"
    exit 1
fi

# Create virtual environment (if it doesn't exist)
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3.12 -m venv venv
else
    echo "✅ Virtual environment already exists"
fi

# Activate and install/update dependencies
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# Run database migrations
echo "🔄 Running database migrations..."
alembic upgrade head

echo "✅ Application installed successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Set up systemd service (as root or with sudo):"
echo "      sudo cp scripts/mentraflow-api.service /etc/systemd/system/"
echo "      sudo systemctl daemon-reload"
echo "      sudo systemctl enable mentraflow-api"
echo "      sudo systemctl start mentraflow-api"
echo ""
echo "   2. Verify deployment (from your local machine):"
echo "      curl http://127.0.0.1:8000/health"
echo ""
echo "   Note: Nginx is handled by your frontend setup."
echo "   The backend runs on port 8000 and your frontend nginx will proxy /api/* to it."

