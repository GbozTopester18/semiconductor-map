# Semiconductor Map — Flask App

## Project Structure

```
semiconductor-map/
├── app.py              # Flask server + REST API
├── data.json           # All fab/company/milestone data (editable)
├── requirements.txt
└── templates/
    ├── index.html      # Animated map (main page)
    └── admin.html      # Data editor UI
```

---

## Run Locally

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the server
python app.py
```

Open your browser at **http://localhost:5000**

- **Map:** http://localhost:5000/
- **Admin panel:** http://localhost:5000/admin

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/data` | Full dataset |
| GET/POST | `/api/fabs` | List / add fabs |
| GET/PUT/DELETE | `/api/fabs/<id>` | Get / update / delete a fab |
| PUT | `/api/fabs/<id>/years` | Replace all year→node entries |
| PUT | `/api/fabs/<id>/years/<year>` | Set one year's node |
| DELETE | `/api/fabs/<id>/years/<year>` | Remove a year entry |
| GET/POST | `/api/companies` | List / add companies |
| PUT/DELETE | `/api/companies/<id>` | Update / delete company |
| GET | `/api/milestones` | All milestones |
| PUT/DELETE | `/api/milestones/<year>` | Set / delete milestones for a year |
| GET/PUT | `/api/coords/<loc_id>` | Get / update a location's coordinates |

---

## Deploy for Free

### Option A — Render (recommended)
1. Push this folder to a GitHub repo
2. Go to https://render.com → New → Web Service
3. Connect your repo
4. Set: **Build command** = `pip install -r requirements.txt`
5. Set: **Start command** = `gunicorn app:app`
6. Add to requirements.txt: `gunicorn`
7. Deploy — you get a free `.onrender.com` URL

### Option B — Railway
1. Push to GitHub
2. Go to https://railway.app → New Project → Deploy from GitHub
3. Railway auto-detects Flask
4. Set start command: `gunicorn app:app`
5. Done — shareable URL in ~2 minutes

### Option C — PythonAnywhere (free tier)
1. Sign up at https://www.pythonanywhere.com
2. Upload files via the Files tab
3. Create a new Web App → Flask → Python 3.12
4. Point WSGI file to your `app.py`

---

## Editing Data

### Via Admin UI
Go to `/admin` in your browser — no code needed.

### Via API (curl examples)

```bash
# Update a fab's node for a specific year
curl -X PUT http://localhost:5000/api/fabs/tsmc-tw/years/2027 \
  -H "Content-Type: application/json" \
  -d '{"node": "N1.4"}'

# Add a new fab
curl -X POST http://localhost:5000/api/fabs \
  -H "Content-Type: application/json" \
  -d '{"id":"tsmc-india","company":"TSMC","loc":"Dholera_IN","name":"TSMC India","years":{"2027":"N28"}}'

# Add a new company
curl -X POST http://localhost:5000/api/companies \
  -H "Content-Type: application/json" \
  -d '{"id":"Rapidus","full":"Rapidus","cat":"foundry","origin":"JP","color":"#ff4d6d"}'
```

All changes are saved instantly to `data.json`.
