# Pietro - Peer-to-Peer Lending Web App

Pietro is a local web app that helps neighbors share items with each other. Think of it as a community library for physical objects!

## What It Does test

- **Borrow**: Search for items your neighbors have and request to borrow them
- **Lend**: List items you own and let others borrow them
- **Connect**: Chat with other users to arrange exchanges

## Prerequisites

- Python 3.7 or higher
- A web browser (Firefox, Safari, Chrome)

## How to Start

### On macOS:

```bash
./start.sh
```

### On Windows:

```batch
start.bat
```

### Manual:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Then open your browser and go to: **http://127.0.0.1:5000**

## How to Stop

### On macOS:

```bash
./stop.sh
```

### On Windows:

```batch
stop.bat
```

### Manual:

Press `Ctrl+C` in the terminal where the app is running.

## File Guide

| File | What It Is |
|------|------------|
| `app.py` | The main application - handles all the logic |
| `templates/` | HTML pages for each view |
| `static/style.css` | The visual design |
| `pietro.db` | The database (created when you first run) |
| `DECISIONS.md` | Why I made certain implementation choices |
| `ARCHITECTURE.md` | How the system works technically |

## Quick Start Guide

1. **Register**: Create an account with your username, password, and location
2. **Add Items**: Go to "Add Item" to list things you're willing to lend
3. **Search**: Look for items other people have listed
4. **Borrow**: Request to borrow an item
5. **Chat**: Once your request is accepted, chat with the owner to arrange pickup

## Need Help?

- Read `DECISIONS.md` to understand implementation choices
- Read `ARCHITECTURE.md` to understand the system design
- Check the code comments in `app.py` for technical details

---

Made with ❤️ for community sharing