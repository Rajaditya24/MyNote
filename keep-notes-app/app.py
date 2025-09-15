from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import json
import os
import hashlib
import pandas as pd
from datetime import datetime
import uuid

app = Flask(__name__)
CORS(app)

# Ensure required directories exist
os.makedirs('user_data', exist_ok=True)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hashlib.sha256(password.encode()).hexdigest() == hashed

def load_users():
    try:
        if os.path.exists('usersinfo.xlsx'):
            df = pd.read_excel('usersinfo.xlsx')
            return df.to_dict('records')
        return []
    except:
        return []

def save_users(users):
    df = pd.DataFrame(users)
    df.to_excel('usersinfo.xlsx', index=False)

def get_user_notes(username):
    user_folder = f'user_data/{username}'
    if not os.path.exists(user_folder):
        return []
    
    notes = []
    for filename in os.listdir(user_folder):
        if filename.endswith('.json'):
            try:
                with open(f'{user_folder}/{filename}', 'r') as f:
                    note = json.load(f)
                    notes.append(note)
            except:
                continue
    return notes

@app.route('/')
def home():
    with open('index.html', 'r') as f:
        return f.read()

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    favorite_item = data.get('favorite_item')
    
    if not all([username, password, favorite_item]):
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    users = load_users()
    
    # Check if username already exists
    for user in users:
        if user['username'] == username:
            return jsonify({'success': False, 'message': 'Username already exists'})
    
    # Add new user
    new_user = {
        'username': username,
        'password': hash_password(password),
        'favorite_item': favorite_item,
        'created_at': datetime.now().isoformat()
    }
    
    users.append(new_user)
    save_users(users)
    
    # Create user folder
    os.makedirs(f'user_data/{username}', exist_ok=True)
    
    return jsonify({'success': True, 'message': 'Registration successful'})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # Check for admin login
    if username == 'admin' and password == 'admin123':
        users = load_users()
        # Decrypt passwords for admin view
        admin_users = []
        for user in users:
            admin_user = user.copy()
            # For demo purposes, we'll show the hash (in real app, you shouldn't show passwords)
            admin_user['password_hash'] = user['password']
            admin_users.append(admin_user)
        
        return jsonify({
            'success': True, 
            'message': 'Admin login successful',
            'user_type': 'admin',
            'users_data': admin_users
        })
    
    users = load_users()
    
    for user in users:
        if user['username'] == username and verify_password(password, user['password']):
            notes = get_user_notes(username)
            return jsonify({
                'success': True, 
                'message': 'Login successful',
                'user_type': 'user',
                'username': username,
                'notes': notes
            })
    
    return jsonify({'success': False, 'message': 'Invalid credentials'})

@app.route('/create_note', methods=['POST'])
def create_note():
    data = request.json
    username = data.get('username')
    title = data.get('title')
    content = data.get('content')
    note_type = data.get('type', 'text')  # 'text' or 'todo'
    
    if not all([username, title, content]):
        return jsonify({'success': False, 'message': 'Title and content are required'})
    
    user_folder = f'user_data/{username}'
    os.makedirs(user_folder, exist_ok=True)
    
    note = {
        'id': str(uuid.uuid4()),
        'title': title,
        'content': content,
        'type': note_type,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
    
    filename = f'{user_folder}/{note["id"]}.json'
    with open(filename, 'w') as f:
        json.dump(note, f, indent=2)
    
    return jsonify({'success': True, 'message': 'Note created successfully', 'note': note})

@app.route('/delete_note', methods=['DELETE'])
def delete_note():
    data = request.json
    username = data.get('username')
    note_id = data.get('note_id')
    
    if not all([username, note_id]):
        return jsonify({'success': False, 'message': 'Username and note ID are required'})
    
    filename = f'user_data/{username}/{note_id}.json'
    
    try:
        os.remove(filename)
        return jsonify({'success': True, 'message': 'Note deleted successfully'})
    except FileNotFoundError:
        return jsonify({'success': False, 'message': 'Note not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error deleting note'})

@app.route('/get_notes/<username>')
def get_notes(username):
    notes = get_user_notes(username)
    return jsonify({'success': True, 'notes': notes})
