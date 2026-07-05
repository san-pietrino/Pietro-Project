# Pietro - Architecture Documentation

## Tech Stack Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Pietro Architecture                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐     HTTP/HTML      ┌─────────────┐     SQL      ┌──────────┐ 
│   Browser   │ ─────────────────→ │   Flask     │ ──────────→ │ SQLite   │ 
│  (Firefox/   │ ←───────────────── │  (Python)   │ ←────────── │  .db     │ 
│   Safari)   │     HTTP/HTML      │  Backend    │             │          │ 
└─────────────┘                    └──────────────┘             └──────────┘ 
                                              │
                                              │ Jinja2 Templates
                                              ▼
                                    ┌──────────────────┐ 
                                    │   HTML/CSS/JS    │ 
                                    │   Templates      │ 
                                    │  (static files)  │ 
                                    └──────────────────┘ 
```

## Why This Stack Was Chosen

### From Specification (Required):
- **Web app**: Must be accessible via browser
- **Database**: Item database mentioned in spec
- **Authentication**: Login/registration system required

### Made by Me (Implementation Decisions):
- **Flask**: Lightweight Python framework, easy for beginners to read and understand
- **SQLite**: No setup required, stores everything in one file, perfect for learning
- **Vanilla HTML/CSS**: No complex JavaScript frameworks, simple to modify
- **Jinja2**: Built into Flask, makes templates easy to read

## Component Details

### 1. Frontend (Browser)
- **Type**: Vanilla HTML/CSS with Jinja2 templates
- **Runs**: local/static - served by Flask
- **Files**: `templates/*.html`, `static/style.css`

### 2. Backend (Flask)
- **Type**: Python Flask application
- **Runs**: local/python - runs as Python process
- **File**: `app.py`
- **Port**: 5000

### 3. Database (SQLite)
- **Type**: SQLite database file
- **Runs**: local/python - file-based, no server needed
- **File**: `pietro.db` (created on first run)

## Data Flow

1. **User opens browser** → goes to http://127.0.0.1:5000
2. **Flask receives request** → checks session for user_id
3. **If not logged in** → shows login/register page
4. **User submits form** → Flask processes and returns HTML
5. **Database operations** → SQLite stores/retrieves data

## External Dependencies

**None** - This is a fully self-hosted application. All components run locally:
- No external APIs
- No cloud services
- No third-party dependencies

## File Structure

```
EDT - PIETRO APP/
├── app.py              # Main Flask application (backend)
├── SPEC.md             # Original specification
├── DECISIONS.md        # Implementation decisions
├── ARCHITECTURE.md     # This file
├── requirements.txt    # Python dependencies
├── start.sh           # Start script (macOS)
├── stop.sh            # Stop script (macOS)
├── README.md          # User documentation
├── templates/         # HTML templates
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── search.html
│   ├── item_detail.html
│   ├── request_item.html
│   ├── add_item.html
│   ├── chat.html
│   └── notifications.html
└── static/
    └── style.css      # CSS styles
```

## How to Run

### On macOS:
```bash
./start.sh
```

### Manual:
```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py

# Open browser
open http://127.0.0.1:5000
```

## Database Schema

### users table
- id (INTEGER PRIMARY KEY)
- username (TEXT UNIQUE)
- password (TEXT - hashed)
- location (TEXT)
- keywords (TEXT - comma separated)

### items table
- id (INTEGER PRIMARY KEY)
- name (TEXT)
- description (TEXT)
- owner_id (INTEGER - foreign key)
- status (TEXT - available/unavailable/requested/suspended)
- keywords (TEXT - comma separated)

### requests table
- id (INTEGER PRIMARY KEY)
- item_id (INTEGER - foreign key)
- borrower_id (INTEGER - foreign key)
- status (TEXT - pending/accepted/declined)
- created_at (TIMESTAMP)

### messages table
- id (INTEGER PRIMARY KEY)
- request_id (INTEGER - foreign key)
- sender_id (INTEGER - foreign key)
- content (TEXT)
- created_at (TIMESTAMP)
