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
echo "   1. Switch to application user: su - mentraflow"
echo "   2. Clone your repository or upload code to $APP_DIR"
echo "   3. Set up Python virtual environment"
echo "   4. Install dependencies"
echo "   5. Configure .env file"
echo "   6. Run migrations"
echo "   7. Set up systemd service"
echo "   8. Configure Nginx"

