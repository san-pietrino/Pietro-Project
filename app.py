# Pietro - Backend Application
# This is the main Flask application that handles all API requests
# → see DECISIONS.md #1 (Flask chosen for simplicity)

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from rapidfuzz import fuzz
import math
import os
import re

app = Flask(__name__)
app.secret_key = 'pietro-secret-key-change-in-production'  # → see DECISIONS.md #2
app.permanent_session_lifetime = timedelta(days=30)

# Database configuration
DATABASE = 'pietro.db'


@app.url_defaults
def add_static_file_version(endpoint, values):
    """Bust the browser cache for static files (icons, CSS, etc.) whenever the
    underlying file changes, by appending its mtime as a query param. Without
    this, re-uploading an asset under the same filename (e.g. a new SVG icon)
    keeps serving the old cached version."""
    if endpoint != 'static' or 'filename' not in values:
        return
    filepath = os.path.join(app.static_folder, values['filename'])
    if os.path.exists(filepath):
        values['v'] = int(os.path.getmtime(filepath))

# Categories shown on the Explore page grid, with an icon/colour used since items don't have category images yet.
EXPLORE_CATEGORIES = [
    {'name': 'Tools', 'icon': '🛠️', 'color': 'color-green'},
    {'name': 'Kitchen', 'icon': '🍳', 'color': 'color-blue'},
    {'name': 'Electronics', 'icon': '🔌', 'color': 'color-pink'},
    {'name': 'Study & Office', 'icon': '📚', 'color': 'color-orange'},
    {'name': 'Sports & Outdoor', 'icon': '⚽', 'color': 'color-green'},
    {'name': 'Events & Parties', 'icon': '🎉', 'color': 'color-blue'},
    {'name': 'Creative & Hobby', 'icon': '🎨', 'color': 'color-pink'},
    {'name': 'Gaming', 'icon': '🎮', 'color': 'color-orange'},
    {'name': 'Home & Living', 'icon': '🛋️', 'color': 'color-green'},
    {'name': 'Mobility', 'icon': '🚲', 'color': 'color-blue'},
    {'name': 'Baby & Child', 'icon': '🧸', 'color': 'color-pink'},
    {'name': 'Pets', 'icon': '🐾', 'color': 'color-orange'},
]


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km between two coordinates, or None if either is missing."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    earth_radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return earth_radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_db_connection():
    """Get a database connection. Creates tables if they don't exist."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.create_function('distance_km', 4, haversine_km)
    return conn


def schema_exists():
    """Check if the new schema exists (has email column in users table)."""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('PRAGMA table_info(users)')
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        return 'email' in columns
    except:
        return False


def migrate_database():
    """Migrate old database schema to new one."""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute('''SELECT name FROM sqlite_master WHERE type='table' AND name='users' ''')
        if not cursor.fetchone():
            conn.close()
            return  # No old database
        
        # Rename old table
        cursor.execute('ALTER TABLE users RENAME TO users_old')
        
        # Create new users table with correct schema
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password TEXT NOT NULL,
                location TEXT,
                categories TEXT
            )
        ''')
        
        # Migrate data from old table
        cursor.execute('''
            INSERT INTO users (id, username, password, location, categories)
            SELECT id, username, password, location, keywords FROM users_old
        ''')
        
        # Drop old table
        cursor.execute('DROP TABLE users_old')
        
        # Do the same for items table if needed
        cursor.execute('''SELECT name FROM sqlite_master WHERE type='table' AND name='items' ''')
        if cursor.fetchone():
            cursor.execute('PRAGMA table_info(items)')
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'category' not in columns:
                cursor.execute('ALTER TABLE items RENAME TO items_old')
                cursor.execute('''
                    CREATE TABLE items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        owner_id INTEGER NOT NULL,
                        category TEXT,
                        status TEXT DEFAULT 'available',
                        photo TEXT,
                        FOREIGN KEY (owner_id) REFERENCES users (id)
                    )
                ''')
                cursor.execute('''
                    INSERT INTO items (id, name, description, owner_id, status, photo)
                    SELECT id, name, description, owner_id, status, NULL FROM items_old
                ''')
                cursor.execute('DROP TABLE items_old')
        
        conn.commit()
        conn.close()
        print("Database migration completed successfully")
    except Exception as e:
        print(f"Migration error: {e}")


def init_db():
    """Initialize the database with required tables and migrate schema."""
    # Check if migration is needed
    if not schema_exists():
        migrate_database()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password TEXT NOT NULL,
            location TEXT,
            categories TEXT
        )
    ''')

    cursor.execute('PRAGMA table_info(users)')
    user_columns = [row[1] for row in cursor.fetchall()]
    if 'photo' not in user_columns:
        cursor.execute('ALTER TABLE users ADD COLUMN photo TEXT')
    if 'latitude' not in user_columns:
        cursor.execute('ALTER TABLE users ADD COLUMN latitude REAL')
    if 'longitude' not in user_columns:
        cursor.execute('ALTER TABLE users ADD COLUMN longitude REAL')
    if 'onboarding_seen' not in user_columns:
        cursor.execute('ALTER TABLE users ADD COLUMN onboarding_seen INTEGER DEFAULT 0')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            owner_id INTEGER NOT NULL,
            category TEXT,
            status TEXT DEFAULT 'available',
            photo TEXT,
            FOREIGN KEY (owner_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            borrower_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items (id),
            FOREIGN KEY (borrower_id) REFERENCES users (id)
        )
    ''')
    
    cursor.execute('PRAGMA table_info(requests)')
    request_columns = [row[1] for row in cursor.fetchall()]
    if 'returned_at' not in request_columns:
        cursor.execute('ALTER TABLE requests ADD COLUMN returned_at TEXT')
    if 'return_status' not in request_columns:
        cursor.execute("ALTER TABLE requests ADD COLUMN return_status TEXT DEFAULT 'not_returned'")
        cursor.execute("UPDATE requests SET return_status = 'returned' WHERE returned_at IS NOT NULL")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (request_id) REFERENCES requests (id),
            FOREIGN KEY (sender_id) REFERENCES users (id)
        )
    ''')

    cursor.execute('PRAGMA table_info(messages)')
    message_columns = [row[1] for row in cursor.fetchall()]
    if 'message_type' not in message_columns:
        cursor.execute("ALTER TABLE messages ADD COLUMN message_type TEXT DEFAULT 'text'")
    if 'resolved' not in message_columns:
        cursor.execute('ALTER TABLE messages ADD COLUMN resolved INTEGER DEFAULT 0')
    if 'is_read' not in message_columns:
        cursor.execute('ALTER TABLE messages ADD COLUMN is_read INTEGER DEFAULT 0')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()


@app.context_processor
def inject_current_user_photo():
    """Make the logged-in user's profile photo available to every template."""
    if 'user_id' not in session:
        return {'current_user_photo': None}
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT photo FROM users WHERE id = ?', (session['user_id'],))
    row = cursor.fetchone()
    conn.close()
    return {'current_user_photo': row['photo'] if row else None}


