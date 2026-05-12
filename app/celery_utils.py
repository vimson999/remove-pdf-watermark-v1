from celery import Celery

# HARDCODED CLOUD REDIS
cloud_redis = 'redis://:login4RDS!!!@101.35.56.140:6379/0'

# Create a global celery instance
celery_app = Celery('app', broker=cloud_redis, backend=cloud_redis)

# FORCE CONFIGURATION
celery_app.conf.broker_url = cloud_redis
celery_app.conf.result_backend = cloud_redis
celery_app.conf.task_always_eager = False  # Ensure it's not eager

def init_celery(app):
    """Link Celery to Flask app context."""
    celery_app.conf.update(app.config)
    # Re-force after update just in case
    celery_app.conf.broker_url = cloud_redis
    celery_app.conf.result_backend = cloud_redis
    
    class ContextTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask
    return celery_app
