# Deploying Frontend + Backend on Same Droplet

Yes! You can deploy both your UI (frontend) and backend on the same Droplet. This is a common and cost-effective setup.

**Note:** This guide assumes your frontend and backend are in **separate repositories**, which is the recommended approach for:
- ✅ Independent version control
- ✅ Separate deployment cycles
- ✅ Different tech stacks (React/Vue vs Python)
- ✅ Team collaboration (frontend/backend teams can work independently)
- ✅ Easier CI/CD setup

---

## 🎯 Deployment Options

### **Option 1: Same Domain, Different Paths** (Recommended)
- Backend: `http://YOUR_DROPLET_IP/api/v1/...` or `http://your-domain.com/api/v1/...`
- Frontend: `http://YOUR_DROPLET_IP/` (root) or `http://your-domain.com/`

### **Option 2: Subdomains**
- Backend: `api.your-domain.com`
- Frontend: `app.your-domain.com` or `your-domain.com`

### **Option 3: Different Ports** (Not recommended)
- Backend: `http://YOUR_DROPLET_IP:8000`
- Frontend: `http://YOUR_DROPLET_IP:3000`

**We'll use Option 1** (same domain, different paths) - it's the cleanest.

---

## 📋 Setup Steps

### **Step 1: Build Your Frontend**

In your **frontend repository**, build for production:

```bash
# Navigate to your frontend repo
cd /path/to/mentraflow-frontend

# Install dependencies (if needed)
npm install
# or
yarn install

# Build for production
npm run build
# or
yarn build

# This creates a `dist/` or `build/` folder
```

### **Step 2: Upload Frontend to Droplet**

From your **frontend repository**:

```bash
# Upload built frontend files
scp -r dist/* mentraflow@YOUR_DROPLET_IP:/var/www/mentraflow-frontend/
# Or if your build folder is named differently:
scp -r build/* mentraflow@YOUR_DROPLET_IP:/var/www/mentraflow-frontend/
```

**Or use the deployment script** (see below for `deploy_frontend_to_droplet.sh`):

### **Step 3: Configure Nginx**

Nginx will serve:
- **Frontend** (static files) from `/var/www/mentraflow-frontend/`
- **Backend** (API) by proxying to `http://127.0.0.1:8000`

**Note:** This nginx configuration is in your frontend repository, not the backend.

---

## 🔧 Nginx Configuration

Here's the complete Nginx config for both frontend and backend (configure this in your frontend repo):

```nginx
server {
    listen 80;
    server_name YOUR_DROPLET_IP your-domain.com;  # Replace with your IP or domain

    # Increase body size for file uploads
    client_max_body_size 50M;
    client_body_timeout 300s;

    # Logging
    access_log /var/log/nginx/mentraflow-access.log;
    error_log /var/log/nginx/mentraflow-error.log;

    # Frontend - Serve static files
    location / {
        root /var/www/mentraflow-frontend;
        try_files $uri $uri/ /index.html;  # For SPA routing
        index index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Backend API - Proxy to FastAPI
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        
        # Headers
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts (important for long-running agent tasks)
        proxy_connect_timeout 75s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Cache control
        proxy_cache_bypass $http_upgrade;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

---

## 📦 Complete Setup Script

### **On Your Droplet:**

```bash
# 1. Create frontend directory
sudo mkdir -p /var/www/mentraflow-frontend
sudo chown -R $USER:$USER /var/www/mentraflow-frontend