@app.context_processor
def inject_unread_messages():
    """Make it known to every template whether the logged-in user has any
    unread chat messages, so the bottom-nav chat icon can show a dot."""
    if 'user_id' not in session:
        return {'has_unread_messages': False}
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 1
        FROM messages m
        JOIN requests r ON m.request_id = r.id
        JOIN items i ON r.item_id = i.id
        WHERE (i.owner_id = ? OR r.borrower_id = ?)
          AND m.sender_id != ?
          AND m.is_read = 0
        LIMIT 1
    ''', (session['user_id'], session['user_id'], session['user_id']))
    row = cursor.fetchone()
    conn.close()
    return {'has_unread_messages': row is not None}


# ==================== AUTHENTICATION ====================

@app.route('/')
def index():
    """Home page - shows the landing page to logged-out visitors only."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page - handles new user creation."""
    categories_list = [
        'Tools', 'Kitchen', 'Electronics', 'Study & Office', 'Sports & Outdoor',
        'Events & Parties', 'Creative & Hobby', 'Gaming', 'Home & Living',
        'Mobility', 'Baby & Child', 'Pets'
    ]
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        location = request.form.get('location')
        categories = request.form.getlist('categories')
        latitude = request.form.get('latitude', type=float)
        longitude = request.form.get('longitude', type=float)
        
        # Validation
        if not username or not email or not password:
            return render_template('register.html', 
                                 error='Username, email and password are required',
                                 categories=categories_list)
        
        if password != password_confirm:
            return render_template('register.html', 
                                 error='Passwords do not match',
                                 categories=categories_list)
        
        if not categories:
            return render_template('register.html', 
                                 error='You must select at least one category of interest',
                                 categories=categories_list)
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Check if username already exists
            cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            if cursor.fetchone():
                return render_template('register.html', 
                                     error='Username already exists',
                                     categories=categories_list)
            
            # Check if email already exists
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            if cursor.fetchone():
                return render_template('register.html', 
                                     error='Email already exists',
                                     categories=categories_list)
            
            # Create new user
            hashed_password = generate_password_hash(password)
            categories_str = ','.join(categories)
            cursor.execute(
                'INSERT INTO users (username, email, password, location, categories, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (username, email, hashed_password, location, categories_str, latitude, longitude)
            )
            conn.commit()

            # Log the new account straight in - no need to make them re-enter the
            # password they just typed on the previous screen.
            session.permanent = True
            session['user_id'] = cursor.lastrowid
            session['username'] = username
            session['login_success'] = True
            return redirect(url_for('dashboard'))
        except Exception as e:
            return render_template('register.html', 
                                 error=str(e),
                                 categories=categories_list)
        finally:
            conn.close()
    
    return render_template('register.html', categories=categories_list)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page - authenticates users."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Try to get user - handle both old and new schema
        try:
            cursor.execute('SELECT id, username, password, email FROM users WHERE username = ? OR email = ?', (username, username))
            user = cursor.fetchone()
        except sqlite3.OperationalError:
            # Fallback for old schema without email column
            cursor.execute('SELECT id, username, password FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
        
        conn.close()
        
        if not user:
            # User not found - redirect to registration
            return redirect(url_for('register'))
        
        if check_password_hash(user['password'], password):
            session.permanent = bool(request.form.get('remember_me'))
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['login_success'] = True  # Flag to show success message on dashboard
            # Success - redirect to dashboard
            return redirect(url_for('dashboard'))
        else:
            # Password is wrong
            return render_template('login.html', error='The password is wrong. Try again')

    error = None
    if request.args.get('session_expired'):
        error = 'Your session has expired. Please log in again.'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    """Logout - clears session and redirects to login."""
    session.clear()
    return redirect(url_for('login'))


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Password recovery form."""
    if request.method == 'POST':
        email = request.form.get('email')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if user:
            # Generate a unique token for password reset
            import secrets
            token = secrets.token_urlsafe(32)
            cursor.execute('''
                INSERT INTO password_reset_tokens (user_id, token, expires_at)
                VALUES (?, ?, datetime('now', '+1 hour'))
            ''', (user['id'], token))
            conn.commit()
            
            # TODO: Send email with reset link
            # For now, show the token (in production, send via email)
            reset_link = url_for('reset_password', token=token, _external=True)
            conn.close()
            return render_template('forgot_password.html', 
                                 message=f'Password reset link: {reset_link}')
        
        conn.close()
        return render_template('forgot_password.html', 
                             message='If an account with that email exists, you will receive a password reset link.')
    
    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password using token."""
    if request.method == 'POST':
        new_password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        if not new_password or new_password != password_confirm:
            return render_template('reset_password.html', 
                                 token=token,
                                 error='Passwords do not match')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify token is valid and not expired
        cursor.execute('''
            SELECT user_id FROM password_reset_tokens
            WHERE token = ? AND expires_at > datetime('now')
        ''', (token,))
        reset_token = cursor.fetchone()
        
        if not reset_token:
            conn.close()
            return render_template('reset_password.html', 
                                 error='Invalid or expired token')
        
        # Update password
        hashed_password = generate_password_hash(new_password)
        cursor.execute('UPDATE users SET password = ? WHERE id = ?', 
                      (hashed_password, reset_token['user_id']))
        
        # Remove used token
        cursor.execute('DELETE FROM password_reset_tokens WHERE token = ?', (token,))
        
        conn.commit()
        conn.close()
        
        return render_template('reset_password.html', 
                             message='Password reset successfully. You can now login with your new password.')
    
    return render_template('reset_password.html', token=token)


# ==================== DASHBOARD ====================

@app.route('/dashboard')
def dashboard():
    """User's personalized dashboard - shows their items and requests."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    success_message = None
    if session.pop('login_success', False):
        success_message = 'You are successfully logged in'

    conn = get_db_connection()
    cursor = conn.cursor()

    # Show the "add an item" prompt once, the first time this user reaches the dashboard.
    cursor.execute('SELECT onboarding_seen FROM users WHERE id = ?', (session['user_id'],))
    onboarding_row = cursor.fetchone()
    show_add_item_prompt = bool(onboarding_row) and not onboarding_row['onboarding_seen']
    if show_add_item_prompt:
        cursor.execute('UPDATE users SET onboarding_seen = 1 WHERE id = ?', (session['user_id'],))
        conn.commit()

    # Get user's items
    cursor.execute('SELECT * FROM items WHERE owner_id = ?', (session['user_id'],))
    my_items = cursor.fetchall()
    
    # Get requests for my items. Excludes accepted ones (once accepted, it's no
    # longer "pending" so it shouldn't linger here) but keeps declined ones. Also
    # excludes requests against my own "wanted" placeholder items (status='requested')
    # - those come from someone responding to my public "looking for X" post with
    # "I have one!", so *they* have the item and *I* am the one who wanted it;
    # showing them here would wrongly claim they're requesting it.
    cursor.execute('''
        SELECT r.id, r.status, r.created_at, i.name as item_name, i.photo as item_photo, u.username as borrower
        FROM requests r
        JOIN items i ON r.item_id = i.id
        JOIN users u ON r.borrower_id = u.id
        WHERE i.owner_id = ? AND i.status != 'requested' AND r.status != 'accepted'
        ORDER BY r.created_at DESC
    ''', (session['user_id'],))
    requests_for_me = cursor.fetchall()

    # Get requested items matching the user's categories
    cursor.execute('SELECT categories FROM users WHERE id = ?', (session['user_id'],))
    user_categories_row = cursor.fetchone()
    user_categories = []
    if user_categories_row and user_categories_row['categories']:
        user_categories = [cat.strip() for cat in user_categories_row['categories'].split(',') if cat.strip()]

    matching_requested_items = []
    seen_request_ids = set()
    if user_categories:
        for category in user_categories:
            cursor.execute('''
                SELECT i.id, i.name, i.description, i.photo, u.username as owner
                FROM items i
                JOIN users u ON i.owner_id = u.id
                WHERE i.category LIKE ? AND i.owner_id != ? AND i.status = 'requested'
                ORDER BY i.id DESC
            ''', (f'%{category}%', session['user_id']))
            for item in cursor.fetchall():
                if item['id'] not in seen_request_ids:
                    matching_requested_items.append(item)
                    seen_request_ids.add(item['id'])

    if not matching_requested_items:
        cursor.execute('''
            SELECT i.id, i.name, i.description, i.photo, u.username as owner
            FROM items i
            JOIN users u ON i.owner_id = u.id
            WHERE i.owner_id != ? AND i.status = 'requested'
            ORDER BY i.id DESC
        ''', (session['user_id'],))
        matching_requested_items = cursor.fetchall()

    # Get the items I'm looking for myself (created via "Request an Item")
    cursor.execute('''
        SELECT id, name, photo
        FROM items
        WHERE owner_id = ? AND status = 'requested'
        ORDER BY id DESC
    ''', (session['user_id'],))
    my_open_requests = cursor.fetchall()

    # Get my borrowing requests
    cursor.execute('''
        SELECT r.id, r.status, r.created_at, i.name as item_name
        FROM requests r
        JOIN items i ON r.item_id = i.id
        WHERE r.borrower_id = ?
        ORDER BY r.created_at DESC
    ''', (session['user_id'],))
    my_requests = cursor.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html',
                         username=session['username'],
                         success_message=success_message,
                         show_add_item_prompt=show_add_item_prompt,
                         my_items=my_items,
                         requests_for_me=requests_for_me,
                         matching_requested_items=matching_requested_items,
                         my_open_requests=my_open_requests,
                         my_requests=my_requests)


@app.route('/explore')
def explore():
    """Explore page - browse items by category, opened from the bottom nav."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('explore.html', categories=EXPLORE_CATEGORIES)


@app.route('/start-chat/<int:item_id>', methods=['GET', 'POST'])
def start_chat_with_item(item_id):
    """Create or reuse a chat request for a requested item and redirect to the chat.

    The "I have one!" button on the dashboard posts here with an optional
    customized message. On top of that, the requester automatically gets an
    system message asking "Would you like to borrow it?" with Yes/No buttons -
    see respond_borrow_offer() for what happens next.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))

    message = (request.form.get('message') or '').strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Make sure the item exists and is a requested item.
    cursor.execute('SELECT id, name, owner_id, status FROM items WHERE id = ?', (item_id,))
    item = cursor.fetchone()
    if not item or item['status'] != 'requested':
        conn.close()
        return redirect(url_for('dashboard'))

    if item['owner_id'] == session['user_id']:
        conn.close()
        return redirect(url_for('dashboard'))

    # If a chat request already exists for this user and item, reuse it.
    cursor.execute('''
        SELECT id FROM requests
        WHERE item_id = ? AND borrower_id = ?
    ''', (item_id, session['user_id']))
    existing = cursor.fetchone()
    is_new_request = not existing
    if existing:
        request_id = existing['id']
    else:
        cursor.execute('''
            INSERT INTO requests (item_id, borrower_id, status)
            VALUES (?, ?, 'pending')
        ''', (item_id, session['user_id']))
        request_id = cursor.lastrowid

    if message:
        cursor.execute('''
            INSERT INTO messages (request_id, sender_id, content)
            VALUES (?, ?, ?)
        ''', (request_id, session['user_id'], message))

    if is_new_request:
        cursor.execute('''
            INSERT INTO messages (request_id, sender_id, content, message_type)
            VALUES (?, ?, ?, 'borrow_offer')
        ''', (request_id, session['user_id'],
              '{} has a {}. Would you like to borrow it?'.format(session['username'], item['name'])))

    conn.commit()
    conn.close()

    return redirect(url_for('chat', request_id=request_id))


@app.route('/request/<int:request_id>/respond-offer', methods=['POST'])
def respond_borrow_offer(request_id):
    """The requester answers Yes/No to the automatic "Would you like to borrow it?"
    prompt sent when someone clicks "I have one!" on their public wanted-item post."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, i.owner_id, i.name as item_name
        FROM requests r
        JOIN items i ON r.item_id = i.id
        WHERE r.id = ?
    ''', (request_id,))
    req = cursor.fetchone()

    if not req or req['owner_id'] != session['user_id']:
        conn.close()
        return "Unauthorized", 403

    if req['status'] == 'pending':
        action = request.form.get('action')
        cursor.execute('''
            UPDATE messages SET resolved = 1
            WHERE request_id = ? AND message_type = 'borrow_offer' AND resolved = 0
        ''', (request_id,))

        if action == 'yes':
            cursor.execute('UPDATE requests SET status = ? WHERE id = ?', ('accepted', request_id))
            # The wanted-item post has been fulfilled - stop matching it to other lenders.
            cursor.execute('UPDATE items SET status = ? WHERE id = ?', ('fulfilled', req['item_id']))
            cursor.execute('''
                INSERT INTO messages (request_id, sender_id, content, message_type)
                VALUES (?, ?, ?, 'borrow_accepted')
            ''', (request_id, session['user_id'], "Great, it's confirmed! You can arrange the handover here."))
        elif action == 'no':
            cursor.execute('UPDATE requests SET status = ? WHERE id = ?', ('declined', request_id))
            cursor.execute('''
                INSERT INTO messages (request_id, sender_id, content, message_type)
                VALUES (?, ?, ?, 'borrow_declined')
            ''', (request_id, session['user_id'], "No thanks, not this time."))

        conn.commit()

    conn.close()
    return redirect(url_for('chat', request_id=request_id))


