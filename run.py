import os
# TRIPLE-FORCE CLEANUP OF ALL PROXIES
for key in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
    if key in os.environ: del os.environ[key]
os.environ['NO_PROXY'] = '*' # Disable proxy for everything in this process

# FORCE ENV VARS BEFORE ANY IMPORTS
cloud_redis = 'redis://:login4RDS!!!@101.35.56.140:6379/0'
os.environ['CELERY_BROKER_URL'] = cloud_redis
os.environ['CELERY_RESULT_BACKEND'] = cloud_redis

from app import create_app
from app.celery_utils import init_celery

config_name = os.getenv('FLASK_CONFIG') or 'default'
app = create_app(config_name)
celery = init_celery(app)

if __name__ == '__main__':
    # Determine port, default to 5005 to avoid conflicts
    port = int(os.environ.get("PORT", 5005))
    # Enable debug mode for auto-reloading
    app.run(host='0.0.0.0', port=port, debug=True)
