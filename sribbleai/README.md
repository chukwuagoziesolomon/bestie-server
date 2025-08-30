# Scribble AI

A document-based question answering system using Django and LangChain.

## Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/scribble-ai.git
   cd scribble-ai
   ```

2. **Set up a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` with your actual configuration.

5. **Apply migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

## Project Structure

- `scribbleintimeai/` - Main Django project
- `chat/` - Chat application with AI integration
- `knowledge_base/` - Document storage and processing

## Environment Variables

Copy `.env.example` to `.env` and update the following variables:

- `SECRET_KEY`: Django secret key
- `DEBUG`: Set to `False` in production
- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `OPENROUTER_MODEL`: Default AI model to use (e.g., `meta-llama/llama-3.3-70b-instruct:free`)
- `SITE_URL`: Your site's URL (for OpenRouter headers)

## License

MIT
