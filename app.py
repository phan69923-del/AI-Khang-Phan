import os
import json
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
from google import genai

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "khangphan-secret-key-2026")

# --- CẤU HÌNH GOOGLE OAUTH ---
oauth = OAuth(app)
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

# --- CẤU HÌNH GEMINI API (Sử dụng gemini-3.5-flash-lite) ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
AI_MODEL_NAME = "gemini-3.5-flash-lite"

# --- QUẢN LÝ BỘ NHỚ LOCAL (JSON) ---
MEMORY_DIR = "khangphan_memory"
MEMORY_FILE = os.path.join(MEMORY_DIR, "chat_database.json")

def init_memory():
    if not os.path.exists(MEMORY_DIR):
        os.makedirs(MEMORY_DIR)
    if not os.path.exists(MEMORY_FILE):
        default_data = {"sessions": {}, "histories": {}, "users": {}}
        save_memory_data(default_data)

def load_memory_data():
    init_memory()
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "sessions" not in data: data["sessions"] = {}
            if "histories" not in data: data["histories"] = {}
            if "users" not in data: data["users"] = {}
            return data
    except Exception:
        return {"sessions": {}, "histories": {}, "users": {}}

def save_memory_data(data):
    if not os.path.exists(MEMORY_DIR):
        os.makedirs(MEMORY_DIR)
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- GIAO DIỆN ĐĂNG NHẬP ---
LOGIN_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Đăng Nhập AI - Khang's Workspace</title>
    <style>
        body { background: #0f172a; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: #1e293b; padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); width: 360px; color: #f8fafc; text-align: center; }
        h2 { margin-bottom: 24px; font-weight: 600; color: #ffffff; }
        input { width: 100%; padding: 12px; margin: 10px 0; background: #0f172a; border: 1px solid #334155; border-radius: 6px; color: #fff; box-sizing: border-box; font-size: 14px; }
        input:focus { border-color: #3b82f6; outline: none; }
        .btn-primary { width: 100%; padding: 12px; background: #2563eb; border: none; border-radius: 6px; color: white; font-weight: 600; cursor: pointer; margin-top: 10px; transition: 0.2s; }
        .btn-primary:hover { background: #1d4ed8; }
        .btn-google { background: #ffffff; color: #3c4043; margin-top: 15px; display: flex; align-items: center; justify-content: center; gap: 12px; text-decoration: none; padding: 12px; border-radius: 6px; font-weight: 600; font-size: 14px; border: 1px solid #dadce0; box-shadow: 0 1px 3px rgba(0,0,0,0.08); transition: 0.2s; width: 100%; box-sizing: border-box;}
        .btn-google:hover { background: #f8f9fa; border-color: #dadce0; }
        .error { color: #ef4444; font-size: 13px; margin-bottom: 10px; }
        .switch-link { margin-top: 20px; font-size: 13px; color: #94a3b8; }
        .switch-link a { color: #38bdf8; text-decoration: none; }
        .switch-link a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>Đăng Nhập AI</h2>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Email / Tên đăng nhập" required>
            <input type="password" name="password" placeholder="Mật khẩu" required>
            <button type="submit" class="btn-primary">Đăng Nhập</button>
        </form>
        
        {% if google_enabled %}
        <a href="/login/google" class="btn-google">
            <svg width="18" height="18" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
                <path fill="#EA4335" d="M24 9.5c3.54 0 6.7 1.22 9.19 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
                <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
                <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
                <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.46-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
                <path fill="none" d="M0 0h48v48H0z"/>
            </svg>
            Đăng nhập bằng Google
        </a>
        {% endif %}

        <div class="switch-link">
            Chưa có tài khoản? <a href="/register">Đăng ký ngay</a>
        </div>
    </div>
</body>
</html>
"""

REGISTER_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Đăng Ký Tài Khoản</title>
    <style>
        body { background: #0f172a; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: #1e293b; padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); width: 360px; color: #f8fafc; text-align: center; }
        h2 { margin-bottom: 24px; font-weight: 600; color: #ffffff; }
        input { width: 100%; padding: 12px; margin: 10px 0; background: #0f172a; border: 1px solid #334155; border-radius: 6px; color: #fff; box-sizing: border-box; font-size: 14px; }
        input:focus { border-color: #3b82f6; outline: none; }
        .btn-primary { width: 100%; padding: 12px; background: #10b981; border: none; border-radius: 6px; color: white; font-weight: 600; cursor: pointer; margin-top: 10px; transition: 0.2s; }
        .btn-primary:hover { background: #059669; }
        .error { color: #ef4444; font-size: 13px; margin-bottom: 10px; }
        .switch-link { margin-top: 20px; font-size: 13px; color: #94a3b8; }
        .switch-link a { color: #38bdf8; text-decoration: none; }
        .switch-link a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>Đăng Ký Tài Khoản</h2>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Tên đăng nhập / Email" required>
            <input type="password" name="password" placeholder="Mật khẩu" required>
            <button type="submit" class="btn-primary">Đăng Ký</button>
        </form>
        <div class="switch-link">
            Đã có tài khoản? <a href="/login">Đăng nhập</a>
        </div>
    </div>
</body>
</html>
"""

# --- GIAO DIỆN CHAT AI CHÍNH ---
CHAT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Khang's Workspace - Gemini 3.5 Flash-Lite</title>
    <style>
        body { background: #0f172a; font-family: 'Segoe UI', sans-serif; color: #f8fafc; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        .sidebar { width: 260px; background: #1e293b; border-right: 1px solid #334155; display: flex; flex-direction: column; padding: 20px; }
        .sidebar h3 { color: #38bdf8; margin-top: 0; font-size: 18px; }
        .user-info { margin-top: auto; font-size: 13px; color: #94a3b8; border-top: 1px solid #334155; padding-top: 15px; display: flex; justify-content: space-between; align-items: center; }
        .logout-btn { color: #ef4444; text-decoration: none; font-weight: 600; }
        .main-chat { flex: 1; display: flex; flex-direction: column; background: #0f172a; }
        .chat-header { padding: 15px 25px; background: #1e293b; border-bottom: 1px solid #334155; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
        .chat-messages { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
        .message { max-width: 75%; padding: 12px 16px; border-radius: 8px; line-height: 1.5; font-size: 14px; word-wrap: break-word; }
        .user-msg { background: #2563eb; color: white; align-self: flex-end; }
        .ai-msg { background: #334155; color: #f8fafc; align-self: flex-start; }
        .chat-input-area { padding: 20px; background: #1e293b; border-top: 1px solid #334155; display: flex; gap: 10px; }
        .chat-input-area input { flex: 1; padding: 12px; background: #0f172a; border: 1px solid #334155; border-radius: 6px; color: white; font-size: 14px; }
        .chat-input-area input:focus { border-color: #3b82f6; outline: none; }
        .chat-input-area button { padding: 0 20px; background: #2563eb; border: none; border-radius: 6px; color: white; font-weight: 600; cursor: pointer; transition: 0.2s; }
        .chat-input-area button:hover { background: #1d4ed8; }
        .model-badge { background: #059669; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h3>Workspace của Khang</h3>
        <p style="font-size: 13px; color: #94a3b8;">Trò chuyện thông minh cùng mô hình mới nhất.</p>
        <div class="user-info">
            <span>👤 {{ username }}</span>
            <a href="/logout" class="logout-btn">Đăng xuất</a>
        </div>
    </div>
    
    <div class="main-chat">
        <div class="chat-header">
            <span>Khang's AI Assistant</span>
            <span class="model-badge">Gemini 3.5 Flash-Lite</span>
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="message ai-msg">Chào sếp! Tôi đang sử dụng mô hình **Gemini 3.5 Flash-Lite**. Sếp cần tôi hỗ trợ việc gì nào?</div>
        </div>
        
        <div class="chat-input-area">
            <input type="text" id="userInput" placeholder="Nhập tin nhắn của bạn..." autofocus>
            <button onclick="sendMessage()">Gửi</button>
        </div>
    </div>

    <script>
        const inputField = document.getElementById('userInput');
        inputField.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') sendMessage();
        });

        async function sendMessage() {
            const text = inputField.value.trim();
            if (!text) return;

            const chatContainer = document.getElementById('chatMessages');
            
            // Hiển thị tin nhắn user
            chatContainer.innerHTML += `<div class="message user-msg">${escapeHtml(text)}</div>`;
            inputField.value = '';
            chatContainer.scrollTop = chatContainer.scrollHeight;

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });
                const data = await response.json();
                
                // Hiển thị phản hồi từ AI
                chatContainer.innerHTML += `<div class="message ai-msg">${escapeHtml(data.reply || data.error)}</div>`;
                chatContainer.scrollTop = chatContainer.scrollHeight;
            } catch (err) {
                chatContainer.innerHTML += `<div class="message ai-msg" style="color:#ef4444;">Lỗi kết nối đến máy chủ!</div>`;
            }
        }

        function escapeHtml(text) {
            return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }
    </script>
</body>
</html>
"""

# --- ROUTES XỬ LÝ ĐĂNG NHẬP / ĐĂNG KÝ / AUTH ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        data = load_memory_data()
        users = data.get("users", {})
        
        if username in users and check_password_hash(users[username], password):
            session['user'] = username
            return redirect(url_for('index'))
        else:
            error = "Tên đăng nhập hoặc mật khẩu không chính xác!"
            
    return render_template_string(LOGIN_HTML_TEMPLATE, error=error, google_enabled=bool(GOOGLE_CLIENT_ID))

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        data = load_memory_data()
        if "users" not in data: data["users"] = {}
            
        if username in data["users"]:
            error = "Tài khoản này đã tồn tại!"
        else:
            data["users"][username] = generate_password_hash(password)
            save_memory_data(data)
            session['user'] = username
            return redirect(url_for('index'))
            
    return render_template_string(REGISTER_HTML_TEMPLATE, error=error)

@app.route('/login/google')
def google_login():
    if not GOOGLE_CLIENT_ID:
        return "Google OAuth chưa được cấu hình trên server.", 400
    redirect_uri = url_for('google_auth', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/auth/google')
def google_auth():
    try:
        token = oauth.google.authorize_access_token()
        resp = oauth.google.get('https://www.googleapis.com/oauth2/v2/userinfo')
        user_info = resp.json()
        email = user_info.get('email')
        
        data = load_memory_data()
        if "users" not in data: data["users"] = {}
        
        if email not in data["users"]:
            data["users"][email] = generate_password_hash(os.urandom(16).hex())
            save_memory_data(data)
            
        session['user'] = email
        return redirect(url_for('index'))
    except Exception as e:
        return f"Lỗi xác thực Google: {str(e)}", 400

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# --- TRANG CHỦ & API CHAT GEMINI 3.5 FLASH-LITE ---
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template_string(CHAT_HTML_TEMPLATE, username=session['user'])

@app.route('/api/chat', methods=['POST'])
def api_chat():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    req_data = request.get_json()
    user_message = req_data.get('message', '')
    
    if not client:
        return jsonify({"error": "Gemini API Key chưa được thiết lập trên server."})
    
    try:
        # Gọi trực tiếp model gemini-3.5-flash-lite
        response = client.models.generate_content(
            model=AI_MODEL_NAME,
            contents=user_message
        )
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"error": f"Lỗi gọi AI: {str(e)}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)
