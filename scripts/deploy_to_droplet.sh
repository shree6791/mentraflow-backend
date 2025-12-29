#!/bin/bash
# Deployment script for DigitalOcean Droplet
# Run this from your local machine to deploy to the Droplet

set -e

# Configuration
DROPLET_IP="147.182.239.22"
DROPLET_USER="root"  # Change to your user if you've created one
APP_DIR="/home/mentraflow/mentraflow-backend"
REMOTE_USER="mentraflow"  # Application user

echo "🚀 Deploying MentraFlow to Droplet..."

# Check if .env exists locally
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found in current directory"
    echo "   Please create .env file with your configuration"
    exit 1
fi

echo "📦 Step 1: Uploading code to Droplet..."
# Upload code (excluding .env, venv, etc.)
rsync -avz --exclude '.env' \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.git' \
    --exclude 'qdrant_storage' \
    ./ ${DROPLET_USER}@${DROPLET_IP}:${APP_DIR}/

echo "📝 Step 2: Uploading .env file..."
# Upload .env separately (more secure)
scp .env ${DROPLET_USER}@${DROPLET_IP}:${APP_DIR}/.env

echo "✅ Code uploaded successfully!"
echo ""
echo "📋 Next steps (SSH into your Droplet):"
echo "   1. ssh ${DROPLET_USER}@${DROPLET_IP}"
echo "   2. cd ${APP_DIR}"
echo "   3. source venv/bin/activate"
echo "   4. pip install -r requirements.txt"
echo "   5. alembic upgrade head"
echo "   6. sudo systemctl restart mentraflow-api"
echo ""
echo "Or run the setup script on the Droplet:"
echo "   ssh ${DROPLET_USER}@${DROPLET_IP} 'bash -s' < scripts/setup_droplet.sh"

