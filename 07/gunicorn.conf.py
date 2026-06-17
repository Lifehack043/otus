"""
Gunicorn configuration file.
"""

import multiprocessing
import os

# Server Socket
bind = f"0.0.0.0:{os.environ.get('GUNICORN_PORT', '8000')}"
backlog = 2048

# Worker Processes
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "gthread"
threads = 2
worker_connections = 1000
timeout = 120
keepalive = 5
graceful_timeout = 30

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'

# Process Naming
proc_name = "django-polls"

# Server Hooks
def post_fork(server, worker):
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def pre_fork(server, worker):
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def pre_exec(server):
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def worker_abort(worker):
    worker.log.info("worker received SIGABRT signal")
