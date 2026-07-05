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
- **Port**: 8001 (bound to `0.0.0.0`, so it's reachable from other devices on the same network - e.g. to test on a phone)

### 3. Database (SQLite)
- **Type**: SQLite database file
- **Runs**: local/python - file-based, no server needed
- **File**: `pietro.db` (created on first run)

## Data Flow

1. **User opens browser** → goes to http://127.0.0.1:8001
2. **Flask receives request** → checks session for user_id
3. **If not logged in** → shows login/register page
4. **User submits form** → Flask processes and returns HTML
5. **Database operations** → SQLite stores/retrieves data

## External Dependencies

Mostly self-hosted, with a few lightweight external pieces:
- **Third-party Python package**: `rapidfuzz` (fuzzy string matching, e.g. for item name suggestions)
- **External API**: OpenStreetMap's Nominatim reverse-geocoding endpoint, called client-side from `register.html` to turn a new user's GPS coordinates into a readable location (e.g. "Trastevere, Rome") - best-effort, never blocks registration if it fails
- **External font**: Google Fonts (`Barlow`) imported in `static/style.css`
- **Browser Geolocation API**: used once at registration to pre-fill location/coordinates; not requested again afterwards
- No cloud services, no backend third-party APIs, no analytics/tracking

## File Structure

```
Pietro-Project/
├── app.py              # Main Flask application (backend)
├── pietro.db           # SQLite database (created on first run)
├── SPEC.md             # Original specification
├── DECISIONS.md        # Implementation decisions
├── ARCHITECTURE.md     # This file
├── requirements.txt    # Python dependencies
├── start.sh            # Start script (macOS)
├── stop.sh             # Stop script (macOS)
├── README.md           # User documentation
├── debug_update.py     # One-off maintenance/debug script
├── update_photo.py     # One-off maintenance/debug script
├── templates/          # HTML templates (Jinja2)
│   ├── index.html          # Landing page (logged-out only)
│   ├── login.html
│   ├── register.html
│   ├── forgot_password.html
│   ├── reset_password.html
│   ├── dashboard.html
│   ├── explore.html         # Browse-by-category grid
│   ├── search.html
│   ├── item_detail.html
│   ├── request_item.html
│   ├── add_item.html        # "Your items" grid + add-item modal
│   ├── chat_list.html        # Chat inbox
│   ├── chat.html
│   ├── profile.html          # "My items" / "Borrowed items" tabs
│   ├── notifications.html
│   ├── loading_screen.html    # Shared splash/loading overlay
│   ├── footer_nav.html        # Shared bottom nav + global "add item" popup
│   └── macros.html            # Shared Jinja macros (e.g. user avatar)
└── static/
    ├── style.css        # All CSS (design system: colors, chips, cards, nav, modals)
    ├── manifest.json    # PWA manifest
    ├── apple-touch-icon.png, icon-192.png, icon-512.png
    ├── icons/           # Small inline SVG icon assets
    ├── uploads/         # User-uploaded item/profile photos
    ├── *.otf, *.ttf     # Custom fonts (Apfel Grotezk, GapSans, BBH Bogle)
    └── img_*.png        # Seed/placeholder item images
```

## How to Run

### On macOS:
```bash
./start.sh
```
Note: `start.sh` currently prints `http://127.0.0.1:5000`, but the app actually
listens on port **8001** - use `http://127.0.0.1:8001` (the script's message is stale).

### Manual:
```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py

# Open browser
open http://127.0.0.1:8001
```

## Database Schema

New columns get added via `ALTER TABLE ... ADD COLUMN` in `init_db()` on startup,
so upgrading the app never requires deleting `pietro.db` - existing rows just get
the new column with its default value.

### users table
- id (INTEGER PRIMARY KEY)
- username (TEXT UNIQUE NOT NULL)
- email (TEXT UNIQUE)
- password (TEXT - hashed)
- location (TEXT - free-text neighborhood, e.g. "Trastevere, Rome"; shown to other users)
- categories (TEXT - comma-separated categories of interest, drives notifications)
- photo (TEXT - profile picture filename in `static/uploads/`)
- latitude, longitude (REAL - captured once at registration via the browser's
  Geolocation API; used server-side only, to sort search results by distance -
  never exposed to other users)
- onboarding_seen (INTEGER - 0/1, whether the first-login "add an item" popup has
  already been shown)

### items table
- id (INTEGER PRIMARY KEY)
- name (TEXT NOT NULL)
- description (TEXT)
- owner_id (INTEGER - foreign key → users.id)
- category (TEXT - single category, not a list)
- status (TEXT - `available` / `requested` / `suspended` / `borrowed`)
  - `requested`: not a real item - a placeholder row representing someone's public
    "I'm looking for X" request (see `request_item`/`start_chat_with_item`)
  - `suspended`: owner declined a request, item temporarily off the market
  - `borrowed`: currently lent out (set when a request is accepted, cleared back
    to `available` when the borrower's return is confirmed)
- photo (TEXT - filename in `static/uploads/`)

### requests table
- id (INTEGER PRIMARY KEY)
- item_id (INTEGER - foreign key → items.id)
- borrower_id (INTEGER - foreign key → users.id)
- status (TEXT - `pending` / `accepted` / `declined`)
- created_at (TIMESTAMP)
- returned_at (TEXT - date the return was confirmed, if any)
- return_status (TEXT - `not_returned` / `pending_confirmation` / `returned`;
  drives the return workflow: borrower flags as returned → owner confirms Yes/No)

### messages table
- id (INTEGER PRIMARY KEY)
- request_id (INTEGER - foreign key → requests.id)
- sender_id (INTEGER - foreign key → users.id)
- content (TEXT)
- created_at (TIMESTAMP)
- message_type (TEXT - `text` (default) / `return_request` / `return_confirmed` /
  `return_denied`; non-`text` messages render as system messages in the chat)
- resolved (INTEGER - 0/1, whether a `return_request` system message has already
  been acted on)
- is_read (INTEGER - 0/1, whether the recipient has opened this chat since the
  message was sent; drives the unread dot on the bottom-nav chat icon and the
  chat list)

### password_reset_tokens table
- id (INTEGER PRIMARY KEY)
- user_id (INTEGER - foreign key → users.id)
- token (TEXT UNIQUE - random URL-safe token emailed/shown to the user)
- created_at (TIMESTAMP)
- expires_at (TIMESTAMP - 1 hour after creation)
