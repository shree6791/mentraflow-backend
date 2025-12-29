# DigitalOcean Droplet Deployment Guide

Complete guide for deploying MentraFlow backend to a DigitalOcean Droplet (VPS).

---

## 🖥️ Prerequisites

- DigitalOcean Droplet created (Ubuntu 24.04 recommended)
- SSH access to your Droplet
- `.env` file configured with production values
- GitHub repository (or code ready to deploy)

---

## 📋 Complete Deployment Process

### **Step 1: Initial Server Setup (One-Time)**

SSH into your Droplet and run the setup script:

```bash
# SSH into Droplet (use DigitalOcean console or SSH)
ssh root@YOUR_DROPLET_IP

# Run the setup script
cd /root  # or wherever you can access the script
# Upload setup_droplet.sh first, or run commands manually
```

**Or run setup commands manually:**

```bash
# Update system
apt update && apt upgrade -y

# Install Python 3.12 and dependencies
apt install -y python3.12 python3.12-venv python3-pip git curl

# Install PostgreSQL client
apt install -y postgresql-client

# Install Nginx (reverse proxy)
apt install -y nginx

# Install Certbot (for SSL/HTTPS - optional for now)
apt install -y certbot python3-certbot-nginx

# Create application user with sudo access
adduser --disabled-password --gecos "" mentraflow
usermod -aG sudo mentraflow

# Create application directory
mkdir -p /home/mentraflow/mentraflow-backend
chown mentraflow:mentraflow /home/mentraflow/mentraflow-backend
```

---

### **Step 2: Set Up SSH Access (One-Time)**

From your **local machine**, set up SSH keys:

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "your-email@example.com"

# Get your public key
cat ~/.ssh/id_ed25519.pub
```

**On the Droplet** (via DigitalOcean console), add your public key:

```bash
# As mentraflow user
mkdir -p ~/.ssh
nano ~/.ssh/authorized_keys
# Paste your public key, save (Ctrl+X, Y, Enter)
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

**Test SSH from local machine:**

```bash
ssh mentraflow@YOUR_DROPLET_IP
```

---

### **Step 3: Deploy Code to Droplet**

From your **local machine** (in the `mentraflow-backend` directory):

```bash
# Make sure you have .env file
ls -la .env

# Run deployment script
./scripts/deploy_to_droplet.sh
```

This will:
- Upload all code (except venv, .git, etc.)
- Upload your `.env` file separately

**Or manually upload:**

```bash
# Upload code
rsync -avz --exclude 'venv' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.git' \
    --exclude 'qdrant_storage' \
    --exclude '.env' \
    ./ mentraflow@YOUR_DROPLET_IP:/home/mentraflow/mentraflow-backend/

# Upload .env separately
scp .env mentraflow@YOUR_DROPLET_IP:/home/mentraflow/mentraflow-backend/.env
```

---

### **Step 4: Install Application on Droplet**

SSH into your Droplet as `mentraflow` user:

```bash
ssh mentraflow@YOUR_DROPLET_IP
cd /home/mentraflow/mentraflow-backend

# Run installation script
bash scripts/install_app_on_droplet.sh
```

**Or install manually:**

```bash
cd /home/mentraflow/mentraflow-backend

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations
alembic upgrade head
```

---

### **Step 5: Set Up Systemd Service**

**On the Droplet** (as root or with sudo):

```bash
# Copy service file
sudo cp /home/mentraflow/mentraflow-backend/scripts/mentraflow-api.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (starts on boot)
sudo systemctl enable mentraflow-api

# Start service
sudo systemctl start mentraflow-api

# Check status
sudo systemctl status mentraflow-api
```

**Verify it's running:**

```bash
# Check if listening on port 8000
sudo netstat -tlnp | grep :8000

# Test API
curl http://127.0.0.1:8000/health
```

---

### **Step 6: Configure Nginx (One-Time Setup)**

**On the Droplet** (as root or with sudo):

**Option A: Backend Only (API only)**

```bash
# Copy Nginx config
sudo cp /home/mentraflow/mentraflow-backend/scripts/nginx.conf /etc/nginx/sites-available/mentraflow-api

# Enable the site
sudo ln -s /etc/nginx/sites-available/mentraflow-api /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Check status
sudo systemctl status nginx
```

**Option B: Frontend + Backend (if deploying UI too)**

```bash
# Copy complete Nginx config
sudo cp /home/mentraflow/mentraflow-backend/scripts/nginx.conf.complete /etc/nginx/sites-available/mentraflow

# Enable the site
sudo ln -s /etc/nginx/sites-available/mentraflow /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

---

### **Step 7: Verify Deployment**

**From your local machine (test from outside the server):**

```bash
# Test health endpoint
curl http://YOUR_DROPLET_IP/health

# Test API endpoint
curl http://YOUR_DROPLET_IP/api/v1/health

# Test Swagger docs (open in browser)
open http://YOUR_DROPLET_IP/docs
# or
curl http://YOUR_DROPLET_IP/docs
```

**Expected response:**
```json
{"status":"healthy","database":"connected","qdrant":"connected"}
```

**Expected response:**

```json
{"status":"healthy","database":"connected","qdrant":"connected"}
```

---

## 🔧 Troubleshooting

### **Port 8000 Already in Use**

If you see "Address already in use" errors:

```bash
# Find what's using port 8000
sudo lsof -i :8000

