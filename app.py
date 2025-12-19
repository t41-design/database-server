from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    try:
        cursor.execute("INSERT OR IGNORE INTO users (name, email, phone) VALUES (?, ?, ?)",
                      ('أحمد محمد', 'ahmed@example.com', '0501234567'))
        cursor.execute("INSERT OR IGNORE INTO users (name, email, phone) VALUES (?, ?, ?)",
                      ('سارة علي', 'sara@example.com', '0559876543'))
    except:
        pass
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return jsonify({
        "status": "success",
        "message": "🚀 خادم قاعدة البيانات يعمل بنجاح!",
        "endpoints": {
            "جميع المستخدمين": "/api/users (GET)",
            "إضافة مستخدم": "/api/users (POST)",
            "بحث": "/api/users/search?q=اسم (GET)",
            "حذف": "/api/users/1 (DELETE)",
            "التحديث": "/api/users/1 (PUT)"
        }
    })

@app.route('/api/users', methods=['GET'])
def get_users():
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        rows = cursor.fetchall()
        
        users = []
        for row in rows:
            users.append(dict(row))
        
        conn.close()
        
        return jsonify({
            "success": True,
            "count": len(users),
            "users": users
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users', methods=['POST'])
def add_user():
    try:
        data = request.get_json()
        
        if not data or 'name' not in data or 'email' not in data:
            return jsonify({"error": "الاسم والبريد الإلكتروني مطلوبان"}), 400
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE email = ?", (data['email'],))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": "البريد الإلكتروني موجود بالفعل"}), 400
        
        cursor.execute('''
            INSERT INTO users (name, email, phone)
            VALUES (?, ?, ?)
        ''', (data['name'], data['email'], data.get('phone', '')))
        
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "✅ تم إضافة المستخدم بنجاح",
            "id": user_id
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "المستخدم غير موجود"}), 404
        
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "🗑️ تم حذف المستخدم بنجاح"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        data = request.get_json()
        
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "المستخدم غير موجود"}), 404
        
        cursor.execute('''
            UPDATE users 
            SET name = ?, email = ?, phone = ?
            WHERE id = ?
        ''', (data.get('name'), data.get('email'), data.get('phone'), user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "✏️ تم تحديث بيانات المستخدم"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/search', methods=['GET'])
def search_users():
    try:
        query = request.args.get('q', '')
        
        if not query:
            return jsonify({"error": "أدخل كلمة للبحث"}), 400
        
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM users 
            WHERE name LIKE ? OR email LIKE ? OR phone LIKE ?
            ORDER BY name
        ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
        
        rows = cursor.fetchall()
        users = [dict(row) for row in rows]
        
        conn.close()
        
        return jsonify({
            "success": True,
            "count": len(users),
            "users": users
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "users_count": user_count,
            "server": "Python Flask on Render"
        })
    except:
        return jsonify({"status": "unhealthy"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
