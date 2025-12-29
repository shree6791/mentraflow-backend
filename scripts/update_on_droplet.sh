#!/bin/bash
# Quick update script - Run this ON the Droplet after code is deployed
# This updates dependencies, runs migrations, and restarts the service

set -e

APP_DIR="/home/mentraflow/mentraflow-backend"

echo "🔄 Updating MentraFlow application..."

cd $APP_DIR

# Activate virtual environment
source venv/bin/activate

# Update dependencies (if requirements.txt changed)
echo "📦 Updating Python dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# Run migrations (if any new ones)
echo "🔄 Running database migrations..."
alembic upgrade head

# Restart service
echo "🔄 Restarting service..."
sudo systemctl restart mentraflow-api

# Wait a moment for service to start
sleep 2

# Check status
echo "📊 Service status:"
sudo systemctl status mentraflow-api --no-pager -l

echo ""
echo "✅ Update complete!"
echo ""
echo "🌐 Test from your local machine:"
echo "   curl http://YOUR_DROPLET_IP:8000/health"
echo "   (Or via frontend nginx: curl http://YOUR_DROPLET_IP/api/v1/health)"

