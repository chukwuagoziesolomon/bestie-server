#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit
set -o nounset
set -o pipefail

echo "Starting build process..."

# Check Python version
echo "Python version:"
python --version

# Upgrade pip first
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies from working environment
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Create cache table
echo "Creating cache table..."
python manage.py createcachetable

echo "Build completed successfully!"
