# Gunicorn configuration for AWS EC2 production deployment
bind = "0.0.0.0:8000"
workers = 4
worker_class = "sync"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
accesslog = "/var/log/stocker/access.log"
errorlog = "/var/log/stocker/error.log"
loglevel = "info"
