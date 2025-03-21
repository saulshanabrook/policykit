from __future__ import absolute_import, unicode_literals

from django.conf import settings


import os

from celery import Celery, signals
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from celery.signals import after_setup_logger, after_setup_task_logger

# https://github.com/namespace-ee/django-datadog-logger
@after_setup_logger.connect
def on_after_setup_logger(logger, *args, **kwargs):
    from django_datadog_logger.formatters.datadog import DataDogJSONFormatter

    formatter = DataDogJSONFormatter()
    for handler in list(logger.handlers):
        handler.setFormatter(formatter)
        handler.setLevel(settings.LOG_LEVEL)


@after_setup_task_logger.connect
def on_after_setup_task_logger(logger, *args, **kwargs):
    from django_datadog_logger.formatters.datadog import DataDogJSONFormatter

    formatter = DataDogJSONFormatter()
    for handler in list(logger.handlers):
        handler.setFormatter(formatter)
        handler.setLevel(settings.LOG_LEVEL)

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'policykit.settings')

if settings.DDTRACE:
    import ddtrace
    ddtrace.patch(celery=True)

app = Celery('policykit',
             broker=os.getenv("CELERY_BROKER_URL"),
             include=['policyengine.tasks',
                      'integrations.reddit.tasks',
                      'integrations.discourse.tasks'])

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Don't store task results in the database
app.conf.task_ignore_result = True

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

@signals.celeryd_init.connect
def init_sentry(**kwargs):
    from django.conf import settings
    dsn = settings.SENTRY_SERVER_DSN
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            integrations=[CeleryIntegration(
                # Add when we upgrade to recent version of sentry which includes
                # https://github.com/getsentry/sentry-python/pull/1967
                # monitor_beat_tasks=True
            )],
        )

if __name__ == '__main__':
    app.start()
