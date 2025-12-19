from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sqlite3
import hashlib
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # غير هذا في الإنتاج

# قاعدة البيانات
DATABASE = 'database.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # جدول المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            phone TEXT,
            profession TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول المنشورات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            post_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT,
            phone TEXT,
            profession TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

# تهيئة قاعدة البيانات
init_db()

# ========== دوال المساعدة ==========

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token.split()[1], app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = data['user_id']
        except:
            return jsonify({'error': 'Token is invalid'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

# ========== API Authentication ==========

@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        required_fields = ['email', 'password', 'full_name']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # التحقق من عدم تكرار البريد
        cursor.execute("SELECT id FROM users WHERE email = ?", (data['email'],))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Email already exists'}), 400
        
        # إنشاء المستخدم
        hashed_password = hash_password(data['password'])
        cursor.execute('''
            INSERT INTO users (email, password, full_name, phone, profession, username)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['email'],
            hashed_password,
            data['full_name'],
            data.get('phone', ''),
            data.get('profession', ''),
            data.get('username', '')
        ))
        
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        # إنشاء token
        token = jwt.encode({
            'user_id': user_id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'])
        
        return jsonify({
            'success': True,
            'message': 'تم التسجيل بنجاح',
            'token': token,
            'user': {
                'id': user_id,
                'email': data['email'],
                'full_name': data['full_name'],
                'phone': data.get('phone', ''),
                'profession': data.get('profession', '')
            }
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        if 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Email and password are required'}), 400
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE email = ?", (data['email'],))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # التحقق من كلمة المرور
        if not verify_password(data['password'], user[3]):  # العمود 3 هو password
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # إنشاء token
        token = jwt.encode({
            'user_id': user[0],  # العمود 0 هو id
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'])
        
        return jsonify({
            'success': True,
            'message': 'تم تسجيل الدخول بنجاح',
            'token': token,
            'user': {
                'id': user[0],
                'email': user[2],
                'full_name': user[4],
                'phone': user[5],
                'profession': user[6]
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== Posts API ==========

@app.route('/api/posts', methods=['GET'])
def get_posts():
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.*, u.full_name, u.email 
            FROM posts p
            JOIN users u ON p.user_id = u.id
            ORDER BY p.created_at DESC
        ''')
        
        posts = []
        for row in cursor.fetchall():
            posts.append(dict(row))
        
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(posts),
            'posts': posts
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/posts', methods=['POST'])
@token_required
def create_post(current_user):
    try:
        data = request.get_json()
        
        if 'title' not in data or 'content' not in data:
            return jsonify({'error': 'Title and content are required'}), 400
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO posts (user_id, title, content, category, phone, profession)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            current_user,
            data['title'],
            data['content'],
            data.get('category', ''),
            data.get('phone', ''),
            data.get('profession', '')
        ))
        
        conn.commit()
        post_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'تم إنشاء المنشور بنجاح',
            'post_id': post_id
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/posts/search', methods=['GET'])
def search_posts():
    try:
        query = request.args.get('q', '')
        category = request.args.get('category', '')
        
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        sql = '''
            SELECT p.*, u.full_name, u.email 
            FROM posts p
            JOIN users u ON p.user_id = u.id
            WHERE (p.title LIKE ? OR p.content LIKE ? OR p.profession LIKE ?)
        '''
        params = [f'%{query}%', f'%{query}%', f'%{query}%']
        
        if category:
            sql += ' AND p.category = ?'
            params.append(category)
        
        sql += ' ORDER BY p.created_at DESC'
        
        cursor.execute(sql, params)
        
        posts = []
        for row in cursor.fetchall():
            posts.append(dict(row))
        
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(posts),
            'posts': posts
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== User API ==========

@app.route('/api/users/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (current_user,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'full_name': user['full_name'],
                'phone': user['phone'],
                'profession': user['profession'],
                'created_at': user['created_at']
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== Main ==========

@app.route('/')
def home():
    return jsonify({
        "status": "success",
        "message": "🚀 خادم قاعدة البيانات يعمل بنجاح!",
        "version": "2.0",
        "endpoints": {
            "التسجيل": "/api/auth/register (POST)",
            "تسجيل الدخول": "/api/auth/login (POST)",
            "المنشورات": "/api/posts (GET/POST)",
            "بحث المنشورات": "/api/posts/search (GET)",
            "بياناتي": "/api/users/me (GET)"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
