# Pietro - Backend Application
# This is the main Flask application that handles all API requests
# → see DECISIONS.md #1 (Flask chosen for simplicity)

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import math

app = Flask(__name__)
app.secret_key = 'pietro-secret-key-change-in-production'  # → see DECISIONS.md #2

# Database configuration
DATABASE = 'pietro.db'


def get_db_connection():
    """Get a database connection. Creates tables if they don't exist."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            location TEXT,
            keywords TEXT
        )
    ''')
    
    # Items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            owner_id INTEGER NOT NULL,
            status TEXT DEFAULT 'available',
            keywords TEXT,
            FOREIGN KEY (owner_id) REFERENCES users (id)
        )
    ''')
    
    # Requests table
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
    
    # Messages table for chat
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
    
    conn.commit()
    conn.close()


# ==================== AUTHENTICATION ====================

@app.route('/')
def index():
    """Home page - redirects to login or dashboard based on session."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page - handles new user creation."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        location = request.form.get('location')
        keywords = request.form.get('keywords', '')
        
        if not username or not password:
            return render_template('register.html', error='Username and password are required')
        
        conn = get_db_connection()
        try:
            # Check if username already exists
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            if cursor.fetchone():
                return render_template('register.html', error='Username already exists')
            
            # Create new user
            hashed_password = generate_password_hash(password)
            cursor.execute(
                'INSERT INTO users (username, password, location, keywords) VALUES (?, ?, ?, ?)',
                (username, hashed_password, location, keywords)
            )
            conn.commit()
            return redirect(url_for('login'))
        except Exception as e:
            return render_template('register.html', error=str(e))
        finally:
            conn.close()
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page - authenticates users."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('register'))
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout - clears session and redirects to login."""
    session.clear()
    return redirect(url_for('login'))


# ==================== DASHBOARD ====================

@app.route('/dashboard')
def dashboard():
    """User's personalized dashboard - shows their items and requests."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user's items
    cursor.execute('SELECT * FROM items WHERE owner_id = ?', (session['user_id'],))
    my_items = cursor.fetchall()
    
    # Get requests for my items
    cursor.execute('''
        SELECT r.id, r.status, r.created_at, i.name as item_name, u.username as borrower
        FROM requests r
        JOIN items i ON r.item_id = i.id
        JOIN users u ON r.borrower_id = u.id
        WHERE i.owner_id = ?
        ORDER BY r.created_at DESC
    ''', (session['user_id'],))
    requests_for_me = cursor.fetchall()
    
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
                         my_items=my_items,
                         requests_for_me=requests_for_me,
                         my_requests=my_requests)


# ==================== ITEM SEARCH ====================

@app.route('/search', methods=['GET', 'POST'])
def search():
    """Search for items - queries the database and shows results."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    query = request.args.get('q', '')
    
    if not query:
        return render_template('search.html', items=[], query='')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user's location for proximity sorting
    cursor.execute('SELECT location FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    user_location = user['location'] if user else ''
    
    # Search for items (case-insensitive)
    cursor.execute('''
        SELECT i.*, u.username as owner, u.location as owner_location
        FROM items i
        JOIN users u ON i.owner_id = u.id
        WHERE (i.name LIKE ? OR i.keywords LIKE ?) AND i.status = 'available'
        ORDER BY 
            CASE WHEN u.location = ? THEN 0
                 WHEN u.location LIKE ? THEN 1
                 ELSE 2 END
    ''', (f'%{query}%', f'%{query}%', user_location, f'%{user_location}%'))
    
    items = cursor.fetchall()
    conn.close()
    
    return render_template('search.html', items=items, query=query)


@app.route('/request-item', methods=['GET', 'POST'])
def request_item():
    """Request form for items not in database."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        item_name = request.form.get('item_name')
        keywords = request.form.get('keywords')
        
        # Store the request in a special table or display on dashboard
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create a placeholder item that shows as "requested"
        cursor.execute('''
            INSERT INTO items (name, description, owner_id, status, keywords)
            VALUES (?, 'REQUESTED ITEM', ?, 'requested', ?)
        ''', (item_name, session['user_id'], keywords))
        conn.commit()
        conn.close()
        
        return redirect(url_for('dashboard'))
    
    return render_template('request_item.html')


# ==================== BORROWING PROCESS ====================

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    """Show item details and allow borrowing request."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT i.*, u.username as owner, u.location as owner_location
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
    
    # Create borrow request
    cursor.execute('''
        INSERT INTO requests (item_id, borrower_id, status)
        VALUES (?, ?, 'pending')
    ''', (item_id, session['user_id']))
    request_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return redirect(url_for('dashboard'))


@app.route('/request/<int:request_id>/respond', methods=['POST'])
def respond_request(request_id):
    """Owner responds to a borrow request (accept/decline)."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    action = request.form.get('action')  # 'accept' or 'decline'
    
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
    elif action == 'decline':
        cursor.execute('UPDATE requests SET status = ? WHERE id = ?', ('declined', request_id))
        # Suspend the item temporarily
        cursor.execute('UPDATE items SET status = ? WHERE id = ?', ('suspended', request_data['item_id']))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for('dashboard'))


# ==================== CHAT ====================

@app.route('/chat/<int:request_id>')
def chat(request_id):
    """Chat between borrower and owner for an accepted request."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get request details
    cursor.execute('''
        SELECT r.*, i.name as item_name, i.owner_id,
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
    
    # Get messages
    cursor.execute('''
        SELECT m.*, u.username as sender_name
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.request_id = ?
        ORDER BY m.created_at ASC
    ''', (request_id,))
    messages = cursor.fetchall()
    
    conn.close()
    
    return render_template('chat.html', 
                         request=request_data,
                         messages=messages,
                         request_id=request_id)


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
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        keywords = request.form.get('keywords', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO items (name, description, owner_id, status, keywords)
            VALUES (?, ?, ?, 'available', ?)
        ''', (name, description, session['user_id'], keywords))
        conn.commit()
        conn.close()
        
        return redirect(url_for('dashboard'))
    
    return render_template('add_item.html')


# ==================== NOTIFICATIONS ====================

@app.route('/notifications')
def notifications():
    """Show notifications for keyword matches."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user's keywords
    cursor.execute('SELECT keywords FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    user_keywords = user['keywords'].split(',') if user and user['keywords'] else []
    
    # Find items matching user's keywords
    matching_items = []
    for keyword in user_keywords:
        keyword = keyword.strip()
        if keyword:
            cursor.execute('''
                SELECT i.*, u.username as owner
                FROM items i
                JOIN users u ON i.owner_id = u.id
                WHERE i.keywords LIKE ? AND i.owner_id != ?
            ''', (f'%{keyword}%', session['user_id']))
            items = cursor.fetchall()
            matching_items.extend(items)
    
    conn.close()
    
    return render_template('notifications.html', items=matching_items)


# Initialize database on startup
if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='127.0.0.1', port=5000)