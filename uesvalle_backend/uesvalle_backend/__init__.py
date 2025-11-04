"""
Uesvalle Backend
================

Django + Celery configuration for ETL pipeline.
"""

from .celery import app as celery_app

__all__ = ('celery_app',)

