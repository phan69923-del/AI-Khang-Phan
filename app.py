import os
import json
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
from google import genai

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "khangphan-secret-key-2026")

# Fix lỗi CSRF / lệch scheme HTTPS khi chạy trên Render proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

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

# --- CẤU HÌNH GEMINI API ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
AI_MODEL_NAME = "gemini-2.5-flash-lite"

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

# --- GIAO DIỆN ĐĂNG NHẬP / ĐĂNG KÝ ---
LOGIN_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI KHANG PHAN - Đăng Nhập</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background-color: #0f172a; 
            color: white; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            height: 100vh; 
            margin: 0; 
        }
        .card { 
            background: #1e293b; 
            padding: 30px; 
            border-radius: 12px; 
            width: 320px; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.4); 
            text-align: center; 
        }
        h2 { margin-bottom: 20px; color: #f8fafc; }
        input { 
            width: 100%; 
            padding: 12px; 
            margin: 8px 0; 
            border-radius: 6px; 
            border: 1px solid #334155; 
            background: #0f172a; 
            color: white; 
            box-sizing: border-box; 
            outline: none;
        }
        input:focus { border-color: #38bdf8; }
        button { 
            width: 100%; 
            padding: 12px; 
            margin-top: 10px; 
            border-radius: 6px; 
            border: none; 
            background: #2563eb; 
            color: white; 
            font-weight: bold; 
            cursor: pointer; 
            transition: 0.2s;
        }
        button:hover { background: #1d4ed8; }
        .btn-google { 
            background: #ea4335; 
            margin-top: 15px; 
            display: block; 
            text-decoration: none; 
            padding: 12px; 
            border-radius: 6px; 
            color: white; 
            font-weight: bold; 
            transition: 0.2s;
        }
        .btn-google:hover { background: #d93025; }
        .toggle { margin-top: 20px; font-size: 14px; color: #94a3b8; cursor: pointer; }
        .toggle span { color: #38bdf8; text-decoration: underline; }
        .error { color: #f87171; font-size: 14px; margin-top: 12px; min-height: 18px; }
    </style>
</head>
<body>

<div class="card">
    <h2 id="form-title">Đăng Nhập AI</h2>
    <input type="text" id="email" placeholder="Email / Tên đăng nhập" autocomplete="off">
    <input type="password" id="password" placeholder="Mật khẩu" onkeypress="handleKeyPress(event)">
    
    <button id="submit-btn" onclick="handleSubmit()">Đăng Nhập</button>
    
    {% if google_enabled %}
    <a href="/login/google" class="btn-google">Đăng nhập bằng Google</a>
    {% endif %}
    
    <div class="error" id="error-msg"></div>

    <div class="toggle" onclick="toggleForm()">
        <span id="toggle-text">Chưa có tài khoản? Đăng ký ngay</span>
    </div>
</div>

<script>
    let isRegister = false;

    function toggleForm() {
        isRegister = !isRegister;
        document.getElementById('form-title').innerText = isRegister ? 'Đăng Ký Tài Khoản' : 'Đăng Nhập AI';
        document.getElementById('submit-btn').innerText = isRegister ? 'Đăng Ký' : 'Đăng Nhập';
        document.getElementById('toggle-text').innerText = isRegister ? 'Đã có tài khoản? Đăng nhập' : 'Chưa có tài khoản? Đăng ký ngay';
        document.getElementById('error-msg').innerText = '';
    }

    function handleKeyPress(e) {
        if (e.key === 'Enter') {
            handleSubmit();
        }
    }

    async function handleSubmit() {
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value.trim();
        const errorMsg = document.getElementById('error-msg');
        
        if (!email || !password) {
            errorMsg.innerText = 'Vui lòng nhập đầy đủ thông tin!';
            return;
        }

        errorMsg.innerText = 'Đang xử lý...';
        const endpoint = isRegister ? '/register' : '/login';

        try {
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, username: email, password })
            });
            const data = await res.json();

            if (res.ok && data.success) {
                window.location.href = data.redirect || '/';
            } else {
                errorMsg.innerText = data.error || data.message || 'Có lỗi xảy ra!';
            }
        } catch (err) {
            errorMsg.innerText = 'Lỗi kết nối máy chủ!';
        }
    }
</script>

</body>
</html>
"""

# --- API XỬ LÝ AUTH ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template_string(LOGIN_HTML_TEMPLATE, google_enabled=bool(GOOGLE_CLIENT_ID))
    
    data = request.get_json() or request.form
    username = data.get('email') or data.get('username')
    password = data.get('password')
    
    db_data = load_memory_data()
    users = db_data.get("users", {})
    
    if username in users and check_password_hash(users[username], password):
        session['user'] = username
        return jsonify({"success": True, "redirect": "/"})
    else:
        return jsonify({"success": False, "error": "Tên đăng nhập hoặc mật khẩu không chính xác!"}), 400

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json() or request.form
    username = data.get('email') or data.get('username')
    password = data.get('password')
    
    db_data = load_memory_data()
    if "users" not in db_data: 
        db_data["users"] = {}
        
    if username in db_data["users"]:
        return jsonify({"success": False, "error": "Tài khoản này đã tồn tại!"}), 400
    
    db_data["users"][username] = generate_password_hash(password)
    save_memory_data(db_data)
    session['user'] = username
    return jsonify({"success": True, "redirect": "/"})

@app.route('/login/google')
def google_login():
    if not GOOGLE_CLIENT_ID:
        return "Google OAuth chưa được cấu hình.", 400
    redirect_uri = url_for('google_auth', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/auth/google')
def google_auth():
    try:
        token = oauth.google.authorize_access_token()
        resp = oauth.google.get('https://www.googleapis.com/oauth2/v2/userinfo')
        user_info = resp.json()
        email = user_info.get('email')
        
        db_data = load_memory_data()
        if "users" not in db_data: db_data["users"] = {}
        
        if email not in db_data["users"]:
            db_data["users"][email] = generate_password_hash(os.urandom(16).hex())
            save_memory_data(db_data)
            
        session['user'] = email
        return redirect(url_for('index'))
    except Exception as e:
        return f"Lỗi xác thực Google: {str(e)}", 400

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# --- TRANG CHỦ & API CHAT ---
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return "<h1>Giao diện Chat của sếp đang ở đây (Dùng file template hoặc gán template chat vào đây)</h1>"

@app.route('/api/chat', methods=['POST'])
def api_chat():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    req_data = request.get_json()
    user_message = req_data.get('message', '')
    
    if not client:
        return jsonify({"error": "Gemini API Key chưa được thiết lập trên server."})
    
    try:
        response = client.models.generate_content(
            model=AI_MODEL_NAME,
            contents=user_message
        )
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"error": f"Lỗi gọi AI: {str(e)}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)
