#!/bin/bash
# Server setup script - Run this ON the Droplet after initial SSH
# This sets up the server environment

set -e

echo "🖥️  Setting up MentraFlow on Droplet..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.12 and dependencies
echo "🐍 Installing Python 3.12..."
sudo apt install -y python3.12 python3.12-venv python3-pip git curl

# Install PostgreSQL client (for database connections)
echo "🗄️  Installing PostgreSQL client..."
sudo apt install -y postgresql-client

# Install Nginx (reverse proxy - one-time setup)
echo "🌐 Installing Nginx..."
sudo apt install -y nginx

# Install Certbot for SSL (optional, for later)
echo "🔒 Installing Certbot (for SSL/HTTPS)..."
sudo apt install -y certbot python3-certbot-nginx

# Create application user (if it doesn't exist)
if ! id "mentraflow" &>/dev/null; then
    echo "👤 Creating application user..."
    sudo adduser --disabled-password --gecos "" mentraflow
    sudo usermod -aG sudo mentraflow
    echo "✅ User 'mentraflow' created and added to sudo group"
else
    # Ensure user is in sudo group (in case it was created without it)
    if ! groups mentraflow | grep -q sudo; then
        echo "👤 Adding mentraflow to sudo group..."
        sudo usermod -aG sudo mentraflow
        echo "✅ User 'mentraflow' added to sudo group"
    fi
fi

# Set up application directory
APP_DIR="/home/mentraflow/mentraflow-backend"
if [ ! -d "$APP_DIR" ]; then
    echo "📁 Creating application directory..."
    sudo mkdir -p $APP_DIR
    sudo chown mentraflow:mentraflow $APP_DIR
fi

echo "✅ Server setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Set up SSH keys for mentraflow user (from your local machine)"
echo "   2. Deploy code using: ./scripts/deploy_to_droplet.sh (from local machine)"
echo "   3. SSH as mentraflow user and run: bash scripts/install_app_on_droplet.sh"
echo "   4. Set up systemd service and Nginx (see install script output)"
echo ""
echo "📚 See docs/DEPLOYMENT_DROPLET.md for complete deployment guide"