PROFILE_CATEGORIES = [
    'Tools', 'Kitchen', 'Electronics', 'Study & Office', 'Sports & Outdoor',
    'Events & Parties', 'Creative & Hobby', 'Gaming', 'Home & Living',
    'Mobility', 'Baby & Child', 'Pets'
]


@app.route('/request/<int:request_id>/return', methods=['POST'])
def toggle_returned(request_id):
    """Let the borrower flag an item as returned. This doesn't mark it returned right
    away - it sends a confirmation request to the lender in chat, and the item stays
    'pending_confirmation' until the lender replies Yes or No."""
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, i.name as item_name, u.username as borrower_name
        FROM requests r
        JOIN items i ON r.item_id = i.id
        JOIN users u ON r.borrower_id = u.id
        WHERE r.id = ?
    ''', (request_id,))
    req = cursor.fetchone()
    if not req or req['borrower_id'] != session['user_id']:
        conn.close()
        return jsonify({'error': 'unauthorized'}), 403

    data = request.get_json(silent=True) or {}
    if data.get('returned') and req['return_status'] == 'not_returned':
        cursor.execute('UPDATE requests SET return_status = ? WHERE id = ?', ('pending_confirmation', request_id))
        cursor.execute('''
            INSERT INTO messages (request_id, sender_id, content, message_type)
            VALUES (?, ?, ?, 'return_request')
        ''', (request_id, session['user_id'],
              '{} marked "{}" as returned. Did you receive it back?'.format(req['borrower_name'], req['item_name'])))
        conn.commit()

    cursor.execute('SELECT return_status, returned_at FROM requests WHERE id = ?', (request_id,))
    updated = cursor.fetchone()
    conn.close()

    return jsonify({'return_status': updated['return_status'], 'returned_at': updated['returned_at']})


@app.route('/request/<int:request_id>/confirm-return', methods=['POST'])
def confirm_return(request_id):
    """Lender confirms or denies the borrower's return claim, from a button in the chat."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, i.owner_id
        FROM requests r
        JOIN items i ON r.item_id = i.id
        WHERE r.id = ?
    ''', (request_id,))
    req = cursor.fetchone()

    if not req or req['owner_id'] != session['user_id']:
        conn.close()
        return "Unauthorized", 403

    if req['return_status'] == 'pending_confirmation':
        action = request.form.get('action')
        cursor.execute('''
            UPDATE messages SET resolved = 1
            WHERE request_id = ? AND message_type = 'return_request' AND resolved = 0
        ''', (request_id,))

        if action == 'yes':
            returned_at = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('UPDATE requests SET return_status = ?, returned_at = ? WHERE id = ?',
                           ('returned', returned_at, request_id))
            cursor.execute('UPDATE items SET status = ? WHERE id = ?', ('available', req['item_id']))
            cursor.execute('''
                INSERT INTO messages (request_id, sender_id, content, message_type)
                VALUES (?, ?, ?, 'return_confirmed')
            ''', (request_id, session['user_id'], 'Great, the return has been confirmed!'))
        elif action == 'no':
            cursor.execute('UPDATE requests SET return_status = ? WHERE id = ?', ('not_returned', request_id))
            cursor.execute('''
                INSERT INTO messages (request_id, sender_id, content, message_type)
                VALUES (?, ?, ?, 'return_denied')
            ''', (request_id, session['user_id'], "Hey, it looks like you haven't returned this item yet. Please check again."))

        conn.commit()

    conn.close()
    return redirect(url_for('chat', request_id=request_id))