# 2. Upload your built frontend files
# (From your local machine, after building)
scp -r dist/* mentraflow@YOUR_DROPLET_IP:/var/www/mentraflow-frontend/

# 3. Update Nginx config (in your frontend repo)
# Copy the config above to your frontend nginx configuration

# 4. Test and restart
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🎨 Frontend Framework Examples

### **React/Vite**
```bash
npm run build  # Creates `dist/` folder
scp -r dist/* mentraflow@YOUR_DROPLET_IP:/var/www/mentraflow-frontend/
```

### **Next.js**
```bash
npm run build  # Creates `.next/` folder
# Next.js needs special setup - see below
```

### **Vue**
```bash
npm run build  # Creates `dist/` folder
scp -r dist/* mentraflow@YOUR_DROPLET_IP:/var/www/mentraflow-frontend/
```

---

## ⚙️ Environment Variables for Frontend

Your frontend needs to know the API URL. Common approaches:

### **Option 1: Build-time Environment Variables**

Create `.env.production` in your frontend:
```env
VITE_API_URL=http://YOUR_DROPLET_IP/api/v1
# or
REACT_APP_API_URL=http://YOUR_DROPLET_IP/api/v1
# When you have a domain:
# VITE_API_URL=https://your-domain.com/api/v1
```

Then build:
```bash
npm run build
```

### **Option 2: Runtime Configuration**

Serve a `config.js` file that your frontend loads:
```javascript
// /var/www/mentraflow-frontend/config.js
window.APP_CONFIG = {
  API_URL: 'http://YOUR_DROPLET_IP/api/v1'
  // When you have a domain:
  // API_URL: 'https://your-domain.com/api/v1'
};
```

---

## 📊 Resource Considerations

Your Droplet has **2GB RAM** - this should be enough for both:

- **Backend**: ~200-400MB RAM (FastAPI + Gunicorn workers)
- **Frontend**: ~50MB RAM (Nginx serving static files)
- **System**: ~200-300MB RAM
- **Total**: ~500-750MB RAM (well within 2GB)

**Recommendation**: Start with both on same Droplet. If you need more resources later, you can:
- Upgrade Droplet to 4GB ($24/month)
- Or move frontend to a CDN (Cloudflare Pages, Vercel, etc.)

---

## 🔒 SSL/HTTPS Setup (When You Get a Domain)

Once you have a domain name:

```bash
# Get SSL certificate for both frontend and backend
sudo certbot --nginx -d your-domain.com

# Certbot will automatically configure both
```

Then:
- Frontend: `https://your-domain.com`
- Backend: `https://your-domain.com/api/v1/...`

---

## 🚀 Quick Deployment Workflow

### **Initial Setup (One-Time)**

```bash
# 1. Set up backend (already done via DEPLOYMENT_DROPLET.md)
# 2. Create frontend directory on Droplet
ssh mentraflow@YOUR_DROPLET_IP
sudo mkdir -p /var/www/mentraflow-frontend
sudo chown -R mentraflow:mentraflow /var/www/mentraflow-frontend

# 3. Configure Nginx (in your frontend repo)
# Use the nginx configuration from your frontend repository
# It should proxy /api/* to http://127.0.0.1:8000
```

### **Deploying Updates**

**Backend (from backend repo):**
```bash
# Use the existing deployment script
cd /path/to/mentraflow-backend
./scripts/deploy_to_droplet.sh

# Or manually:
ssh mentraflow@YOUR_DROPLET_IP
cd /home/mentraflow/mentraflow-backend
git pull  # or rsync from local
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
sudo systemctl restart mentraflow-api
```

**Frontend (from frontend repo):**
```bash
# Build and upload
cd /path/to/mentraflow-frontend
npm run build
scp -r dist/* mentraflow@YOUR_DROPLET_IP:/var/www/mentraflow-frontend/
# That's it! No restart needed for static files
```

---

## 🎯 Recommended Structure

```
/var/www/mentraflow-frontend/     # Frontend static files
  ├── index.html
  ├── assets/
  └── ...

/home/mentraflow/mentraflow-backend/  # Backend code
  ├── app/
  ├── scripts/
  └── ...
```

---

## ✅ Benefits of Same Droplet

1. **Cost Effective**: One server for both
2. **Simple Setup**: One Nginx config
3. **Easy SSL**: One certificate for both
4. **Low Latency**: Frontend and backend on same server
5. **Simple Deployment**: One place to manage

---

## 📝 Nginx Configuration Location

**Important:** The nginx configuration is in your **frontend repository**, not the backend.

The backend doesn't need nginx - it runs on port 8000 and your frontend nginx proxies `/api/*` requests to it.

---

**Last Updated:** 2025-12-29

