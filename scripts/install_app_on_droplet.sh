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

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3.12 -m venv venv

# Activate and install dependencies
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations
echo "🔄 Running database migrations..."
source venv/bin/activate
alembic upgrade head

echo "✅ Application installed successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Test the application:"
echo "      source venv/bin/activate"
echo "      gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"
echo ""
echo "   2. Set up systemd service (as root):"
echo "      sudo cp scripts/mentraflow-api.service /etc/systemd/system/"
echo "      sudo systemctl daemon-reload"
echo "      sudo systemctl enable mentraflow-api"
echo "      sudo systemctl start mentraflow-api"
echo ""
echo "   3. Configure Nginx (as root) - ONE-TIME SETUP:"
echo "      sudo cp scripts/nginx.conf /etc/nginx/sites-available/mentraflow-api"
echo "      sudo ln -s /etc/nginx/sites-available/mentraflow-api /etc/nginx/sites-enabled/"
echo "      sudo rm /etc/nginx/sites-enabled/default  # Remove default site"
echo "      sudo nginx -t  # Test configuration"
echo "      sudo systemctl restart nginx"
echo "      # Your API will be accessible at http://147.182.239.22 (no port needed!)"