@app.route('/profile')
def profile():
    """Show the user's profile page with owned and borrowed items."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT username, email, location, categories, photo FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    if not user:
        conn.close()
        session.clear()
        return redirect(url_for('login'))

    user_categories = [c.strip() for c in (user['categories'] or '').split(',') if c.strip()]

    cursor.execute('''
        SELECT i.id, i.name, i.photo, i.category, i.description, i.status,
               (SELECT u.username FROM requests r
                JOIN users u ON r.borrower_id = u.id
                WHERE r.item_id = i.id AND r.status = 'accepted' AND r.return_status != 'returned'
                ORDER BY r.created_at DESC LIMIT 1) as borrower_name,
               (SELECT COUNT(*) FROM requests r WHERE r.item_id = i.id) as request_count
        FROM items i
        WHERE i.owner_id = ? AND i.status NOT IN ('requested', 'fulfilled')
    ''', (session['user_id'],))
    my_items = cursor.fetchall()

    cursor.execute('''
        SELECT i.id, i.name, i.photo, i.category, i.description, u.username as owner_name, u.location as owner_location,
               r.id as request_id, r.status, r.return_status, r.returned_at
        FROM requests r
        JOIN items i ON r.item_id = i.id
        JOIN users u ON i.owner_id = u.id
        WHERE r.borrower_id = ? AND r.status = 'accepted'
        ORDER BY r.created_at DESC
    ''', (session['user_id'],))
    borrowed_items = []
    for row in cursor.fetchall():
        item = dict(row)
        item['returned_at_display'] = format_return_date(item['returned_at'])
        borrowed_items.append(item)

    conn.close()

    return render_template('profile.html', user=user, my_items=my_items, borrowed_items=borrowed_items,
                         categories=PROFILE_CATEGORIES, user_categories=user_categories)


@app.route('/profile/edit', methods=['POST'])
def edit_profile():
    """Update the logged-in user's username, email, location and categories."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    username = request.form.get('username')
    email = request.form.get('email')
    location = request.form.get('location')
    categories = request.form.getlist('categories')
    photo_file = request.files.get('photo')

    if not username or not email:
        return redirect(url_for('profile'))

    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM users WHERE username = ? AND id != ?', (username, session['user_id']))
        if cursor.fetchone():
            return redirect(url_for('profile'))

        cursor.execute('SELECT id FROM users WHERE email = ? AND id != ?', (email, session['user_id']))
        if cursor.fetchone():
            return redirect(url_for('profile'))

        if photo_file and photo_file.filename:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{secure_filename(photo_file.filename)}"
            uploads_dir = os.path.join(app.static_folder, 'uploads')
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
            photo_file.save(os.path.join(uploads_dir, filename))
            cursor.execute('UPDATE users SET photo = ? WHERE id = ?', (filename, session['user_id']))

        cursor.execute(
            'UPDATE users SET username = ?, email = ?, location = ?, categories = ? WHERE id = ?',
            (username, email, location, ','.join(categories), session['user_id'])
        )
        conn.commit()
        session['username'] = username
    finally:
        conn.close()

    return redirect(url_for('profile'))


