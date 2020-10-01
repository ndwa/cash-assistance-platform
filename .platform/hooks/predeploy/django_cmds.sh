#!/bin/bash
# Source virtual environment. it is not always active during predeployment
source /var/app/venv/staging-LQM1lest/bin/activate
# Collect static files in STATIC_PATH defined in settings.py
python manage.py collectstatic --no-input
# compile .po translations files into .mo files.
python manage.py compilemessages