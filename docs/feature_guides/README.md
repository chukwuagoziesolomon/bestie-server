# Bestyy Server

A comprehensive backend server for the Bestyy platform, built with Django and Django REST framework.

## Features

- User authentication and authorization
- Vendor management system
- Real-time notifications via WebSockets
- RESTful API endpoints
- Admin dashboard

## Documentation

- [API Documentation](docs/API.md)
- [WebSocket Implementation](docs/WEBSOCKETS.md)
- [WebSocket Setup and Testing](WEBSOCKET_SETUP.md)

## Prerequisites

- Python 3.8+
- Redis (for production)
- PostgreSQL (recommended for production)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/bestyy-server.git
   cd bestyy-server
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Run migrations:
   ```bash
   python manage.py migrate
   ```

6. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

## Running the Development Server

```bash
# Start Redis (required for WebSockets in production)
redis-server &

# Start the development server
python manage.py runserver
```

For WebSocket support in development, use Daphne:

```bash
pip install daphne
daphne bestyy.asgi:application
```

## Testing

Run the test suite:

```bash
pytest
```

## WebSocket Support

This project includes real-time WebSocket support for:

- Admin activity feeds
- Vendor notifications
- Real-time updates

See [WebSocket Setup](WEBSOCKET_SETUP.md) for detailed information on setting up and testing WebSockets.

## Deployment

For production deployment, see the [deployment guide](docs/DEPLOYMENT.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