# ==================== ITEM SEARCH ====================

# Below this, a normalized+fuzzy match is considered "close enough" to show.
# Mirrors a Fuse.js threshold of roughly 0.3-0.4 (lower = stricter there),
# just on rapidfuzz's 0-100 similarity scale instead (higher = stricter here).
FUZZY_MATCH_THRESHOLD = 70


def normalize_text(value):
    """Lowercase and drop spaces/hyphens/underscores, so 'Hair Dryer', 'hair-dryer'
    and 'hairdryer' all normalize to the same string and compare equal."""
    return re.sub(r'[\s\-_]+', '', (value or '').lower())


def item_relevance(query, name):
    """0-110 relevance score for ranking search results against a free-typed query.
    Normalized exact/substring matches rank above everything else; anything short
    of that falls back to a fuzzy ratio so small typos still surface a result."""
    query_norm = normalize_text(query)
    name_norm = normalize_text(name)
    if not query_norm or not name_norm:
        return 0
    if query_norm == name_norm:
        return 110
    if query_norm in name_norm:
        return 100
    return fuzz.WRatio(query_norm, name_norm)


@app.route('/search/suggestions')
def search_suggestions():
    """Live type-ahead suggestions for the search bar, as the user types."""
    if 'user_id' not in session:
        return jsonify([])

    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT name FROM items WHERE status = 'available'")
    names = [row['name'] for row in cursor.fetchall()]
    conn.close()

    scored = [(item_relevance(query, name), name) for name in names]
    scored = [s for s in scored if s[0] >= FUZZY_MATCH_THRESHOLD]
    scored.sort(key=lambda s: -s[0])
    suggestions = [name for score, name in scored[:8]]

    return jsonify(suggestions)


