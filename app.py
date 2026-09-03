import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from google import genai  # Dùng SDK Gemini mới nhất
from google.genai import types
import requests

# 1. Khởi tạo App & Config
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.secret_key = os.environ.get("SECRET_KEY", "khangphan_secret_key_cuc_ky_bao_mat")

# 2. Cấu hình Database SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 3. Khởi tạo Gemini Client từ biến môi trường Render
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(150), default="Đoạn chat mới")

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), nullable=False)
    sender = db.Column(db.String(20), nullable=False) 
    content = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()

# --- ROUTES GOOGLE OAUTH ---
@app.route('/login/google')
def login_google():
    redirect_uri = url_for('authorize_google', _external=True, _scheme='https')
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={os.environ.get('GOOGLE_CLIENT_ID', '')}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
    )
    return redirect(google_auth_url)

@app.route('/login/google/authorized')
def authorize_google():
    code = request.args.get('code')
    if not code:
        return "Không nhận được mã xác thực từ Google", 400

    redirect_uri = url_for('authorize_google', _external=True, _scheme='https')
    
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        'code': code,
        'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
        'client_secret': os.environ.get("GOOGLE_CLIENT_SECRET"),
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }
    
    token_response = requests.post(token_url, data=payload)
    token_data = token_response.json()
    
    access_token = token_data.get('access_token')
    if not access_token:
        return f"Lỗi lấy token trực tiếp từ Google: {token_data}", 400

    userinfo_response = requests.get(
        'https://www.googleapis.com/oauth2/v3/userinfo',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    user_info = userinfo_response.json()
    
    email = user_info.get('email')
    if not email:
        return f"Không lấy được email từ Google. Dữ liệu trả về: {user_info}", 400

    username = email.split('@')[0]
    
    user = User.query.filter_by(username=username).first()
    if not user:
        user_id_str = str(user_info.get('sub', 'google_user'))
        dummy_password = generate_password_hash(user_id_str)
        user = User(username=username, password=dummy_password)
        db.session.add(user)
        db.session.commit()

    session['user_id'] = user.id
    session['username'] = username
    return redirect(url_for('index'))

# --- ROUTES AUTHENTICATION THƯỜNG ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return jsonify({'success': True, 'message': 'Đăng nhập thành công!'})
        
        return jsonify({'success': False, 'message': 'Sai tên đăng nhập hoặc mật khẩu!'}), 401
        
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    return login()

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Vui lòng điền đầy đủ thông tin!'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': 'Tài khoản đã tồn tại!'}), 400
        
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Đăng ký thành công! Hãy đăng nhập.'})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

# --- ROUTES QUẢN LÝ CHAT ---
@app.route('/api/chats', methods=['GET', 'POST'])
def manage_chats():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    user_id = session['user_id']
    if request.method == 'GET':
        chats = Chat.query.filter_by(user_id=user_id).order_by(Chat.id.desc()).all()
        return jsonify([{'id': c.id, 'title': c.title} for c in chats])
    elif request.method == 'POST':
        new_chat = Chat(user_id=user_id, title="Đoạn chat mới")
        db.session.add(new_chat)
        db.session.commit()
        return jsonify({'id': new_chat.id, 'title': new_chat.title})

@app.route('/api/chats/<int:chat_id>', methods=['GET', 'PUT', 'DELETE'])
def single_chat(chat_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    chat = Chat.query.filter_by(id=chat_id, user_id=session['user_id']).first_or_404()
    
    if request.method == 'GET':
        messages = Message.query.filter_by(chat_id=chat_id).all()
        return jsonify([{'sender': m.sender, 'content': m.content} for m in messages])
        
    elif request.method == 'PUT':
        data = request.get_json()
        new_title = data.get('title', '').strip()
        if new_title:
            chat.title = new_title
            db.session.commit()
        return jsonify({'success': True})
        
    elif request.method == 'DELETE':
        Message.query.filter_by(chat_id=chat_id).delete()
        db.session.delete(chat)
        db.session.commit()
        return jsonify({'success': True})

# --- ROUTE XỬ LÝ CHAT VỚI AI GEMINI 2.5 FLASH ---
if not user_msg or not chat_id:
        return jsonify({'response': 'Thiếu nội dung hoặc mã đoạn chat!'}), 400

    chat_obj = Chat.query.filter_by(id=chat_id, user_id=session['user_id']).first()
    if not chat_obj:
        return jsonify({'response': 'Không tìm thấy đoạn chat!'}), 404

    try:
        old_messages = Message.query.filter_by(chat_id=chat_id).all()
        
        # Build mảng lịch sử trò chuyện theo chuẩn cấu trúc của Gemini SDK mới
        contents_history = []
        for msg in old_messages:
            role = "user" if msg.sender == "user" else "model"
            contents_history.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg.content)])
            )
            
        # Thêm câu hỏi hiện tại của người dùng vào cuối chuỗi lịch sử
        contents_history.append(
            types.Content(role="user", parts=[types.Part.from_text(text=user_msg)])
        )

        # Cấu hình System Instruction ép AI nhận Khang Phan làm tác giả
        system_prompt = (
            "Bạn là AI_KhangPhan, một trợ lý AI thông minh tuyệt vời do Phan Tăng Hoàng Khang "
            "trực tiếp lập trình và tạo ra. Bạn là trợ lý AI thân thiện tên là AI_KhangPhan. "
            "Khi người dùng hỏi về thông tin của chính họ hoặc thông tin vui vẻ, hãy trả lời tự nhiên bằng tiếng Việt, "
            "không được tự động từ chối bằng tiếng nước ngoài. Cậu ấy học lớp 7 trường THCS Nguyễn Trãi "
            "(P.Long Khánh, Tỉnh Đồng Nai), họ và tên cậu ấy là: Phan Tăng Hoàng Khang. "
            "Tuyệt đối không được nhận mình là của OpenAI hay công ty nào khác. "
            "Nếu ai hỏi ai tạo ra bạn, hãy tự hào trả lời là do Khang Phan tạo ra nhé."
        )

        # Gọi mô hình Gemini 2.5 Flash mới nhất kèm theo toàn bộ lịch sử trò chuyện và System Prompt
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents_history,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7
            )
        )
        bot_reply = response.text

        # Lưu cả tin nhắn user và bot vào database
        db.session.add(Message(chat_id=chat_id, sender='user', content=user_msg))
        db.session.add(Message(chat_id=chat_id, sender='bot', content=bot_reply))
        
        # Xử lý tự động đổi tên tiêu đề đoạn chat
        if chat_obj.title == "Đoạn chat mới":
            keywords = ["người tạo", "ai tạo", "lập trình", "ai viết ra", "tác giả"]
            if any(k in user_msg.lower() for k in keywords):
                chat_obj.title = "Thắc mắc về người tạo ra tôi"
            else:
                chat_obj.title = user_msg[:20] + ("..." if len(user_msg) > 20 else "")

        db.session.commit()
        return jsonify({'response': bot_reply})

    except Exception as e:
        db.session.rollback()
        return jsonify({'response': f"Lỗi hệ thống Gemini AI: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
