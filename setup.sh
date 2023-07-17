#!/bin/bash

# Script to setup a basic flow witout docker

# Install the project dependencies
pip install --no-cache-dir -r requirements.txt

# setting db if not setup
pg_ctl -D /usr/local/var/postgres start # if not already running
createdb taskscheduler # if not already created

createuser taskscheduler
psql taskscheduler -c 'alter user taskscheduler with superuser'

# Set the environment variables
export DJANGO_SETTINGS_MODULE=taskscheduler.settings
export PYTHONPATH=/app

# adding migrations and collecting static 
python ./manage.py makemigrations
python ./manage.py migrate
python ./manage.py collectstatic --no-input

python ./manage.py runserver
# # Start the Gunicorn web server (TODO fix the static issue)
# gunicorn taskscheduler.wsgi:application --bind 0.0.0.0:8400