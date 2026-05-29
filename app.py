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
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            location TEXT,
            categories TEXT
        )
    ''')
    
    # Items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            owner_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            status TEXT DEFAULT 'available',
            photo TEXT,
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
    
    # Password reset tokens table
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
                'INSERT INTO users (username, email, password, location, categories) VALUES (?, ?, ?, ?, ?)',
                (username, email, hashed_password, location, categories_str)
            )
            conn.commit()
            return redirect(url_for('login'))
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
        cursor.execute('SELECT id, username, password, email FROM users WHERE username = ? OR email = ?', (username, username))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            # User not found - redirect to registration
            return redirect(url_for('register'))
        
        if check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['login_success'] = True  # Flag to show success message on dashboard
            # Success - redirect to dashboard
            return redirect(url_for('dashboard'))
        else:
            # Password is wrong
            return render_template('login.html', error='The password is wrong. Try again')
    
    return render_template('login.html')


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
                         success_message=success_message,
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
        return render_template('search.html', items=[], query='', message='Enter an item name to search')
    
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
        WHERE i.name LIKE ? AND i.status = 'available'
        ORDER BY 
            CASE WHEN u.location = ? THEN 0
                 WHEN u.location LIKE ? THEN 1
                 ELSE 2 END
    ''', (f'%{query}%', user_location, f'%{user_location}%'))
    
    items = cursor.fetchall()
    
    if not items:
        # Item doesn't exist, show message to user about requesting it
        cursor.execute('''
            SELECT * FROM items WHERE name LIKE ? AND status = 'requested'
        ''', (f'%{query}%',))
        
        requested_items = cursor.fetchall()
        if requested_items:
            conn.close()
            return render_template('search.html', 
                                 items=[], 
                                 query=query,
                                 message='The requested item is currently unavailable. See pending requests:',
                                 requested_items=requested_items,
                                 show_request_form=True)
        else:
            conn.close()
            return render_template('search.html', 
                                 items=[], 
                                 query=query,
                                 message='The requested item is currently unavailable.',
                                 show_request_form=True)
    
    conn.close()
    return render_template('search.html', items=items, query=query)


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
        category = request.form.get('category')
        description = request.form.get('description', '')
        
        if not item_name or not category:
            return render_template('request_item.html', 
                                 error='Item name and category are required',
                                 categories=categories_list)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create a "requested" item
        cursor.execute('''
            INSERT INTO items (name, description, owner_id, category, status)
            VALUES (?, ?, ?, ?, 'requested')
        ''', (item_name, description, session['user_id'], category))
        
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
        photo = request.form.get('photo')  # TODO: Handle file upload
        
        if not name or not category:
            return render_template('add_item.html', 
                                 error='Item name and category are required',
                                 categories=categories_list)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if item with same name already exists
        cursor.execute('SELECT category FROM items WHERE name = ?', (name,))
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
        
        return redirect(url_for('dashboard'))
    
    return render_template('add_item.html', categories=categories_list)


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
    app.run(debug=True, host='127.0.0.1', port=5000)