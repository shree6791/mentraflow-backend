# DigitalOcean Droplet Deployment Guide

This guide covers deploying MentraFlow backend to a DigitalOcean Droplet (VPS).

---

## 🖥️ Your Droplet Setup

Based on your Droplet configuration:
- **Name**: mentraflow-api
- **Public IP**: 147.182.239.22
- **Private IP**: 10.124.0.3
- **Region**: SFO3 (San Francisco)
- **Specs**: 2 GB Memory / 50 GB Disk
- **OS**: Ubuntu 24.04 (LTS) x64

---

## ✅ What You Have

- ✅ Droplet created and running
- ✅ `.env` file configured
- ✅ Public IP address: `147.182.239.22`

---

## 📋 Deployment Steps for Droplet

### **Step 1: SSH into Your Droplet**

```bash
# SSH into your Droplet
ssh root@147.182.239.22
# Or if you've set up a user:
ssh root@147.182.239.22
```

### **Step 2: Initial Server Setup**

```bash
# Update system
apt update && apt upgrade -y

# Install Python 3.12 and dependencies
apt install -y python3.12 python3.12-venv python3-pip git

# Install PostgreSQL client (if using managed DB, you might not need this)
apt install -y postgresql-client

# Install Nginx (reverse proxy)
apt install -y nginx

# Install Certbot (for SSL certificates)
apt install -y certbot python3-certbot-nginx
```

### **Step 3: Create Application User**

```bash
# Create a non-root user for the application
adduser --disabled-password --gecos "" mentraflow
usermod -aG sudo mentraflow

# Switch to application user
su - mentraflow
```

### **Step 4: Clone Your Repository**

```bash
# Clone your repository
cd /home/mentraflow
git clone https://github.com/your-username/mentraflow-backend.git
cd mentraflow-backend

# Or if you prefer, upload files via SCP:
# From your local machine:
# scp -r . mentraflow@147.182.239.22:/home/mentraflow/mentraflow-backend
```

### **Step 5: Set Up Python Environment**

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### **Step 6: Configure Environment Variables**

```bash
# Copy your .env file to the server
# From your local machine:
scp .env mentraflow@147.182.239.22:/home/mentraflow/mentraflow-backend/.env

# Or create it manually on the server:
nano .env
# Paste your environment variables
```

**Important**: Make sure your `.env` has:
- `HOST=0.0.0.0` (not 127.0.0.1)
- `PORT=8000` (or your preferred port)
- `DEBUG=false`
- All your database, Qdrant, and OpenAI credentials

### **Step 7: Run Database Migrations**

```bash
# Activate virtual environment
source venv/bin/activate

# Run migrations
alembic upgrade head
```

### **Step 8: Test the Application**

```bash
# Test run (make sure it works)
source venv/bin/activate
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# In another terminal, test:
curl http://147.182.239.22:8000/health
```

### **Step 9: Set Up Systemd Service**

Create a systemd service to run the app automatically:

```bash
sudo nano /etc/systemd/system/mentraflow-api.service
```

Add this content:

```ini
[Unit]
Description=MentraFlow API
After=network.target

[Service]
Type=simple
User=mentraflow
WorkingDirectory=/home/mentraflow/mentraflow-backend
Environment="PATH=/home/mentraflow/mentraflow-backend/venv/bin"
ExecStart=/home/mentraflow/mentraflow-backend/venv/bin/gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120 --access-logfile - --error-logfile - --log-level info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mentraflow-api
sudo systemctl start mentraflow-api
sudo systemctl status mentraflow-api
```

### **Step 10: Configure Nginx (Reverse Proxy) - One-Time Setup**

**Choose your setup:**

#### **Option A: Backend Only** (API only)
```bash
# Copy the backend-only Nginx configuration
sudo cp /home/mentraflow/mentraflow-backend/scripts/nginx.conf /etc/nginx/sites-available/mentraflow-api
sudo ln -s /etc/nginx/sites-available/mentraflow-api /etc/nginx/sites-enabled/
```

