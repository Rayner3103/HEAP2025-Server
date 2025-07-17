# HEAP2025
This is a project for HEAP 2025 by .Hacks SMU. 

To run server-python, ensure that you have python installed.
Next, install all necessary packages:
```pip install flask flask-cors supabase python-dotenv```
Next, go to /server-python and type
```python app.py```

# Acadiverse — Backend

This is the backend service for [**Acadiverse**](https://heap-2025-client.vercel.app), a web platform that helps tertiary students discover academic and professional events. It scrapes public event sources and allows authenticated organisations to create and manage event listings.

## 🌐 Website Functionality (Backend Roles)

- RESTful API serving event data to the frontend
- Scraping engine to fetch events from public academic/professional sites
- Organisation authentication and authorization
- Event creation, editing, and deletion for authenticated users
- Image uploads for event listings
- Scheduled scraping with cron jobs

## ⚙️ Tech Stack

- Framework: Flask (FastAPI-style routing)
- Scheduler: APScheduler
- Database: Supabase (PostgreSQL)
- CORS: flask-cors
- Auth: Supabase Auth (JWT)
- Deployment: Render.com

## 🚀 Running Locally

### Prerequisites

- Python 3.10+
- pip or poetry
- Supabase project and API keys

### Steps

1. Clone the repository

   git clone https://github.com/your-org/acadiverse-backend.git
   cd acadiverse-backend

2. Create and activate a virtual environment

   python -m venv venv
   source venv/bin/activate     # On Windows: venv\Scripts\activate

3. Install dependencies

   pip install -r requirements.txt

4. Create a `.env` file

   Add the following environment variables:

   SUPABASE_URL=your_supabase_url  
   SUPABASE_KEY=your_anon_or_service_key  
   SUPABASE_JWT_SECRET=your_jwt_secret  
   IMAGE_UPLOAD_PATH=./static/images  
   CRON_SCHEDULE=0 12 * * *  # Example: run scraper daily at 12PM SGT

5. Run the backend server

   flask run

   # Or if using app.py as the entry point:
   python app.py

6. Visit the API

   Open http://localhost:5000 in your browser

## 🔁 Example Endpoints

- GET /events — List all events
- POST /events — Create a new event (auth required)
- GET /events/<id> — Get event by ID
- DELETE /events/<id> — Delete an event (auth required)
- POST /auth/login — Organisation login
- POST /upload-image — Upload event image

## 👥 Collaborators

- Rayner Sim Zhi Heng
- [Name Placeholder]
- [Name Placeholder]

## 🔗 Hosted Link

Backend: https://acadiverse-backend.onrender.com  
(Used internally by frontend at https://acadiverse.vercel.app)
