# Deployment Guide - Hetzner Server

## Prerequisites
- Hetzner server with Docker and Docker Compose installed
- Domain name (optional, but recommended)
- SSH access to your server

## Step 1: Install Docker on Hetzner Server

```bash
# SSH into your server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose -y

# Verify installation
docker --version
docker-compose --version
```

## Step 2: Clone/Upload Your Project

**Option A: Using Git (Recommended)**
```bash
# On your server
cd /opt
git clone https://github.com/yourusername/ascii-fireworks.git
cd ascii-fireworks
```

**Option B: Using SCP**
```bash
# From your local machine
scp -r /path/to/ascii-fireworks root@your-server-ip:/opt/
```

## Step 3: Deploy with Docker Compose

```bash
# On your server
cd /opt/ascii-fireworks

# Build and start containers
docker-compose up -d --build

# Check if containers are running
docker-compose ps

# View logs
docker-compose logs -f
```

## Step 4: Configure Firewall

```bash
# Allow HTTP traffic
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp

# Enable firewall
ufw enable
```

## Step 5: Set Up Nginx Reverse Proxy (Recommended)

### Install Nginx
```bash
apt install nginx -y
```

### Create Nginx Config
```bash
nano /etc/nginx/sites-available/fireworks
```

Paste this configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket timeout
        proxy_read_timeout 86400;
    }
}
```

### Enable the site
```bash
ln -s /etc/nginx/sites-available/fireworks /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

## Step 6: Set Up SSL with Let's Encrypt (Optional but Recommended)

```bash
# Install certbot
apt install certbot python3-certbot-nginx -y

# Get SSL certificate
certbot --nginx -d your-domain.com

# Certbot will automatically configure SSL
```

## Step 7: Configure Auto-Start on Reboot

Docker Compose services with `restart: unless-stopped` will automatically start on reboot.

To ensure Docker starts on boot:
```bash
systemctl enable docker
```

## Management Commands

### View logs
```bash
docker-compose logs -f web
docker-compose logs -f redis
```

### Restart services
```bash
docker-compose restart
```

### Stop services
```bash
docker-compose down
```

### Update deployment
```bash
# Pull latest changes (if using git)
git pull

# Rebuild and restart
docker-compose up -d --build

# Or without downtime
docker-compose build
docker-compose up -d --no-deps web
```

### Check Redis data
```bash
docker-compose exec redis redis-cli
# Then run: GET patakha:counter
```

## Monitoring

### Check container health
```bash
docker-compose ps
docker stats
```

### Check disk space
```bash
df -h
docker system df
```

### Clean up old Docker images
```bash
docker system prune -a
```

## Backup Redis Data

```bash
# Backup
docker-compose exec redis redis-cli SAVE
docker cp ascii-fireworks-redis-1:/data/dump.rdb ./backup-$(date +%Y%m%d).rdb

# Restore
docker cp backup-20241020.rdb ascii-fireworks-redis-1:/data/dump.rdb
docker-compose restart redis
```

## Troubleshooting

### WebSocket connection fails
- Check if port 8000 is open: `netstat -tlnp | grep 8000`
- Check Nginx logs: `tail -f /var/log/nginx/error.log`
- Verify WebSocket upgrade headers in Nginx config

### Redis connection issues
```bash
docker-compose logs redis
docker-compose exec redis redis-cli ping
```

### High memory usage
```bash
# Check Redis memory
docker-compose exec redis redis-cli INFO memory

# Set max memory limit
docker-compose exec redis redis-cli CONFIG SET maxmemory 256mb
docker-compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

## Environment Variables

Edit `.env` file or `docker-compose.yml`:

```env
REDIS_URL=redis://redis:6379
RATE_LIMIT_SECONDS=0.3
```

## Security Best Practices

1. **Change default ports** (if not using Nginx)
2. **Set up firewall rules** (ufw)
3. **Use SSL/HTTPS** (Let's Encrypt)
4. **Regular updates**: `apt update && apt upgrade`
5. **Monitor logs**: `docker-compose logs -f`
6. **Backup Redis data** regularly

## Performance Tuning

### For high traffic:

1. **Scale horizontally** (multiple web containers):
```yaml
services:
  web:
    deploy:
      replicas: 3
```

2. **Use Redis persistence**:
Already configured in docker-compose.yml with `appendonly yes`

3. **Add connection limits** in Nginx:
```nginx
limit_conn_zone $binary_remote_addr zone=addr:10m;
limit_conn addr 10;
```

## Quick Deploy Script

Create `deploy.sh`:
```bash
#!/bin/bash
cd /opt/ascii-fireworks
git pull
docker-compose build
docker-compose up -d
docker-compose logs -f
```

Make it executable: `chmod +x deploy.sh`

---

**Your app will be accessible at:**
- Direct: `http://your-server-ip:8000`
- With Nginx: `http://your-domain.com`
- With SSL: `https://your-domain.com`

🎉 Happy Deploying!

