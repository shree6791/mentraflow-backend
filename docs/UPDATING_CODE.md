# Updating Code on Droplet

Quick reference guide for updating your MentraFlow backend code on the Droplet.

---

## 🚀 Quick Update Process (2 Steps)

### **Step 1: Deploy Code from Local Machine**

From your **local machine** (in the `mentraflow-backend` directory):

```bash
# Deploy code to Droplet
./scripts/deploy_to_droplet.sh
```

This script:
- Uploads code via `rsync` (excludes `.env`, `venv`, `__pycache__`, etc.)
- Uploads `.env` file separately via `scp`
- **Does NOT** restart the service (you'll do that in Step 2)

---

### **Step 2: Update on Droplet**

SSH into your Droplet and run the update script:

```bash
# SSH into Droplet
ssh mentraflow@YOUR_DROPLET_IP

# Run update script
cd /home/mentraflow/mentraflow-backend
bash scripts/update_on_droplet.sh
```

This script automatically:
- ✅ Updates Python dependencies (if `requirements.txt` changed)
- ✅ Runs database migrations (if any new ones)
- ✅ Restarts the service
- ✅ Shows service status

---

## ✅ Verify Update

From your **local machine**:

```bash
# Test health endpoint
curl http://YOUR_DROPLET_IP/health

# Test API endpoint
curl http://YOUR_DROPLET_IP/api/v1/health
```

**Expected response:**
```json
{"status":"healthy","database":"connected","qdrant":"connected"}
```

---

## 🔧 Manual Update (Alternative)

If you prefer to update manually or the script fails:

```bash
# SSH into Droplet
ssh mentraflow@YOUR_DROPLET_IP

# Navigate to app directory
cd /home/mentraflow/mentraflow-backend

# Activate virtual environment
source venv/bin/activate

# Install new dependencies (if requirements.txt changed)
pip install -r requirements.txt

# Run new migrations (if any)
alembic upgrade head

# Restart service
sudo systemctl restart mentraflow-api

# Verify service is running
sudo systemctl status mentraflow-api
```

---

## 📋 What Gets Updated

The `deploy_to_droplet.sh` script uploads:
- ✅ All code files (`app/`, `alembic/`, `scripts/`, etc.)
- ✅ Configuration files (`requirements.txt`, `alembic.ini`, etc.)
- ✅ `.env` file (separately, for security)

**Excluded** (not uploaded):
- ❌ `venv/` or `.venv/` - Virtual environment (recreated on server)
- ❌ `__pycache__/` - Python cache files
- ❌ `.git/` - Git repository
- ❌ `*.pyc` - Compiled Python files
- ❌ `qdrant_storage/` - Local Qdrant storage (if using local Qdrant)

---

## 🐛 Troubleshooting

### **Service Won't Start**

```bash
# Check service logs
sudo journalctl -u mentraflow-api -n 50

# Check for errors
sudo journalctl -u mentraflow-api -n 50 | grep -i error
```

### **Migrations Fail**

```bash
# Check migration status
cd /home/mentraflow/mentraflow-backend
source venv/bin/activate
alembic current
alembic history

# Check database connection
# Verify DATABASE_URL in .env is correct
```

### **Dependencies Won't Install**

```bash
# Check Python version
python3 --version  # Should be 3.12+

# Recreate virtual environment (if needed)
cd /home/mentraflow/mentraflow-backend
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### **Code Not Updating**

```bash
# Verify files were uploaded
ls -la /home/mentraflow/mentraflow-backend/app/

# Check file timestamps
stat /home/mentraflow/mentraflow-backend/app/main.py
```

---

## 📝 Quick Reference

**From local machine:**
```bash
./scripts/deploy_to_droplet.sh
```

**On Droplet:**
```bash
cd /home/mentraflow/mentraflow-backend
bash scripts/update_on_droplet.sh
```

**Test:**
```bash
curl http://YOUR_DROPLET_IP/health
```

---

## 🔗 Related Documentation

- **[Complete Deployment Guide](./DEPLOYMENT_DROPLET.md)** - Full deployment instructions
- **[Deployment Status](./DEPLOYMENT_STATUS.md)** - Current deployment status
- **[Frontend + Backend Deployment](./FRONTEND_BACKEND_DEPLOYMENT.md)** - Deploying both UI and API

---

**Last Updated:** 2025-12-29

