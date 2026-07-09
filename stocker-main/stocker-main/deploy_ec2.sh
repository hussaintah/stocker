#!/bin/bash
# ─── Stocker EC2 Deployment Script ───────────────────────────────────────────
# Run on a fresh Ubuntu 22.04 EC2 instance with:
#   bash deploy_ec2.sh

set -e

echo "=== [1/7] Updating system packages ==="
sudo apt-get update -y && sudo apt-get upgrade -y

echo "=== [2/7] Installing Python 3, pip, Nginx ==="
sudo apt-get install -y python3-pip python3-venv nginx

echo "=== [3/7] Cloning / copying app ==="
# If using git:
# git clone https://github.com/YOUR_USERNAME/stocker.git ~/stocker
# Otherwise: already in ~/stocker

cd ~/stocker

echo "=== [4/7] Creating virtual environment & installing deps ==="
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== [5/7] Setting up DynamoDB tables ==="
python setup_dynamodb.py

echo "=== [6/7] Configuring Nginx ==="
sudo mkdir -p /var/log/stocker
sudo cp nginx.conf /etc/nginx/sites-available/stocker
sudo ln -sf /etc/nginx/sites-available/stocker /etc/nginx/sites-enabled/stocker
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

echo "=== [7/7] Creating systemd service ==="
sudo tee /etc/systemd/system/stocker.service > /dev/null <<EOF
[Unit]
Description=Stocker Flask App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/stocker
Environment="PATH=/home/ubuntu/stocker/venv/bin"
ExecStart=/home/ubuntu/stocker/venv/bin/gunicorn -c gunicorn.conf.py app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable stocker
sudo systemctl start stocker

echo ""
echo "✅ Stocker deployed successfully!"
echo "   App running at: http://$(curl -s ifconfig.me)"
echo "   Logs: sudo journalctl -u stocker -f"
