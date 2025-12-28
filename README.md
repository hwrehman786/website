# Blog Website

This is a simple blog website with user registration, login, and post creation functionality.

## Setup

1. **Install Python:** Make sure you have Python 3 installed on your system.

2. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install the required packages:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Environment Variables:**
   For security reasons, the `SECRET_KEY` and `FLASK_DEBUG` are loaded from environment variables.

   **On Windows:**
   ```powershell
   $env:SECRET_KEY = 'a_very_secret_key'
   $env:FLASK_DEBUG = 'true'
   ```

   **On macOS/Linux:**
   ```bash
   export SECRET_KEY='a_very_secret_key'
   export FLASK_DEBUG='true'
   ```

## Running the Application

1. **Run the Flask application:**
   ```bash
   python main.py
   ```

2. **Open your web browser and navigate to:**
   ```
   http://127.0.0.1:5000/
   ```

## Features

- User registration and login
- Create new blog posts
- View all blog posts
- User session management