@app.route('/search', methods=['GET', 'POST'])
def search():
    """Search for items - queries the database and shows results."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    query = request.args.get('q', '')
    category = request.args.get('category', '')

    # Provide categories for the template to allow quick category selection
    categories = [c['name'] for c in EXPLORE_CATEGORIES]

    if not query and not category:
        return render_template('search.html', items=[], query='', message='Enter an item name to search', categories=categories)

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the user's location (and, if granted, their private device coordinates) for proximity sorting.
    # Coordinates are only ever used server-side to compute a distance for ordering - never sent to
    # other users or exposed in any response.
    cursor.execute('SELECT location, latitude, longitude FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    user_location = user['location'] if user else ''
    user_lat = user['latitude'] if user else None
    user_lon = user['longitude'] if user else None

    # Search for items, optionally narrowed to a category. The name match itself
    # (normalized + fuzzy, tolerant to spacing/case/typos) happens below in Python,
    # since that kind of comparison isn't expressible as a plain SQL LIKE.
    # Never show the viewer their own items - you can't borrow what you already have.
    conditions = ["i.status = 'available'", "i.owner_id != ?"]
    params = [user_lat, user_lon, session['user_id']]
    if category:
        conditions.append('i.category = ?')
        params.append(category)
    params.extend([user_location, f'%{user_location}%'])

    cursor.execute(f'''
        SELECT i.*, u.username as owner, u.location as owner_location,
               distance_km(?, ?, u.latitude, u.longitude) as distance
        FROM items i
        JOIN users u ON i.owner_id = u.id
        WHERE {' AND '.join(conditions)}
        ORDER BY
            CASE WHEN distance IS NULL THEN 1 ELSE 0 END,
            distance,
            CASE WHEN u.location = ? THEN 0
                 WHEN u.location LIKE ? THEN 1
                 ELSE 2 END
    ''', params)

    items = cursor.fetchall()

    if query:
        # Relevance first; Python's sort is stable, so items tied on relevance
        # keep the distance/location order the SQL query already put them in.
        scored = [(item_relevance(query, item['name']), item) for item in items]
        scored = [s for s in scored if s[0] >= FUZZY_MATCH_THRESHOLD]
        scored.sort(key=lambda s: -s[0])
        items = [item for score, item in scored]

    if not items:
        if query:
            # Item doesn't exist, show message to user about requesting it
            cursor.execute("SELECT * FROM items WHERE status = 'requested'")
            candidates = cursor.fetchall()
            scored = [(item_relevance(query, item['name']), item) for item in candidates]
            scored = [s for s in scored if s[0] >= FUZZY_MATCH_THRESHOLD]
            scored.sort(key=lambda s: -s[0])
            requested_items = [item for score, item in scored]
        else:
            requested_items = []

        conn.close()
        if requested_items:
            return render_template('search.html',
                                 items=[],
                                 query=query,
                                 category=category,
                                 message='The requested item is currently unavailable. See pending requests:',
                                 requested_items=requested_items,
                                 show_request_form=True,
                                 categories=categories)
        else:
            return render_template('search.html',
                                 items=[],
                                 query=query,
                                 category=category,
                                 message='No items found in this category yet.' if category else 'The requested item is currently unavailable.',
                                 show_request_form=bool(query),
                                 categories=categories)

    conn.close()
    return render_template('search.html', items=items, query=query, category=category, categories=categories)


@app.route('/request-item', methods=['GET', 'POST'])
def request_item():
    """Request form for items not in database."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    categories_list = [
        'Tools', 'Kitchen', 'Electronics', 'Study & Office', 'Sports & Outdoor',
        'Events & Parties', 'Creative & Hobby', 'Gaming', 'Home & Living',
        'Mobility', 'Baby & Child', 'Pets'
    ]
    
    if request.method == 'POST':
        item_name = request.form.get('item_name')
        categories = request.form.getlist('categories')
        description = request.form.get('description', '')
        photo_file = request.files.get('photo')

        if not item_name or not categories:
            return render_template('request_item.html',
                                 error='Item name and category are required',
                                 categories=categories_list)

        category = ','.join(categories)

        photo = None
        if photo_file and photo_file.filename:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{secure_filename(photo_file.filename)}"
            uploads_dir = os.path.join(app.static_folder, 'uploads')
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
            photo_file.save(os.path.join(uploads_dir, filename))
            photo = filename

        conn = get_db_connection()
        cursor = conn.cursor()

        # Create a "requested" item
        cursor.execute('''
            INSERT INTO items (name, description, owner_id, category, status, photo)
            VALUES (?, ?, ?, ?, 'requested', ?)
        ''', (item_name, description, session['user_id'], category, photo))
        
        # Send notifications to users interested in this category
        cursor.execute('''
            SELECT id FROM users 
            WHERE id != ? AND categories LIKE ?
        ''', (session['user_id'], f'%{category}%'))
        
        interested_users = cursor.fetchall()
        
        # TODO: Create notification system
        # For now, just log that these users should be notified
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('dashboard'))
    
    return render_template('request_item.html', categories=categories_list)


# ==================== BORROWING PROCESS ====================

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    """Show item details and allow borrowing request."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT i.*, u.username as owner, u.location as owner_location,
               (SELECT bu.username FROM requests r
                JOIN users bu ON r.borrower_id = bu.id
                WHERE r.item_id = i.id AND r.status = 'accepted' AND r.return_status != 'returned'
                ORDER BY r.created_at DESC LIMIT 1) as borrower_name
        FROM items i
        JOIN users u ON i.owner_id = u.id
        WHERE i.id = ?
    ''', (item_id,))
    item = cursor.fetchone()
    conn.close()
    
    if not item:
        return "Item not found", 404
    
    return render_template('item_detail.html', item=item)


@app.route('/borrow/<int:item_id>', methods=['POST'])
def borrow_item(item_id):
    """Send a borrow request to the item owner."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if item is available
    cursor.execute('SELECT * FROM items WHERE id = ? AND status = ?', (item_id, 'available'))
    item = cursor.fetchone()

    if not item:
        return "Item not available", 400

    if item['owner_id'] == session['user_id']:
        conn.close()
        return "You can't borrow your own item", 400

    # Create borrow request
    cursor.execute('''
        INSERT INTO requests (item_id, borrower_id, status)
        VALUES (?, ?, 'pending')
    ''', (item_id, session['user_id']))
    request_id = cursor.lastrowid

    # Kick off the chat with an automatic greeting from the borrower
    cursor.execute('''
        INSERT INTO messages (request_id, sender_id, content)
        VALUES (?, ?, ?)
    ''', (request_id, session['user_id'], "Heyy, I requested your Item!\nlet me know :)"))

    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))


