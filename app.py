from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)  # تمكين CORS للاتصال من التطبيق

# إعداد قاعدة البيانات
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ========== تعريف النماذج ==========

# نموذج المستخدم
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

# نموذج المنشور (الجديد)
class Post(db.Model):
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    profession = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_email': self.user_email,
            'title': self.title,
            'content': self.content,
            'category': self.category,
            'phone': self.phone,
            'profession': self.profession,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

# ========== إنشاء الجداول ==========
with app.app_context():
    db.create_all()
    print("✅ تم إنشاء الجداول بنجاح!")

# ========== نقاط الوصول (Routes) ==========

# صفحة البداية
@app.route('/')
def home():
    return jsonify({
        "message": "🚀 خادم قاعدة البيانات يعمل بنجاح!",
        "status": "healthy",
        "database": "connected",
        "timestamp": datetime.utcnow().isoformat()
    })

# ========== نقاط وصول المستخدمين ==========

# جلب جميع المستخدمين
@app.route('/api/users', methods=['GET'])
def get_users():
    try:
        users = User.query.all()
        return jsonify({
            "success": True,
            "count": len(users),
            "users": [user.to_dict() for user in users]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# إضافة مستخدم جديد
@app.route('/api/users', methods=['POST'])
def add_user():
    try:
        data = request.json
        
        # التحقق من البيانات المطلوبة
        if not data.get('name') or not data.get('email'):
            return jsonify({
                "success": False,
                "error": "الاسم والبريد الإلكتروني مطلوبان"
            }), 400
        
        # التحقق من عدم وجود البريد مسبقاً
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({
                "success": False,
                "error": "البريد الإلكتروني مستخدم مسبقاً"
            }), 409
        
        # إنشاء المستخدم
        user = User(
            name=data['name'],
            email=data['email'],
            phone=data.get('phone', '')
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "تم إضافة المستخدم بنجاح",
            "user": user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# البحث في المستخدمين
@app.route('/api/users/search', methods=['GET'])
def search_users():
    try:
        query = request.args.get('q', '')
        
        if not query:
            return jsonify({
                "success": True,
                "count": 0,
                "users": []
            })
        
        # البحث في الأسماء والبريد
        users = User.query.filter(
            (User.name.ilike(f'%{query}%')) | 
            (User.email.ilike(f'%{query}%'))
        ).all()
        
        return jsonify({
            "success": True,
            "count": len(users),
            "users": [user.to_dict() for user in users]
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ========== نقاط وصول المنشورات (الجديدة) ==========

# جلب جميع المنشورات
@app.route('/api/posts', methods=['GET'])
def get_posts():
    try:
        posts = Post.query.order_by(Post.created_at.desc()).all()
        return jsonify({
            "success": True,
            "count": len(posts),
            "posts": [post.to_dict() for post in posts]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# إضافة منشور جديد
@app.route('/api/posts', methods=['POST'])
def add_post():
    try:
        data = request.json
        
        # التحقق من البيانات المطلوبة
        required_fields = ['user_email', 'title', 'content']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "success": False,
                    "error": f"حقل {field} مطلوب"
                }), 400
        
        # إنشاء المنشور
        post = Post(
            user_email=data['user_email'],
            title=data['title'],
            content=data['content'],
            category=data.get('category', ''),
            phone=data.get('phone', ''),
            profession=data.get('profession', '')
        )
        
        db.session.add(post)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "تم نشر المنشور بنجاح",
            "post": post.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# البحث في المنشورات
@app.route('/api/posts/search', methods=['GET', 'POST'])
def search_posts():
    try:
        if request.method == 'POST':
            data = request.json
            query = data.get('query', '')
        else:
            query = request.args.get('q', '')
        
        if not query:
            return jsonify({
                "success": True,
                "count": 0,
                "results": []
            })
        
        # البحث في العنوان والمحتوى والتصنيف
        posts = Post.query.filter(
            (Post.title.ilike(f'%{query}%')) | 
            (Post.content.ilike(f'%{query}%')) |
            (Post.category.ilike(f'%{query}%')) |
            (Post.profession.ilike(f'%{query}%'))
        ).order_by(Post.created_at.desc()).all()
        
        return jsonify({
            "success": True,
            "count": len(posts),
            "results": [post.to_dict() for post in posts]
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# جلب منشورات مستخدم معين
@app.route('/api/posts/user/<email>', methods=['GET'])
def get_user_posts(email):
    try:
        posts = Post.query.filter_by(user_email=email)\
                 .order_by(Post.created_at.desc()).all()
        
        return jsonify({
            "success": True,
            "count": len(posts),
            "posts": [post.to_dict() for post in posts]
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ========== نقاط وخاصة بالتطبيق ==========

# تسجيل الدخول (مبسط)
@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email', '')
        
        if not email:
            return jsonify({"success": False, "error": "البريد مطلوب"}), 400
        
        # البحث عن المستخدم
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # إذا لم يكن موجوداً، ننشئه (تسجيل تلقائي)
            user = User(
                name=email.split('@')[0],
                email=email,
                phone=''
            )
            db.session.add(user)
            db.session.commit()
        
        return jsonify({
            "success": True,
            "user": user.to_dict(),
            "token": f"token_{user.id}"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# التسجيل (مخصص للتطبيق)
@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.json
        
        # التحقق من البيانات
        if not data.get('full_name') or not data.get('email'):
            return jsonify({
                "success": False,
                "error": "الاسم الكامل والبريد مطلوبان"
            }), 400
        
        # التحقق من عدم وجود البريد
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({
                "success": False,
                "error": "البريد مستخدم مسبقاً"
            }), 409
        
        # إنشاء المستخدم
        user = User(
            name=data['full_name'],
            email=data['email'],
            phone=data.get('phone', '')
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "تم إنشاء الحساب بنجاح",
            "user": user.to_dict(),
            "token": f"token_{user.id}"
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# ========== نقطة فحص الصحة ==========
@app.route('/health', methods=['GET'])
def health_check():
    try:
        # محاولة الاتصال بقاعدة البيانات
        user_count = User.query.count()
        post_count = Post.query.count()
        
        return jsonify({
            "database": "connected",
            "server": "Python Flask with Posts API",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "stats": {
                "users_count": user_count,
                "posts_count": post_count
            }
        })
    except Exception as e:
        return jsonify({
            "database": "disconnected",
            "server": "Python Flask",
            "status": "unhealthy",
            "error": str(e)
        }), 500

# ========== تشغيل الخادم ==========
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    app.run(host='0.0.0.0', port=port, debug=True)
