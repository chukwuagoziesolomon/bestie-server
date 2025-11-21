#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit
set -o nounset
set -o pipefail

echo "Starting build process..."

# Change to project root directory (build.sh is in bestyy/ subdirectory)
cd "$(dirname "$0")/.."
echo "Working directory: $(pwd)"

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
python -B manage.py collectstatic --noinput

# Run database migrations
echo "Running database migrations..."
python -B manage.py migrate

# Create cache table
echo "Creating cache table..."
python -B manage.py createcachetable

# Create superuser automatically
echo "Creating superuser..."
python -B create_superuser.py

# Clear Python cache to force fresh code load
echo "Clearing Python cache..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

echo "Build completed successfully at $(date)"