@app.route('/request/<int:request_id>/respond', methods=['GET', 'POST'])
def respond_request(request_id):
    """Owner responds to a borrow request (accept/decline).

    The "I have one!" button on the dashboard posts here with no action
    specified, which means accept, plus an optional customized message that
    gets sent to the borrower as the opening chat message.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))

    action = request.form.get('action', 'accept')  # 'accept' or 'decline'
    message = (request.form.get('message') or '').strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the request and verify ownership
    cursor.execute('''
        SELECT r.*, i.owner_id
        FROM requests r
        JOIN items i ON r.item_id = i.id
        WHERE r.id = ?
    ''', (request_id,))
    request_data = cursor.fetchone()

    if not request_data or request_data['owner_id'] != session['user_id']:
        conn.close()
        return "Unauthorized", 403

    if action == 'accept':
        cursor.execute('UPDATE requests SET status = ? WHERE id = ?', ('accepted', request_id))
        cursor.execute('UPDATE items SET status = ? WHERE id = ?', ('borrowed', request_data['item_id']))
        if message:
            cursor.execute('''
                INSERT INTO messages (request_id, sender_id, content)
                VALUES (?, ?, ?)
            ''', (request_id, session['user_id'], message))
    elif action == 'decline':
        cursor.execute('UPDATE requests SET status = ? WHERE id = ?', ('declined', request_id))
        # Suspend the item temporarily
        cursor.execute('UPDATE items SET status = ? WHERE id = ?', ('suspended', request_data['item_id']))
        # Let the requester know automatically
        cursor.execute('''
            INSERT INTO messages (request_id, sender_id, content)
            VALUES (?, ?, ?)
        ''', (request_id, session['user_id'], "Sorry, I can't lend this item right now :("))

    conn.commit()
    conn.close()

    if action == 'decline':
        return redirect(url_for('dashboard'))
    return redirect(url_for('chat', request_id=request_id))


# ==================== CHAT ====================

def format_chat_timestamp(value):
    """Format a stored message timestamp for the chat list preview:
    time (HH:MM) for today, weekday abbreviation for the past week, else a date."""
    if not value:
        return ''
    try:
        ts = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    except (TypeError, ValueError):
        return value

    today = datetime.now().date()
    if ts.date() == today:
        return ts.strftime('%H:%M')
    elif (today - ts.date()).days < 7:
        return ts.strftime('%a').lower()
    else:
        return ts.strftime('%d/%m/%Y')


def format_message_time(value):
    """Format a single message's timestamp for display inside a chat, as HH:MM."""
    if not value:
        return ''
    try:
        ts = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    except (TypeError, ValueError):
        return value
    return ts.strftime('%H:%M')


def format_return_date(value):
    """Format a stored return date (YYYY-MM-DD) as e.g. 'July 5, 2026'."""
    if not value:
        return ''
    try:
        d = datetime.strptime(value, '%Y-%m-%d')
    except (TypeError, ValueError):
        return value
    return '{} {}, {}'.format(d.strftime('%B'), d.day, d.year)


@app.route('/chat')
def chat_index():
    """List the user's chat conversations that have already started (i.e. have at least one message)."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT r.id, i.name as item_name,
               (CASE WHEN i.owner_id = ? THEN u2.username ELSE u1.username END) as other_name,
               (CASE WHEN i.owner_id = ? THEN u2.photo ELSE u1.photo END) as other_photo,
               (SELECT content FROM messages m WHERE m.request_id = r.id ORDER BY m.created_at DESC LIMIT 1) as last_message,
               (SELECT created_at FROM messages m WHERE m.request_id = r.id ORDER BY m.created_at DESC LIMIT 1) as last_message_at,
               (SELECT COUNT(*) FROM messages m WHERE m.request_id = r.id AND m.sender_id != ? AND m.is_read = 0) as unread_count
        FROM requests r
        JOIN items i ON r.item_id = i.id
        JOIN users u1 ON i.owner_id = u1.id
        JOIN users u2 ON r.borrower_id = u2.id
        WHERE (i.owner_id = ? OR r.borrower_id = ?)
          AND EXISTS (SELECT 1 FROM messages m WHERE m.request_id = r.id)
        ORDER BY unread_count > 0 DESC, last_message_at DESC
    ''', (session['user_id'], session['user_id'], session['user_id'], session['user_id'], session['user_id']))
    rows = cursor.fetchall()

    conn.close()

    chats = []
    for row in rows:
        chat = dict(row)
        chat['last_message_at'] = format_chat_timestamp(row['last_message_at'])
        chats.append(chat)

    return render_template('chat_list.html', chats=chats)


@app.route('/chat/<int:request_id>')
def chat(request_id):
    """Chat between borrower and owner for an accepted request."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get request details
    cursor.execute('''
        SELECT r.*, i.name as item_name, i.photo as item_photo, i.description as item_description,
               i.owner_id, i.status as item_status,
               (SELECT username FROM users WHERE id = i.owner_id) as requester_name,
               (SELECT username FROM users WHERE id = r.borrower_id) as borrower_name
        FROM requests r
        JOIN items i ON r.item_id = i.id
        WHERE r.id = ?
    ''', (request_id,))
    request_data = cursor.fetchone()

    # Verify access
    if not request_data or (request_data['owner_id'] != session['user_id'] and
                           request_data['borrower_id'] != session['user_id']):
        conn.close()
        return "Unauthorized", 403

    is_owner = request_data['owner_id'] == session['user_id']
    if is_owner:
        chat_partner = request_data['borrower_name']
    else:
        chat_partner = request_data['requester_name']

    cursor.execute('''
        SELECT m.*, u.username as sender_name
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.request_id = ?
        ORDER BY m.created_at ASC
    ''', (request_id,))
    messages = []
    for row in cursor.fetchall():
        msg = dict(row)
        msg['created_at'] = format_message_time(row['created_at'])
        messages.append(msg)

    conn.close()

    return render_template('chat.html',
                         chat_request=request_data,
                         chat_partner=chat_partner,
                         messages=messages,
                         request_id=request_id,
                         is_owner=is_owner)