#### **Option B: Frontend + Backend** (Recommended if deploying UI too)
```bash
# Copy the complete Nginx configuration (handles both frontend and backend)
sudo cp /home/mentraflow/mentraflow-backend/scripts/nginx.conf.complete /etc/nginx/sites-available/mentraflow
sudo ln -s /etc/nginx/sites-available/mentraflow /etc/nginx/sites-enabled/

# Create frontend directory
sudo mkdir -p /var/www/mentraflow-frontend
sudo chown -R mentraflow:mentraflow /var/www/mentraflow-frontend
```

**Then for both options:**
```bash
# Remove default Nginx site
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Check status
sudo systemctl status nginx
```

**Your API is now accessible at:**
- `http://147.182.239.22/api/v1/...` (with Option B, frontend at root `/`)
- `http://147.182.239.22/health`

**Note:** See `docs/FRONTEND_BACKEND_DEPLOYMENT.md` for complete frontend + backend setup guide.

### **Step 11: Set Up SSL (Let's Encrypt)**

If you have a domain name pointing to your Droplet:

```bash
sudo certbot --nginx -d your-domain.com
```

This will:
- Get SSL certificate
- Configure Nginx automatically
- Set up auto-renewal

### **Step 12: Configure Firewall**

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
sudo ufw status
```

### **Step 13: Set Up Logging**

```bash
# View application logs
sudo journalctl -u mentraflow-api -f

# View Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

## 🔄 Updating the Application

### **Pull Latest Code**

```bash
cd /home/mentraflow/mentraflow-backend
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install new dependencies (if any)
pip install -r requirements.txt

# Run migrations (if any)
alembic upgrade head

# Restart service
sudo systemctl restart mentraflow-api
```

---

## 🐛 Troubleshooting

### **Service Won't Start**

```bash
# Check service status
sudo systemctl status mentraflow-api

# Check logs
sudo journalctl -u mentraflow-api -n 50

# Check if port is in use
sudo netstat -tulpn | grep 8000
```

### **Application Not Accessible**

```bash
# Check if service is running
sudo systemctl status mentraflow-api

# Check Nginx status
sudo systemctl status nginx

# Check firewall
sudo ufw status

# Test from server
curl http://localhost:8000/health
```

### **Database Connection Issues**

```bash
# Test database connection
psql $DATABASE_URL

# Check if DATABASE_URL is set correctly
echo $DATABASE_URL
```

---

## 📊 Monitoring

### **Resource Usage**

```bash
# CPU and memory
htop

# Disk usage
df -h

# Application logs
sudo journalctl -u mentraflow-api -f
```

### **Set Up Monitoring (Optional)**

Consider setting up:
- DigitalOcean Monitoring (built-in)
- Uptime monitoring (UptimeRobot, Pingdom)
- Application monitoring (Sentry for errors)

---

## 🔒 Security Checklist

- [ ] Firewall configured (UFW)
- [ ] SSH key authentication (disable password auth)
- [ ] Non-root user for application
- [ ] SSL certificate installed
- [ ] Environment variables secured (not in code)
- [ ] Database uses SSL
- [ ] Regular system updates
- [ ] Fail2ban installed (optional but recommended)

---

## 💰 Cost

Your current setup:
- **Droplet**: 2GB RAM / 50GB Disk - ~$12/month
- **Database**: Managed PostgreSQL (if using) - ~$15/month
- **Qdrant**: Cloud (if using) - Free tier or ~$25/month
- **Total**: ~$27-52/month

---

## 🚀 Quick Commands Reference

```bash
# Start service
sudo systemctl start mentraflow-api

# Stop service
sudo systemctl stop mentraflow-api

# Restart service
sudo systemctl restart mentraflow-api

# View logs
sudo journalctl -u mentraflow-api -f

# Check status
sudo systemctl status mentraflow-api

# Reload Nginx
sudo systemctl reload nginx

# Test Nginx config
sudo nginx -t
```

---

**Last Updated:** 2025-01-XX

