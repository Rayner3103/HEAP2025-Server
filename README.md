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

   `git clone https://github.com/Rayner3103/HEAP2025-Server.git`
   
   `cd python-server`

2. Create and activate a virtual environment

   `python -m venv venv`

   `source venv/bin/activate`     
   
   On Windows: `venv\Scripts\activate`

3. Install dependencies

   `pip install -r requirements.txt`

4. Create a `.env` file

   Add the following environment variables:

   ```
   SUPABASE_URL=your_supabase_url 
   SUPABASE_KEY_SERVICE_ROLE = your_service_key  
   SUPABASE_ROOT_USER_PASSWORD = your_root_user_password
   GEMINI_API_KEY = your_google_gemini_api_key
   SERVER_ASSET_PATH = http://localhost:10000/uploads/
   ```

5. Run the backend server

   `python app.py`

6. Visit the API

   Open http://localhost:10000 in your browser

   You should see something like this:
   ```
   {"data":"Active","error":"","status":true}
   ```

## 🔁 Example Endpoints

- GET / — Show server health status
- GET /jobs —Show scrapping job time
- GET /get_all — List all events
- POST /get_all — List all events under a user (auth required)
- For details, please refer to the codes


## 👥 Collaborators

- [Brian Leong Jie Ren](https://www.linkedin.com/in/brian-leong-jie-ren/) (Technical Lead)
- Joel Soh Zhipeng (Development & Research)
- [Rayner Sim Zhi Heng](http://www.linkedin.com/in/raynersimzhiheng) (Systems& Security)
- [Geri Neo Zili](https://www.linkedin.com/in/geri-neo-8865a3341/) (Technical Development)
- [Leong Yan Lyn](https://www.linkedin.com/in/yan-lyn-leong/) (Strategy & User Experience)

## 🔗 Hosted Link

Backend: https://heap2025-server.onrender.com/

(Used internally by frontend at https://heap-2025-client.vercel.app/)
