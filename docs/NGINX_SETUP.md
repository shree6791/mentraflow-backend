# Nginx Setup Guide - One-Time Configuration

This is a **one-time setup** that takes about 2 minutes. After this, Nginx will automatically proxy all requests to your FastAPI application.

---

## ✅ Why Nginx?

- **Standard ports**: Access API at `http://147.182.239.22` (no `:8000` needed)
- **SSL/HTTPS ready**: Easy to add SSL certificate later
- **Better security**: Hides your app port from public
- **Production best practice**: Standard setup for web applications
- **File uploads**: Handles large file uploads better

---

## 🚀 Quick Setup (2 Minutes)

### **Step 1: Copy Configuration**

```bash
# On your Droplet, as root:
sudo cp /home/mentraflow/mentraflow-backend/scripts/nginx.conf /etc/nginx/sites-available/mentraflow-api
```

### **Step 2: Enable Site**

```bash
# Create symlink to enable the site
sudo ln -s /etc/nginx/sites-available/mentraflow-api /etc/nginx/sites-enabled/

# Remove default Nginx site (optional but recommended)
sudo rm /etc/nginx/sites-enabled/default
```

### **Step 3: Test & Restart**

```bash
# Test configuration (make sure no errors)
sudo nginx -t

# If test passes, restart Nginx
sudo systemctl restart nginx

# Check status
sudo systemctl status nginx
```

### **Step 4: Test Your API**

```bash
# Test from your local machine or browser:
curl http://147.182.239.22/health

# Should return:
# {"status":"healthy","database":"connected","qdrant":"connected"}
```

**That's it!** ✅

---

## 🔒 Adding SSL/HTTPS (Later, Optional)

If you get a domain name pointing to your Droplet:

```bash
# Install SSL certificate (free with Let's Encrypt)
sudo certbot --nginx -d your-domain.com

# Certbot will automatically:
# - Get SSL certificate
# - Update Nginx config
# - Set up auto-renewal
```

Then your API will be accessible at:
- `https://your-domain.com` (secure)
- `http://your-domain.com` (redirects to HTTPS)

---

## 🐛 Troubleshooting

### **Nginx won't start**

```bash
# Check configuration syntax
sudo nginx -t

# Check error logs
sudo tail -f /var/log/nginx/error.log
```

### **502 Bad Gateway**

This means Nginx can't reach your app. Check:

```bash
# Is your app running?
sudo systemctl status mentraflow-api

# Is it listening on port 8000?
sudo netstat -tulpn | grep 8000

# Check app logs
sudo journalctl -u mentraflow-api -f
```

### **Can't access API**

```bash
# Check firewall
sudo ufw status

# Make sure port 80 is open
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp  # For HTTPS later
```

---

## 📊 Nginx Logs

```bash
# Access logs (who's hitting your API)
sudo tail -f /var/log/nginx/mentraflow-api-access.log

# Error logs
sudo tail -f /var/log/nginx/mentraflow-api-error.log
```

---

## 🔄 Updating Nginx Config

If you need to change the config later:

```bash
# Edit config
sudo nano /etc/nginx/sites-available/mentraflow-api

# Test
sudo nginx -t

# Reload (no downtime)
sudo systemctl reload nginx
```

---

## ✅ Benefits You Get

1. **Clean URLs**: `http://147.182.239.22` instead of `http://147.182.239.22:8000`
2. **SSL Ready**: Easy to add HTTPS later
3. **Better Security**: App port (8000) not exposed publicly
4. **Production Ready**: Standard web server setup
5. **File Uploads**: Handles large files (50MB limit configured)

---

**Total Setup Time**: ~2 minutes  
**Maintenance**: Zero (runs automatically)  
**Worth It**: ✅ Yes!

---

**Last Updated:** 2025-01-XX

