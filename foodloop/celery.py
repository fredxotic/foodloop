"""
Celery configuration for FoodLoop

Handles background tasks including:
- Email sending
- Notification processing  
- Analytics generation
- Cache warming
- Data cleanup
- AI model updates
"""

import os
from celery import Celery
from django.conf import settings
from decouple import config

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodloop.settings')

# Create Celery application
app = Celery('foodloop')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Celery Configuration
app.conf.update(
    # Broker settings
    broker_url=config('CELERY_BROKER_URL', default='redis://127.0.0.1:6379/0'),
    result_backend=config('CELERY_RESULT_BACKEND', default='redis://127.0.0.1:6379/0'),
    
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Africa/Nairobi',
    enable_utc=True,
    
    # Task execution settings
    task_always_eager=config('CELERY_TASK_ALWAYS_EAGER', default=False, cast=bool),
    task_eager_propagates=True,
    task_ignore_result=False,
    task_store_eager_result=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Beat scheduler settings (for periodic tasks)
    beat_scheduler='django_celery_beat.schedulers:DatabaseScheduler',
    
    # Task routing
    task_routes={
        'core.tasks.send_email': {'queue': 'emails'},
        'core.tasks.process_notifications': {'queue': 'notifications'},
        'core.tasks.generate_analytics': {'queue': 'analytics'},
        'core.tasks.cleanup_*': {'queue': 'cleanup'},
        'core.tasks.ai_*': {'queue': 'ai'},
    },
    
    # Queue configuration
    task_default_queue='default',
    task_queues={
        'default': {
            'exchange': 'default',
            'exchange_type': 'direct',
            'routing_key': 'default',
        },
        'emails': {
            'exchange': 'emails',
            'exchange_type': 'direct',
            'routing_key': 'emails',
        },
        'notifications': {
            'exchange': 'notifications', 
            'exchange_type': 'direct',
            'routing_key': 'notifications',
        },
        'analytics': {
            'exchange': 'analytics',
            'exchange_type': 'direct', 
            'routing_key': 'analytics',
        },
        'cleanup': {
            'exchange': 'cleanup',
            'exchange_type': 'direct',
            'routing_key': 'cleanup',
        },
        'ai': {
            'exchange': 'ai',
            'exchange_type': 'direct',
            'routing_key': 'ai',
        },
    },
    
    # Retry settings
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    task_max_retries=3,
    task_default_retry_delay=60,
    
    # Result settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
    },
    
    # Security
    worker_hijack_root_logger=False,
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
)

# Auto-discover tasks from installed apps
app.autodiscover_tasks()

# Health check task
@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery connectivity"""
    print(f'Request: {self.request!r}')
    return 'Celery is working!'

# Configure periodic tasks
app.conf.beat_schedule = {
    # Send expiry reminders every 30 minutes
    'send-expiry-reminders': {
        'task': 'core.tasks.send_expiry_reminders',
        'schedule': 30 * 60,  # 30 minutes
        'options': {'queue': 'notifications'}
    },
    
    # Clean up expired donations every hour
    'cleanup-expired-donations': {
        'task': 'core.tasks.cleanup_expired_donations',
        'schedule': 60 * 60,  # 1 hour
        'options': {'queue': 'cleanup'}
    },
    
    # Generate daily analytics at midnight
    'generate-daily-analytics': {
        'task': 'core.tasks.generate_daily_analytics',
        'schedule': 0,  # Daily at midnight
        'options': {'queue': 'analytics'}
    },
    
    # Warm up popular caches every 15 minutes
    'warm-cache': {
        'task': 'core.tasks.warm_popular_caches',
        'schedule': 15 * 60,  # 15 minutes
        'options': {'queue': 'default'}
    },
    
    # Clean up old notifications weekly
    'cleanup-old-notifications': {
        'task': 'core.tasks.cleanup_old_notifications',
        'schedule': 7 * 24 * 60 * 60,  # Weekly
        'options': {'queue': 'cleanup'}
    },
    
    # Update AI recommendations every hour
    'update-ai-recommendations': {
        'task': 'core.tasks.update_ai_recommendations',
        'schedule': 60 * 60,  # 1 hour
        'options': {'queue': 'ai'}
    },
    
    # Send weekly nutrition reports on Sunday at 9 AM
    'send-weekly-nutrition-reports': {
        'task': 'core.tasks.send_weekly_nutrition_reports',
        'schedule': {
            'minute': 0,
            'hour': 9,
            'day_of_week': 0,  # Sunday
        },
        'options': {'queue': 'emails'}
    },
}

if __name__ == '__main__':
    app.start()