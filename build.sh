#!/usr/bin/env bash
# Render build command: ./build.sh
set -o errexit

pip install -r requirements.txt

# staticfiles/ and the SQLite database are not committed, so create them here
python manage.py collectstatic --noinput
python manage.py migrate --noinput
