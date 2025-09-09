#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit
set -o nounset
set -o pipefail

echo "Starting build process..."

# Check Python version
echo "Python version:"
python --version

# Upgrade pip and install build tools
echo "Upgrading pip and installing build tools..."
pip install --upgrade pip
pip install setuptools==68.2.2 wheel==0.41.2

# Install dependencies with no cache to avoid issues
echo "Installing Python dependencies..."
pip install -r requirements.txt --no-cache-dir

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
