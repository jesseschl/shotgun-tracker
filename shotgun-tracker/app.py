import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
import os
from functools import wraps
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-dev-key-change-in-production')
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/shotgun_tracker')

# Initialize database
def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()
    
    # Create tables if they don't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            taken INTEGER DEFAULT 0,
            owed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS failed_login_attempts (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if users already exist to avoid duplicates
    c.execute('SELECT COUNT(*) FROM users')
    user_count = c.fetchone()[0]
    
    if user_count == 0:
        # Insert the 3 users with passwords from environment
        users_data = json.loads(os.environ.get('USERS_JSON', '[]'))
        for user in users_data:
            c.execute('INSERT INTO users (username, password, taken, owed) VALUES (%s, %s, %s, %s)', 
                     (user['username'], user['password'], 0, 0))
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    conn.cursor_factory = RealDictCursor
    return conn

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('app.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        conn = get_db_connection()
        
        # Check if user is locked out (3 failed attempts in last hour)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        c = conn.cursor()
        c.execute(
            'SELECT COUNT(*) as count FROM failed_login_attempts WHERE username = %s AND attempt_time > %s',
            (username, one_hour_ago)
        )
        recent_failures = c.fetchone()
        
        if recent_failures['count'] >= 3:
            conn.close()
            return jsonify({'error': 'Account locked due to too many failed login attempts. Try again in 1 hour.'}), 429
        
        # Check credentials
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = %s AND password = %s', 
                          (username, password))
        user = c.fetchone()
        
        if user:
            # Clear failed attempts on successful login
            c.execute('DELETE FROM failed_login_attempts WHERE username = %s', (username,))
            conn.commit()
            conn.close()
            
            session['user_id'] = user['id']
            session['username'] = user['username']
            return jsonify({'success': True})
        else:
            # Record failed attempt
            c.execute('INSERT INTO failed_login_attempts (username) VALUES (%s)', (username,))
            conn.commit()
            conn.close()
            return jsonify({'error': 'Invalid credentials'}), 401
    
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/users', methods=['GET'])
def get_all_users():
    """Public endpoint - returns all users without authentication"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, username, taken, owed FROM users ORDER BY username')
    users = c.fetchall()
    conn.close()
    return jsonify([dict(user) for user in users])

@app.route('/api/current-user', methods=['GET'])
@login_required
def get_current_user():
    user_id = session.get('user_id')
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, username, taken, owed FROM users WHERE id = %s', (user_id,))
    user = c.fetchone()
    conn.close()
    return jsonify(dict(user) if user else {'error': 'User not found'})

@app.route('/api/users/<int:user_id>/taken', methods=['POST'])
@login_required
def update_taken(user_id):
    # Only allow users to update their own data
    if session.get('user_id') != user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    action = data.get('action')  # 'increment' or 'decrement'
    amount = data.get('amount', 1)
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = c.fetchone()
    
    if user:
        new_taken = user['taken']
        if action == 'increment':
            new_taken += amount
        elif action == 'decrement':
            new_taken = max(0, new_taken - amount)
        
        c.execute('UPDATE users SET taken = %s WHERE id = %s', (new_taken, user_id))
        conn.commit()
        c.execute('SELECT id, username, taken, owed FROM users WHERE id = %s', (user_id,))
        updated_user = c.fetchone()
        conn.close()
        return jsonify(dict(updated_user))
    
    conn.close()
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/users/<int:user_id>/owed', methods=['POST'])
@login_required
def update_owed(user_id):
    # Only allow users to update their own data
    if session.get('user_id') != user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    action = data.get('action')  # 'increment' or 'decrement'
    amount = data.get('amount', 1)
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = c.fetchone()
    
    if user:
        new_owed = user['owed']
        if action == 'increment':
            new_owed += amount
        elif action == 'decrement':
            new_owed = max(0, new_owed - amount)
        
        c.execute('UPDATE users SET owed = %s WHERE id = %s', (new_owed, user_id))
        conn.commit()
        c.execute('SELECT id, username, taken, owed FROM users WHERE id = %s', (user_id,))
        updated_user = c.fetchone()
        conn.close()
        return jsonify(dict(updated_user))
    
    conn.close()
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/users/<int:user_id>/pay-off', methods=['POST'])
@login_required
def pay_off_shot(user_id):
    # Only allow users to update their own data
    if session.get('user_id') != user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    """Decreases owed by 1 and increases taken by 1"""
    data = request.json
    amount = data.get('amount', 1)
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = c.fetchone()
    
    if user:
        new_owed = max(0, user['owed'] - amount)
        new_taken = user['taken'] + amount
        
        c.execute('UPDATE users SET owed = %s, taken = %s WHERE id = %s', 
                    (new_owed, new_taken, user_id))
        conn.commit()
        c.execute('SELECT id, username, taken, owed FROM users WHERE id = %s', (user_id,))
        updated_user = c.fetchone()
        conn.close()
        return jsonify(dict(updated_user))
    
    conn.close()
    return jsonify({'error': 'User not found'}), 404

if __name__ == '__main__':
    init_db()
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=debug_mode, port=port)