@app.route('/chat/<int:request_id>/mark-read', methods=['POST'])
def mark_chat_read(request_id):
    """Mark the other person's messages as read. Called from the client when the
    user leaves the chat screen (not when it's opened), so a message is only
    considered "read" once the user has actually finished looking at the chat."""
    if 'user_id' not in session:
        return '', 401

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, i.owner_id
        FROM requests r
        JOIN items i ON r.item_id = i.id
        WHERE r.id = ?
    ''', (request_id,))
    req = cursor.fetchone()

    if not req or (req['owner_id'] != session['user_id'] and req['borrower_id'] != session['user_id']):
        conn.close()
        return '', 403

    cursor.execute('''
        UPDATE messages SET is_read = 1
        WHERE request_id = ? AND sender_id != ? AND is_read = 0
    ''', (request_id, session['user_id']))
    conn.commit()
    conn.close()

    return '', 204


@app.route('/chat/<int:request_id>/send', methods=['POST'])
def send_message(request_id):
    """Send a message in the chat."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    message = request.form.get('message')
    if not message:
        return redirect(url_for('chat', request_id=request_id))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify access
    cursor.execute('''
        SELECT r.*, i.owner_id
        FROM requests r
        JOIN items i ON r.item_id = i.id
        WHERE r.id = ?
    ''', (request_id,))
    request_data = cursor.fetchone()
    
    if not request_data or (request_data['owner_id'] != session['user_id'] and 
                           request_data['borrower_id'] != session['user_id']):
        conn.close()
        return "Unauthorized", 403
    
    # Insert message
    cursor.execute('''
        INSERT INTO messages (request_id, sender_id, content)
        VALUES (?, ?, ?)
    ''', (request_id, session['user_id'], message))
    conn.commit()
    conn.close()
    
    return redirect(url_for('chat', request_id=request_id))


# ==================== ITEM MANAGEMENT ====================

@app.route('/add-item', methods=['GET', 'POST'])
def add_item():
    """Add a new item to lend."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    categories_list = [
        'Tools', 'Kitchen', 'Electronics', 'Study & Office', 'Sports & Outdoor',
        'Events & Parties', 'Creative & Hobby', 'Gaming', 'Home & Living',
        'Mobility', 'Baby & Child', 'Pets'
    ]
    
    suggested_category = None
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        description = request.form.get('description')
        photo_file = request.files.get('photo')
        
        # Handle photo upload
        photo = None
        if photo_file and photo_file.filename:
            from datetime import datetime as dt
            timestamp = dt.now().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{secure_filename(photo_file.filename)}"
            uploads_dir = os.path.join(app.static_folder, 'uploads')
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
            photo_path = os.path.join(uploads_dir, filename)
            photo_file.save(photo_path)
            photo = filename
        
        if not name or not category:
            return render_template('add_item.html', 
                                 error='Item name and category are required',
                                 categories=categories_list)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if the user already has an item with this same name
        cursor.execute('SELECT category FROM items WHERE name = ? AND owner_id = ?', (name, session['user_id']))
        existing = cursor.fetchone()
        
        if existing and not request.form.get('confirmed'):
            # Item exists, suggest the category
            suggested_category = existing['category']
            conn.close()
            return render_template('add_item.html', 
                                 name=name,
                                 suggested_category=suggested_category,
                                 categories=categories_list,
                                 message=f'This item already exists in our database. We suggest category: {suggested_category}')
        
        # Add the item
        cursor.execute('''
            INSERT INTO items (name, description, owner_id, category, status, photo)
            VALUES (?, ?, ?, ?, 'available', ?)
        ''', (name, description, session['user_id'], category, photo))
        conn.commit()
        conn.close()

        # Return to whichever page the "Add item" popup was opened from (e.g. the
        # dashboard), instead of forcing a jump to the separate items grid page.
        referrer = request.referrer
        if referrer and referrer.startswith(request.host_url):
            return redirect(referrer)
        return redirect(url_for('profile'))

    # GET request - fetch user's items
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT i.id, i.name, i.photo, i.category, i.status,
               (SELECT u.username FROM requests r
                JOIN users u ON r.borrower_id = u.id
                WHERE r.item_id = i.id AND r.status = 'accepted' AND r.return_status != 'returned'
                ORDER BY r.created_at DESC LIMIT 1) as borrower_name
        FROM items i
        WHERE i.owner_id = ? AND i.status NOT IN ('requested', 'fulfilled')
    ''', (session['user_id'],))
    user_items = cursor.fetchall()
    conn.close()
    
    return render_template('add_item.html', categories=categories_list, user_items=user_items)


@app.route('/item/<int:item_id>/delete', methods=['POST'])
def delete_item(item_id):
    """Let an owner delete one of their own items. Blocked if the item has ever
    been requested/borrowed, so we don't orphan another user's chat or history."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT owner_id FROM items WHERE id = ?', (item_id,))
    item = cursor.fetchone()
    if not item or item['owner_id'] != session['user_id']:
        conn.close()
        return "Unauthorized", 403

    cursor.execute('SELECT COUNT(*) as count FROM requests WHERE item_id = ?', (item_id,))
    if cursor.fetchone()['count'] > 0:
        conn.close()
        return "This item has borrow history and can't be deleted", 400

    cursor.execute('DELETE FROM items WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('profile'))


# ==================== NOTIFICATIONS ====================

@app.route('/notifications')
def notifications():
    """Show notifications for category matches."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user's categories of interest
    cursor.execute('SELECT categories FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    user_categories = user['categories'].split(',') if user and user['categories'] else []
    user_categories = [cat.strip() for cat in user_categories]
    
    # Find items matching user's categories (that were recently posted/requested)
    matching_items = []
    for category in user_categories:
        if category:
            cursor.execute('''
                SELECT i.*, u.username as owner
                FROM items i
                JOIN users u ON i.owner_id = u.id
                WHERE i.category = ? AND i.owner_id != ? AND i.status IN ('available', 'requested')
                ORDER BY i.id DESC
            ''', (category, session['user_id']))
            items = cursor.fetchall()
            matching_items.extend(items)
    
    conn.close()
    
    return render_template('notifications.html', items=matching_items)


# Initialize database on startup
if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=8001)
       