# 📈 Stocker — Cloud-Native Stock Trading Platform

> SmartBridge Internship Project | Flask · AWS EC2 · Amazon DynamoDB

Stocker is a next-generation virtual stock trading platform. Users register with $1,00,000 virtual balance and can buy/sell stocks in real time, track their portfolio P&L, and view market data — all backed by AWS infrastructure.

---

## 🏗️ Architecture

```
User Browser
    │
    ▼
AWS EC2 (Ubuntu 22.04)
    ├── Nginx (reverse proxy, port 80)
    └── Gunicorn (WSGI server, port 8000)
            └── Flask Application (app.py)
                    ├── boto3 ──► Amazon DynamoDB
                    │               ├── stocker_users
                    │               ├── stocker_portfolio
                    │               └── stocker_orders
                    └── yfinance ──► Yahoo Finance API (live prices)

Monitoring: Amazon CloudWatch
Storage:    Amazon S3 (static assets / backups)
Auth:       AWS IAM (EC2 role — no hardcoded keys)
```

---

## 🚀 Features

| Feature | Description |
|---------|-------------|
| 🔒 Secure Auth | SHA-256 passwords, Flask sessions, role-based access |
| ⚡ Real-Time Trading | Buy/sell with live prices via yfinance (mock fallback) |
| 💼 Portfolio Tracking | P&L, allocation breakdown, per-holding analytics |
| 🌐 Market Overview | Live prices for top 8 stocks |
| 📋 Transaction History | Full order ledger with timestamps |
| ☁️ Cloud-Native | EC2 + DynamoDB + CloudWatch + IAM |

---

## ⚙️ Local Setup

### Prerequisites
- Python 3.9+
- AWS account with DynamoDB access
- AWS credentials configured (`~/.aws/credentials` or environment variables)

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/stocker.git
cd stocker

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your AWS credentials and secret key

# 5. Create DynamoDB tables
python setup_dynamodb.py

# 6. Run the app
python app.py
# Visit http://localhost:5000
```

---

## ☁️ AWS EC2 Deployment

```bash
# On a fresh Ubuntu 22.04 EC2 instance:
git clone https://github.com/YOUR_USERNAME/stocker.git ~/stocker
cd ~/stocker
chmod +x deploy_ec2.sh
./deploy_ec2.sh
```

### Required EC2 Security Group Rules
| Type | Port | Source |
|------|------|--------|
| HTTP | 80 | 0.0.0.0/0 |
| HTTPS | 443 | 0.0.0.0/0 |
| SSH | 22 | Your IP |

### IAM Role (attach to EC2)
The EC2 instance needs an IAM role with:
- `AmazonDynamoDBFullAccess`
- `CloudWatchAgentServerPolicy`

---

## 🗄️ DynamoDB Schema

### `stocker_users`
| Key | Type | Notes |
|-----|------|-------|
| UserID (PK) | String | UUID |
| email | String | Unique |
| password_hash | String | SHA-256 |
| balance | Number | Decimal |
| full_name | String | |
| role | String | user/admin |

### `stocker_portfolio`
| Key | Type | Notes |
|-----|------|-------|
| UserID (PK) | String | |
| symbol (SK) | String | e.g. AAPL |
| quantity | Number | |
| avg_buy_price | Number | |

### `stocker_orders`
| Key | Type | Notes |
|-----|------|-------|
| OrderID (PK) | String | UUID |
| UserID (GSI) | String | For per-user queries |
| symbol | String | |
| action | String | buy/sell |
| quantity | Number | |
| price | Number | |
| total | Number | |
| timestamp | String | ISO 8601 |

---

## 📁 Project Structure

```
stocker/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── setup_dynamodb.py      # One-time DB table creation
├── gunicorn.conf.py       # Production WSGI config
├── nginx.conf             # Nginx reverse proxy config
├── deploy_ec2.sh          # Automated EC2 deployment script
├── .env.example           # Environment variable template
├── config/
│   └── aws_config.py      # AWS region & table name config
├── utils/
│   ├── stock_data.py      # Price fetching (yfinance + mock)
│   └── helpers.py         # DynamoDB decimal serialization
├── templates/
│   ├── base.html          # Shared layout + sidebar
│   ├── index.html         # Landing page
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── trade.html
│   ├── portfolio.html
│   ├── market.html
│   ├── history.html
│   └── profile.html
└── static/
    ├── css/style.css      # Full design system
    └── js/main.js         # Ticker + flash dismiss
```

---

## 👨‍💻 Developed By

Hussain Taha — B.Tech Information Technology, Amity University Noida  
SmartBridge Cloud Computing Internship (NASSCOM Initiative)

AWS Services Used: **EC2 · DynamoDB · IAM · CloudWatch · S3**
