"""Gunicorn settings (values overridable through environment variables)."""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get('GUNICORN_WORKERS', '2'))
# gthread: the chat and notification endpoints are polled; threads keep a slow
# client from pinning a whole worker process.
worker_class = 'gthread'
threads = int(os.environ.get('GUNICORN_THREADS', '4'))
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '30'))
graceful_timeout = 20          # ECS sends SIGTERM, then SIGKILL after stopTimeout
keepalive = 65                 # longer than the ALB idle timeout (60 s)
max_requests = 1000            # recycle workers to bound memory growth
max_requests_jitter = 100
# tmpfs for worker heartbeat files: the container root filesystem is read-only
worker_tmp_dir = '/dev/shm'  # nosec B108
forwarded_allow_ips = '*'      # traffic only reaches the task from the ALB security group

accesslog = '-'
errorlog = '-'
# One JSON object per request -> queryable fields in CloudWatch Logs Insights.
# %({x-forwarded-for}i)s is logged raw; the trusted client IP is resolved in Django.
access_log_format = (
    '{"event": "access", "method": "%(m)s", "path": "%(U)s", "status": %(s)s, '
    '"bytes": "%(B)s", "duration_ms": %(M)s, "forwarded_for": "%({x-forwarded-for}i)s", '
    '"user_agent": "%(a)s"}'
)
