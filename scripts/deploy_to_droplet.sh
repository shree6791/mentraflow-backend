#!/bin/bash
# Deployment script for DigitalOcean Droplet
# Run this from your local machine to deploy to the Droplet

set -e

# Configuration
DROPLET_IP="147.182.239.22"
DROPLET_USER="mentraflow"  # SSH user (matches your SSH key setup)
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
    --exclude '.venv' \
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
echo ""
echo "   For FIRST-TIME setup:"
echo "   1. ssh ${DROPLET_USER}@${DROPLET_IP}"
echo "   2. cd ${APP_DIR}"
echo "   3. Run: bash scripts/install_app_on_droplet.sh"
echo "   4. Set up systemd service and Nginx (see install script output)"
echo ""
echo "   For UPDATES (after initial setup):"
echo "   1. ssh ${DROPLET_USER}@${DROPLET_IP}"
echo "   2. cd ${APP_DIR}"
echo "   3. Run: bash scripts/update_on_droplet.sh"
echo "   4. Test from your local machine:"
echo "      curl http://${DROPLET_IP}/health"

