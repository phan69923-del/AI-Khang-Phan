import os
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, send_from_directory
from google import genai
from authlib.integrations.flask_client import OAuth

import khangphan_memory

app = Flask(__name__)
app.secret_key = '07062014'

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

client = genai.Client(api_key=GEMINI_API_KEY)

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

db = khangphan_memory.load_memory_data()
chat_sessions = db.get("sessions", {})        
server_histories = db.get("histories", {})    

users_db = {"khangphan": "123456"}

# Giao diện Trang chủ / Trải nghiệm thử công khai cho Google Bot và mọi người
LANDING_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI KhangPhan - Trợ lý ảo thông minh</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: #131314; color: #e3e3e3; display: flex; align-items: center; justify-content: center; height: 100vh; padding: 20px; }
        .hero-card { background-color: #1e1f20; padding: 40px; border-radius: 24px; border: 1px solid #2b2c2d; width: 100%; max-width: 550px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        .hero-icon { font-size: 48px; color: #8ab4f8; margin-bottom: 15px; }
        h1 { font-size: 24px; color: #ffffff; margin-bottom: 10px; }
        p { color: #aaa; font-size: 14px; line-height: 1.6; margin-bottom: 30px; }
        .btn-group { display: flex; gap: 12px; justify-content: center; }
        .btn { padding: 12px 24px; border-radius: 12px; font-weight: 600; font-size: 14px; text-decoration: none; cursor: pointer; transition: 0.2s; display: inline-flex; align-items: center; gap: 8px; }
        .btn-primary { background-color: #8ab4f8; color: #131314; }
        .btn-primary:hover { background-color: #a8c7fa; }
        .btn-secondary { background-color: #2b2c2d; color: #fff; border: 1px solid #333; }
        .btn-secondary:hover { background-color: #38393a; }
        .footer-links { margin-top: 30px; font-size: 12px; color: #666; display: flex; justify-content: center; gap: 15px; }
        .footer-links a { color: #888; text-decoration: none; }
        .footer-links a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="hero-card">
        <i class="fa-solid fa-brain hero-icon"></i>
        <h1>Chào mừng đến với AI KhangPhan</h1>
        <p>Hệ thống trợ lý ảo thông minh ứng dụng công nghệ đa mô hình hiện đại, giúp bạn giải đáp thắc mắc, viết code, và xử lý công việc nhanh chóng, bảo mật tuyệt đối.</p>
        
        <div class="btn-group">
            <a href="/login" class="btn btn-primary"><i class="fa-solid fa-rocket"></i> Bắt đầu ngay</a>
            <a href="/privacy" class="btn btn-secondary"><i class="fa-solid fa-shield-halved"></i> Chính sách bảo mật</a>
        </div>

        <div class="footer-links">
            <a href="/privacy">Chính sách bảo mật</a>
            <span>•</span>
            <a href="/terms">Điều khoản sử dụng</a>
        </div>
    </div>
</body>
</html>
"""

PRIVACY_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Chính sách bảo mật - AI KhangPhan</title>
    <style>
        body { background: #131314; color: #e3e3e3; font-family: sans-serif; padding: 40px; line-height: 1.6; max-width: 800px; margin: 0 auto; }
        h1 { color: #8ab4f8; margin-bottom: 20px; }
        p, li { color: #ccc; margin-bottom: 10px; }
        a { color: #8ab4f8; }
    </style>
</head>
<body>
    <h1>Chính sách bảo mật</h1>
    <p>Ứng dụng <strong>AI KhangPhan</strong> tôn trọng và cam kết bảo vệ quyền riêng tư của người dùng.</p>
    <p><strong>1. Thu thập thông tin:</strong> Chúng tôi chỉ sử dụng thông tin cơ bản từ tài khoản Google OAuth (như Email và tên hiển thị) với mục đích duy nhất là xác thực quyền truy cập vào hệ thống trò chuyện.</p>
    <p><strong>2. Sử dụng dữ liệu:</strong> Nội dung các cuộc trò chuyện được xử lý thông qua API Google Gemini để trả về kết quả cho người dùng và không chia sẻ cho bên thứ ba.</p>
    <p><a href="/">← Quay lại trang chủ</a></p>
</body>
</html>
"""

TERMS_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Điều khoản sử dụng - AI KhangPhan</title>
    <style>
        body { background: #131314; color: #e3e3e3; font-family: sans-serif; padding: 40px; line-height: 1.6; max-width: 800px; margin: 0 auto; }
        h1 { color: #8ab4f8; margin-bottom: 20px; }
        p, li { color: #ccc; margin-bottom: 10px; }
        a { color: #8ab4f8; }
    </style>
</head>
<body>
    <h1>Điều khoản sử dụng</h1>
    <p>Khi sử dụng ứng dụng AI KhangPhan, bạn đồng ý tuân thủ các quy định về an toàn thông tin và sử dụng trợ lý ảo vào các mục đích học tập, làm việc hợp pháp.</p>
    <p><a href="/">← Quay lại trang chủ</a></p>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tài khoản - AI KhangPhan</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: #131314; color: #e3e3e3; display: flex; align-items: center; justify-content: center; height: 100vh; }
        .login-card { background-color: #1e1f20; padding: 35px; border-radius: 20px; border: 1px solid #2b2c2d; width: 100%; max-width: 400px; text-align: center; }
        .login-card i.logo-icon { font-size: 36px; color: #8ab4f8; margin-bottom: 10px; }
        .login-card h2 { margin-bottom: 20px; font-size: 20px; color: #ffffff; }
        
        .auth-tabs { display: flex; background: #131314; border-radius: 12px; padding: 4px; margin-bottom: 20px; border: 1px solid #2b2c2d; }
        .tab-btn { flex: 1; background: none; border: none; padding: 10px; color: #888; font-weight: 500; font-size: 14px; cursor: pointer; border-radius: 10px; transition: 0.2s; }
        .tab-btn.active { background: #2b2c2d; color: #fff; }

        .input-group { margin-bottom: 15px; text-align: left; }
        .input-group input { width: 100%; padding: 12px 16px; border-radius: 10px; border: 1px solid #333; background-color: #131314; color: #fff; outline: none; font-size: 14px; }
        .input-group input:focus { border-color: #8ab4f8; }
        
        .submit-btn { width: 100%; padding: 12px; background-color: #8ab4f8; border: none; border-radius: 10px; color: #131314; font-weight: 600; cursor: pointer; transition: 0.2s; margin-top: 5px; font-size: 14px; }
        .submit-btn:hover { background-color: #a8c7fa; }

        .divider { display: flex; align-items: center; text-align: center; margin: 20px 0; color: #666; font-size: 13px; }
        .divider::before, .divider::after { content: ''; flex: 1; border-bottom: 1px solid #2b2c2d; }
        .divider::before { margin-right: 10px; }
        .divider::after { margin-left: 10px; }

        .google-btn { width: 100%; display: flex; align-items: center; justify-content: center; gap: 10px; background-color: #131314; border: 1px solid #333; padding: 11px; border-radius: 10px; color: #fff; font-size: 14px; font-weight: 500; cursor: pointer; transition: background 0.2s; text-decoration: none; }
        .google-btn:hover { background-color: #2b2c2d; }
        .google-btn img { width: 18px; height: 18px; }

        .error-msg { background: rgba(255,107,107,0.1); color: #ff6b6b; font-size: 13px; padding: 8px; border-radius: 8px; margin-bottom: 15px; border: 1px solid rgba(255,107,107,0.2); text-align: left; }
        .success-msg { background: rgba(138,180,248,0.1); color: #8ab4f8; font-size: 13px; padding: 8px; border-radius: 8px; margin-bottom: 15px; border: 1px solid rgba(138,180,248,0.2); text-align: left; }
        .form-section { display: none; }
        .form-section.active { display: block; }
        .back-home { margin-top: 15px; display: block; font-size: 13px; color: #888; text-decoration: none; }
        .back-home:hover { color: #fff; }
    </style>
</head>
<body>
    <div class="login-card">
        <i class="fa-solid fa-brain logo-icon"></i>
        <h2>AI KhangPhan WorkSpace</h2>

        {% if error %}
            <div class="error-msg"><i class="fa-solid fa-circle-exclamation"></i> {{ error }}</div>
        {% endif %}
        {% if success %}
            <div class="success-msg"><i class="fa-solid fa-circle-check"></i> {{ success }}</div>
        {% endif %}

        <div class="auth-tabs">
            <button class="tab-btn active" id="tabLoginBtn" onclick="switchTab('login')">Đăng nhập</button>
            <button class="tab-btn" id="tabRegisterBtn" onclick="switchTab('register')">Đăng ký</button>
        </div>

        <form id="loginForm" class="form-section active" method="POST" action="/login">
            <input type="hidden" name="action" value="login">
            <div class="input-group">
                <input type="text" name="login_identity" placeholder="Tên đăng nhập hoặc Email" required>
            </div>
            <div class="input-group">
                <input type="password" name="password" placeholder="Mật khẩu" required>
            </div>
            <button type="submit" class="submit-btn">Đăng nhập</button>
        </form>

        <form id="registerForm" class="form-section" method="POST" action="/login">
            <input type="hidden" name="action" value="register">
            <div class="input-group">
                <input type="text" name="reg_identity" placeholder="Tên đăng nhập hoặc Email" required>
            </div>
            <div class="input-group">
                <input type="password" name="reg_password" placeholder="Mật khẩu mới" required>
            </div>
            <button type="submit" class="submit-btn">Đăng ký tài khoản</button>
        </form>

        <div class="divider">hoặc</div>

        <a href="/login_google" class="google-btn">
            <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="Google logo">
            Đăng nhập bằng Google
        </a>

        <a href="/" class="back-home">← Về trang chủ giới thiệu</a>
    </div>

    <script>
        function switchTab(tab) {
            const loginBtn = document.getElementById('tabLoginBtn');
            const registerBtn = document.getElementById('tabRegisterBtn');
            const loginForm = document.getElementById('loginForm');
            const registerForm = document.getElementById('registerForm');

            if (tab === 'login') {
                loginBtn.classList.add('active');
                registerBtn.classList.remove('active');
                loginForm.classList.add('active');
                registerForm.classList.remove('active');
            } else {
                registerBtn.classList.add('active');
                loginBtn.classList.remove('active');
                registerForm.classList.add('active');
                loginForm.classList.remove('active');
            }
        }
    </script>
</body>
</html>
"""

HTML_TEMPLATE = """<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><title>AI KhangPhan - Trợ lý ảo thông minh</title><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"><script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script><style>* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; } body { background-color: #131314; color: #e3e3e3; display: flex; height: 100vh; overflow: hidden; } .sidebar { width: 260px; background-color: #1e1f20; border-right: 1px solid #2b2c2d; display: flex; flex-direction: column; justify-content: space-between; height: 100vh; position: fixed; left: 0; top: 0; z-index: 1000; } .sidebar-top { padding: 16px; } .sidebar-logo-container { display: flex; align-items: center; gap: 10px; padding: 8px 4px; margin-bottom: 20px; } .sidebar-logo-container i { font-size: 20px; color: #8ab4f8; } .sidebar-logo-container span { color: #ffffff; font-weight: 600; font-size: 15px; } .new-chat-btn { display: flex; align-items: center; gap: 10px; background-color: #2b2c2d; color: #ffffff; border: none; padding: 12px 16px; border-radius: 30px; width: 100%; cursor: pointer; font-size: 14px; font-weight: 500; } .chat-history { padding: 0 16px; overflow-y: auto; flex: 1; } .history-item { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-radius: 20px; font-size: 14px; color: #cccccc; cursor: pointer; margin-top: 5px; } .history-item:hover, .history-item.active { background-color: #2b2c2d; color: #ffffff; } .history-content { display: flex; align-items: center; gap: 10px; flex: 1; overflow: hidden; } .history-text { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; } .delete-chat-btn { background: none; border: none; color: #888; cursor: pointer; padding: 4px 6px; } .sidebar-footer { padding: 16px; border-top: 1px solid #2b2c2d; font-size: 13px; color: #aaa; } .footer-actions { display: flex; gap: 8px; margin-top: 10px; } .footer-btn { flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px; background-color: #2b2c2d; color: #fff; border: none; padding: 8px; border-radius: 16px; cursor: pointer; font-size: 13px; text-decoration: none; } .main-chat { margin-left: 260px; width: calc(100% - 260px); display: flex; flex-direction: column; height: 100vh; background-color: #131314; } .chat-header { padding: 16px 24px; font-size: 16px; font-weight: 500; color: #c4c7c5; border-bottom: 1px solid #2b2c2d; display: flex; align-items: center; gap: 12px; } .chat-messages { flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 20px; max-width: 900px; width: 100%; margin: 0 auto; } .message { max-width: 85%; line-height: 1.6; font-size: 15px; padding: 12px 18px; border-radius: 16px; word-wrap: break-word; } .message.user { background-color: #2b2c2d; align-self: flex-end; color: #fff; border-bottom-right-radius: 4px; } .message.bot { background-color: #1e1f20; align-self: flex-start; color: #e3e3e3; border: 1px solid #2b2c2d; border-bottom-left-radius: 4px; } .chat-input-container { padding: 20px 24px; } .chat-input-box { max-width: 900px; margin: 0 auto; background-color: #1e1f20; border-radius: 30px; display: flex; align-items: center; padding: 8px 16px; border: 1px solid #333; } .chat-input-box textarea { flex: 1; background: none; border: none; color: #fff; font-size: 15px; resize: none; outline: none; max-height: 120px; padding: 8px 0; } .send-btn { background: none; border: none; color: #8ab4f8; font-size: 18px; cursor: pointer; padding: 8px; }</style></head><body><div class="sidebar" id="sidebar"><div class="sidebar-top"><div class="sidebar-logo-container"><i class="fa-solid fa-brain"></i><span>AI KhangPhan</span></div><button class="new-chat-btn" onclick="startNewChat()"><i class="fa-solid fa-plus"></i> Cuộc trò chuyện mới</button></div><div class="chat-history" id="chatHistory"></div><div class="sidebar-footer"><div>Khang Phan WorkSpace</div><div class="footer-actions"><a href="/logout" class="footer-btn"><i class="fa-solid fa-right-from-bracket"></i> Đăng xuất</a></div></div></div><div class="main-chat" id="mainChat"><div class="chat-header"><span id="chatTitleHeader">AI KhangPhan</span></div><div class="chat-messages" id="chatMessages"><div class="message bot">Chào bạn! Tôi có thể giúp gì cho bạn hôm nay?</div></div><div class="chat-input-container"><div class="chat-input-box"><textarea id="userInput" placeholder="Hỏi AI Khang Phan..." rows="1" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMessage();}"></textarea><button class="send-btn" onclick="sendMessage()"><i class="fa-solid fa-paper-plane"></i></button></div></div></div><script>let chatSessions = {{ sessions | tojson | safe }}; let currentChatId = Object.keys(chatSessions)[0] || ""; if(currentChatId) loadChatSession(currentChatId); renderHistoryList(); function renderHistoryList() { const hc = document.getElementById('chatHistory'); hc.innerHTML = ''; for(let id in chatSessions) { hc.innerHTML += `<div class="history-item ${id===currentChatId?'active':''}" onclick="loadChatSession('${id}')"><div class="history-content"><i class="fa-regular fa-message"></i><span class="history-text">${chatSessions[id].title}</span></div></div>`; } } function loadChatSession(id) { currentChatId=id; document.getElementById('chatTitleHeader').textContent=chatSessions[id].title; const cm=document.getElementById('chatMessages'); cm.innerHTML=''; chatSessions[id].messages.forEach(m=>{ cm.innerHTML += `<div class="message ${m.role}">${m.role==='bot'?marked.parse(m.text):m.text}</div>`; }); cm.scrollTop=cm.scrollHeight; renderHistoryList(); } async function startNewChat() { const newId = 'chat_' + Date.now(); const res = await fetch('/new_chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({chat_id:newId})}); const data = await res.json(); chatSessions=data.sessions; loadChatSession(newId); } async function sendMessage() { const input = document.getElementById('userInput'); const text = input.value.trim(); if(!text) return; const cm = document.getElementById('chatMessages'); cm.innerHTML += `<div class="message user">${text}</div>`; chatSessions[currentChatId].messages.push({role:'user', text:text}); input.value=''; cm.scrollTop=cm.scrollHeight; const res = await fetch('/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:text, chat_id:currentChatId})}); const data = await res.json(); if(data.response) { cm.innerHTML += `<div class="message bot">${marked.parse(data.response)}</div>`; chatSessions=data.sessions; document.getElementById('chatTitleHeader').textContent=chatSessions[currentChatId].title; renderHistoryList(); cm.scrollTop=cm.scrollHeight; } }</script></body></html>
"""

@app.route('/')
def index():
    if session.get('logged_in'):
        return render_template_string(HTML_TEMPLATE, sessions=chat_sessions)
    return render_template_string(LANDING_TEMPLATE)

@app.route('/privacy')
def privacy():
    return render_template_string(PRIVACY_TEMPLATE)

@app.route('/terms')
def terms():
    return render_template_string(TERMS_TEMPLATE)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    success = None
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'register':
            reg_identity = request.form.get('reg_identity', '').strip()
            reg_pass = request.form.get('reg_password', '').strip()
            if reg_identity in users_db:
                error = "Tài khoản đã tồn tại!"
            elif reg_identity and reg_pass:
                users_db[reg_identity] = reg_pass
                success = "Đăng ký thành công!"
            else:
                error = "Vui lòng điền đủ thông tin!"
        else:
            login_identity = request.form.get('login_identity', '').strip()
            password = request.form.get('password', '').strip()
            if login_identity in users_db and users_db[login_identity] == password:
                session['logged_in'] = True
                session['user'] = login_identity
                return redirect('/')
            else:
                error = "Sai thông tin đăng nhập!"
    return render_template_string(LOGIN_TEMPLATE, error=error, success=success)

@app.route('/login_google')
def login_google():
    redirect_uri = url_for('auth_google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/google/callback')
@app.route('/callback')
@app.route('/login/google/authorized')
def auth_google_callback():
    try:
        token = google.authorize_access_token()
        resp = google.get('https://www.googleapis.com/oauth2/v3/userinfo')
        user_info = resp.json()
        session['logged_in'] = True
        session['user'] = user_info.get('email')
    except Exception as e:
        print(f"Lỗi OAuth: {e}")
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/new_chat', methods=['POST'])
def new_chat():
    data = request.get_json() or {}
    chat_id = data.get('chat_id')
    if chat_id:
        chat_sessions[chat_id] = {
            "title": "Cuộc trò chuyện mới",
            "messages": [{"role": "bot", "text": "Chào bạn! Tôi có thể giúp gì cho bạn hôm nay?"}]
        }
        server_histories[chat_id] = []
        khangphan_memory.save_memory_data({"sessions": chat_sessions, "histories": server_histories})
    return jsonify({"sessions": chat_sessions})

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json() or {}
        user_message = data.get('message', '').strip()
        chat_id = data.get('chat_id')
        if not user_message:
            return jsonify({'error': 'Trống'}), 400

        if chat_id in chat_sessions and chat_sessions[chat_id]["title"] == "Cuộc trò chuyện mới":
            chat_sessions[chat_id]["title"] = user_message[:25] + ('...' if len(user_message) > 25 else '')

        if chat_id not in server_histories:
            server_histories[chat_id] = []

        system_prompt = (
            "Bạn là trợ lý ảo AI KhangPhan. "
            "Người đã sáng tạo và lập trình ra bạn là Phan Tăng Hoàng Khang, một học sinh lớp 7 tại Trường THCS Nguyễn Trãi, "
            "Phường Long Khánh, Thành Phố Đồng Nai."
        )

        bot_response = ""
        try:
            chat_session = client.chats.create(model='gemini-3.5-flash-lite', config={'system_instruction': system_prompt}, history=server_histories[chat_id])
            bot_response = chat_session.send_message(user_message).text
        except:
            try:
                chat_session_backup = client.chats.create(model='gemini-3.6-flash', config={'system_instruction': system_prompt}, history=server_histories[chat_id])
                bot_response = chat_session_backup.send_message(user_message).text
            except Exception as e:
                bot_response = f"Lỗi hệ thống: {str(e)}"

        server_histories[chat_id].append({"role": "user", "parts": [{"text": user_message}]})
        server_histories[chat_id].append({"role": "model", "parts": [{"text": bot_response}]})

        if chat_id in chat_sessions:
            chat_sessions[chat_id]["messages"].append({"role": "user", "text": user_message})
            chat_sessions[chat_id]["messages"].append({"role": "bot", "text": bot_response})

        khangphan_memory.save_memory_data({"sessions": chat_sessions, "histories": server_histories})
        return jsonify({'response': bot_response, 'sessions': chat_sessions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route để Google Search Console quét file xác minh HTML
@app.route('/<path:filename>')
def catch_all(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