# Kill the process
sudo fuser -k 8000/tcp

# Or kill specific process
sudo kill -9 PID

# Check for other services
sudo systemctl list-units --type=service | grep -i mentraflow

# Stop conflicting services
sudo systemctl stop mentraflow.service  # if old service exists
```

### **Service Fails to Start**

```bash
# Check logs
sudo journalctl -u mentraflow-api -n 50 --no-pager

# Check if .env file exists
ls -la /home/mentraflow/mentraflow-backend/.env

# Test app import
cd /home/mentraflow/mentraflow-backend
source venv/bin/activate
python -c "from app.main import app; print('OK')"
```

### **Database Connection Issues**

```bash
# Check DATABASE_URL in .env
grep DATABASE_URL /home/mentraflow/mentraflow-backend/.env

# Test database connection
cd /home/mentraflow/mentraflow-backend
source venv/bin/activate
python -c "
import asyncio
from app.infrastructure.database import check_db_connection
print(asyncio.run(check_db_connection()))
"
```

### **Migrations Fail**

```bash
# Check if alembic directory is uploaded
ls -la /home/mentraflow/mentraflow-backend/alembic/

# Check if app directory is complete
ls -la /home/mentraflow/mentraflow-backend/app/

# Re-upload if missing
# From local machine:
scp -r alembic/ mentraflow@YOUR_DROPLET_IP:/home/mentraflow/mentraflow-backend/
scp -r app/ mentraflow@YOUR_DROPLET_IP:/home/mentraflow/mentraflow-backend/
```

---

## 📝 Useful Commands

### **Service Management**

```bash
# Check API status
sudo systemctl status mentraflow-api

# Restart API
sudo systemctl restart mentraflow-api

# Stop API
sudo systemctl stop mentraflow-api

# View API logs
sudo journalctl -u mentraflow-api -f

# View last 100 log lines
sudo journalctl -u mentraflow-api -n 100 --no-pager
```

### **Nginx Management**

```bash
# Check Nginx status
sudo systemctl status nginx

# Restart Nginx
sudo systemctl restart nginx

# Test Nginx config
sudo nginx -t

# View Nginx logs
sudo tail -f /var/log/nginx/mentraflow-api-access.log
sudo tail -f /var/log/nginx/mentraflow-api-error.log
```

### **Deployment**

```bash
# From local machine - deploy code
./scripts/deploy_to_droplet.sh

# On server - after deployment
sudo systemctl restart mentraflow-api
```

---

## 🔄 Updating the Application

### **Quick Update Process**

**From your local machine:**

```bash
# Deploy code changes
./scripts/deploy_to_droplet.sh
```

**On the Droplet (SSH in):**

```bash
# Quick update (recommended)
cd /home/mentraflow/mentraflow-backend
bash scripts/update_on_droplet.sh
```

This script automatically:
- Updates Python dependencies (if `requirements.txt` changed)
- Runs database migrations (if any new ones)
- Restarts the service

### **Manual Update (if needed)**

If you prefer to update manually:

```bash
cd /home/mentraflow/mentraflow-backend
source venv/bin/activate

# Install new dependencies (if requirements.txt changed)
pip install -r requirements.txt

# Run new migrations (if any)
alembic upgrade head

# Restart service
sudo systemctl restart mentraflow-api

# Verify
sudo systemctl status mentraflow-api
curl http://127.0.0.1:8000/health
```

---

## 🔒 Security Best Practices

1. **Firewall**: Configure UFW to only allow necessary ports
   ```bash
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw enable
   ```

2. **SSH Keys**: Use SSH keys instead of passwords
3. **Non-Root User**: Application runs as `mentraflow` user, not root
4. **Environment Variables**: Never commit `.env` file to git
5. **SSL/HTTPS**: Set up SSL certificate when you have a domain

---

## 🌐 Setting Up SSL/HTTPS (When You Have a Domain)

Once you have a domain name pointing to your Droplet:

```bash
# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Certbot will automatically configure Nginx for HTTPS
# Your API will be accessible at https://your-domain.com
```

---

## 📊 Monitoring

### **Check Resource Usage**

```bash
# CPU and memory
htop
# or
top

# Disk usage
df -h

# Check service status
sudo systemctl status mentraflow-api nginx
```

---

## ✅ Deployment Checklist

- [ ] Droplet created and accessible
- [ ] SSH keys set up
- [ ] Server setup completed (Python, Nginx, etc.)
- [ ] Code deployed to Droplet
- [ ] `.env` file configured
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Database migrations run
- [ ] Systemd service configured and running
- [ ] Nginx configured and running
- [ ] API accessible at `http://YOUR_DROPLET_IP/api/v1/...`
- [ ] Health check returns `{"status":"healthy"}`

---

## 🆘 Getting Help

If you encounter issues:

1. Check service logs: `sudo journalctl -u mentraflow-api -n 100`
2. Check Nginx logs: `sudo tail -f /var/log/nginx/mentraflow-api-error.log`
3. Verify all files are uploaded correctly
4. Check `.env` file has correct values
5. Verify database and Qdrant are accessible

---

**Last Updated:** 2025-12-29
