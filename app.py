import os
import json
import traceback
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
from google import genai

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "khangphan_secret_key_2026_07062014")

# Khởi tạo client Gemini với API key
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

DB_FILE = "database.json"

# ==============================================================================
# TEMPLATE 1: GIAO DIỆN ĐĂNG NHẬP & ĐĂNG KÝ (LOGIN_HTML_TEMPLATE)
# ==============================================================================
LOGIN_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Đăng nhập / Đăng ký - AI KhangPhan</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #f8fafc;
            padding: 20px;
        }
        .auth-container {
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            width: 100%;
            max-width: 420px;
            padding: 40px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
        }
        .auth-header {
            text-align: center;
            margin-bottom: 30px;
        }
        .auth-header i {
            font-size: 48px;
            color: #38bdf8;
            margin-bottom: 12px;
        }
        .auth-header h2 {
            font-size: 26px;
            font-weight: 700;
            color: #f8fafc;
        }
        .auth-header p {
            color: #94a3b8;
            font-size: 14px;
            margin-top: 6px;
        }
        .tab-buttons {
            display: flex;
            background: rgba(15, 23, 42, 0.6);
            padding: 4px;
            border-radius: 12px;
            margin-bottom: 25px;
        }
        .tab-btn {
            flex: 1;
            padding: 10px;
            border: none;
            background: transparent;
            color: #94a3b8;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .tab-btn.active {
            background: #38bdf8;
            color: #0f172a;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-size: 13px;
            color: #cbd5e1;
            font-weight: 500;
        }
        .input-wrapper {
            position: relative;
        }
        .input-wrapper i {
            position: absolute;
            left: 14px;
            top: 50%;
            transform: translateY(-50%);
            color: #64748b;
        }
        .form-control {
            width: 100%;
            padding: 12px 16px 12px 42px;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid #334155;
            border-radius: 10px;
            color: #fff;
            font-size: 14px;
            outline: none;
            transition: border-color 0.3s;
        }
        .form-control:focus {
            border-color: #38bdf8;
        }
        .submit-btn {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
            border: none;
            border-radius: 10px;
            color: #0f172a;
            font-weight: 700;
            font-size: 15px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            margin-top: 10px;
        }
        .submit-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(56, 189, 248, 0.3);
        }
        .alert-message {
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 13px;
            margin-bottom: 15px;
            display: none;
        }
        .alert-error {
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid #ef4444;
            color: #fca5a5;
        }
        .footer-links {
            margin-top: 25px;
            text-align: center;
            font-size: 12px;
            color: #64748b;
        }
        .footer-links a {
            color: #38bdf8;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="auth-container">
        <div class="auth-header">
            <i class="fa-solid fa-robot"></i>
            <h2>AI KhangPhan</h2>
            <p>Trợ lý trí tuệ nhân tạo thông minh</p>
        </div>

        <div class="tab-buttons">
            <button class="tab-btn active" id="loginTabBtn" onclick="switchTab('login')">Đăng nhập</button>
            <button class="tab-btn" id="registerTabBtn" onclick="switchTab('register')">Đăng ký</button>
        </div>

        <div id="alertBox" class="alert-message alert-error"></div>

        <form id="authForm" onsubmit="handleAuth(event)">
            <div class="form-group">
                <label for="username">Tên tài khoản / Email</label>
                <div class="input-wrapper">
                    <i class="fa-solid fa-user"></i>
                    <input type="text" id="username" class="form-control" placeholder="Nhập tài khoản của bạn" required>
                </div>
            </div>

            <div class="form-group">
                <label for="password">Mật khẩu</label>
                <div class="input-wrapper">
                    <i class="fa-solid fa-lock"></i>
                    <input type="password" id="password" class="form-control" placeholder="Nhập mật khẩu" required>
                </div>
            </div>

            <button type="submit" id="submitBtn" class="submit-btn">Đăng nhập</button>
        </form>

        <div class="footer-links">
            <p><a href="/privacy">Chính sách bảo mật</a> | <a href="/terms">Điều khoản dịch vụ</a></p>
            <p style="margin-top: 8px;">&copy; 2026 AI KhangPhan - Phan Tăng Hoàng Khang</p>
        </div>
    </div>

    <script>
        let currentMode = 'login';

        function switchTab(mode) {
            currentMode = mode;
            const alertBox = document.getElementById('alertBox');
            alertBox.style.display = 'none';

            if (mode === 'login') {
                document.getElementById('loginTabBtn').classList.add('active');
                document.getElementById('registerTabBtn').classList.remove('active');
                document.getElementById('submitBtn').innerText = 'Đăng nhập';
            } else {
                document.getElementById('registerTabBtn').classList.add('active');
                document.getElementById('loginTabBtn').classList.remove('active');
                document.getElementById('submitBtn').innerText = 'Đăng ký tài khoản';
            }
        }

        async function handleAuth(event) {
            event.preventDefault();
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value.trim();
            const alertBox = document.getElementById('alertBox');
            
            alertBox.style.display = 'none';

            const endpoint = currentMode === 'login' ? '/login' : '/register';
            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    window.location.href = data.redirect || '/';
                } else {
                    alertBox.innerText = data.error || 'Có lỗi xảy ra, vui lòng thử lại!';
                    alertBox.style.display = 'block';
                }
            } catch (err) {
                alertBox.innerText = 'Không thể kết nối tới server!';
                alertBox.style.display = 'block';
            }
        }
    </script>
</body>
</html>
"""

# ==============================================================================
# TEMPLATE 2: GIAO DIỆN KHUNG CHAT AI (CHAT_HTML_TEMPLATE)
# ==============================================================================
CHAT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI KhangPhan - Trợ lý Trí tuệ nhân tạo</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', sans-serif; }
        body { display: flex; height: 100vh; background-color: #0f172a; color: #f8fafc; overflow: hidden; }
        
        /* Sidebar */
        .sidebar {
            width: 280px;
            background-color: #1e293b;
            display: flex;
            flex-direction: column;
            border-right: 1px solid #334155;
            transition: all 0.3s ease;
        }
        .sidebar-header {
            padding: 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #334155;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: bold;
            font-size: 18px;
            color: #38bdf8;
        }
        .new-chat-btn {
            margin: 15px;
            padding: 12px;
            background: #38bdf8;
            color: #0f172a;
            border: none;
            border-radius: 10px;
            font-weight: bold;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: 0.2s;
        }
        .new-chat-btn:hover { background: #0284c7; color: #fff; }
        .chat-list { flex: 1; overflow-y: auto; padding: 10px; }
        .chat-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 5px;
            cursor: pointer;
            color: #cbd5e1;
            font-size: 14px;
            transition: background 0.2s;
        }
        .chat-item:hover, .chat-item.active { background: #334155; color: #fff; }
        .chat-item-title {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 180px;
        }
        .delete-btn {
            color: #64748b;
            cursor: pointer;
            opacity: 0;
            transition: opacity 0.2s;
        }
        .chat-item:hover .delete-btn { opacity: 1; }
        .delete-btn:hover { color: #ef4444; }
        
        .user-profile {
            padding: 15px;
            border-top: 1px solid #334155;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 14px;
        }
        .logout-btn { color: #ef4444; text-decoration: none; font-size: 16px; }

        /* Main Chat Area */
        .main-chat { flex: 1; display: flex; flex-direction: column; height: 100vh; background: #0f172a; }
        .chat-header {
            height: 60px;
            border-bottom: 1px solid #334155;
            display: flex;
            align-items: center;
            padding: 0 20px;
            font-size: 16px;
            font-weight: 600;
            color: #e2e8f0;
        }
        .messages-container {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .message {
            display: flex;
            gap: 15px;
            max-width: 80%;
        }
        .message.user { align-self: flex-end; flex-direction: row-reverse; }
        .message.bot { align-self: flex-start; }
        .avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            flex-shrink: 0;
        }
        .user .avatar { background: #0284c7; color: #fff; }
        .bot .avatar { background: #38bdf8; color: #0f172a; }
        .content {
            background: #1e293b;
            padding: 12px 16px;
            border-radius: 12px;
            font-size: 15px;
            line-height: 1.6;
            word-break: break-word;
        }
        .user .content { background: #0284c7; color: #fff; border-bottom-right-radius: 2px; }
        .bot .content { background: #1e293b; border-bottom-left-radius: 2px; border: 1px solid #334155; }
        .content p { margin-bottom: 8px; }
        .content p:last-child { margin-bottom: 0; }

        /* Input Area */
        .input-area {
            padding: 20px;
            border-top: 1px solid #334155;
            background: #0f172a;
        }
        .input-box {
            display: flex;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 8px 12px;
            align-items: center;
        }
        .input-box input {
            flex: 1;
            background: transparent;
            border: none;
            color: #fff;
            padding: 8px;
            font-size: 15px;
            outline: none;
        }
        .send-btn {
            background: #38bdf8;
            border: none;
            color: #0f172a;
            width: 36px;
            height: 36px;
            border-radius: 8px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: 0.2s;
        }
        .send-btn:hover { background: #0284c7; color: #fff; }
    </style>
</head>
<body>
    <!-- Sidebar -->
    <div class="sidebar">
        <div class="sidebar-header">
            <div class="brand">
                <i class="fa-solid fa-robot"></i>
                <span>AI KhangPhan</span>
            </div>
        </div>
        <button class="new-chat-btn" onclick="createNewChat()">
            <i class="fa-solid fa-plus"></i> Cuộc trò chuyện mới
        </button>
        <div class="chat-list" id="chatList"></div>
        <div class="user-profile">
            <span><i class="fa-solid fa-user-circle"></i> {{ session.get('user', 'Khách') }}</span>
            <a href="/logout" class="logout-btn" title="Đăng xuất"><i class="fa-solid fa-right-from-bracket"></i></a>
        </div>
    </div>

    <!-- Main Chat -->
    <div class="main-chat">
        <div class="chat-header" id="currentChatTitle">Cuộc trò chuyện mới</div>
        <div class="messages-container" id="messagesContainer"></div>
        <div class="input-area">
            <div class="input-box">
                <input type="text" id="userInput" placeholder="Gửi tin nhắn cho AI KhangPhan..." onkeydown="if(event.key === 'Enter') sendMessage()">
                <button class="send-btn" onclick="sendMessage()"><i class="fa-solid fa-paper-plane"></i></button>
            </div>
        </div>
    </div>

    <script>
        let sessions = {{ sessions | tojson }};
        let currentChatId = Object.keys(sessions)[0] || 'chat_' + Date.now();

        if (!sessions[currentChatId]) {
            sessions[currentChatId] = { title: "Cuộc trò chuyện mới", messages: [] };
        }

        function renderSidebar() {
            const list = document.getElementById('chatList');
            list.innerHTML = '';
            for (let id in sessions) {
                const item = document.createElement('div');
                item.className = `chat-item ${id === currentChatId ? 'active' : ''}`;
                item.onclick = () => switchChat(id);
                item.innerHTML = `
                    <div class="chat-item-title"><i class="fa-regular fa-message"></i> ${sessions[id].title}</div>
                    <i class="fa-solid fa-trash delete-btn" onclick="event.stopPropagation(); deleteChat('${id}')"></i>
                `;
                list.appendChild(item);
            }
        }

        function renderMessages() {
            const container = document.getElementById('messagesContainer');
            container.innerHTML = '';
            const chat = sessions[currentChatId];
            if (!chat) return;

            document.getElementById('currentChatTitle').innerText = chat.title;

            chat.messages.forEach(msg => {
                const div = document.createElement('div');
                div.className = `message ${msg.role}`;
                const isUser = msg.role === 'user';
                div.innerHTML = `
                    <div class="avatar">${isUser ? 'U' : 'AI'}</div>
                    <div class="content">${isUser ? msg.text : marked.parse(msg.text)}</div>
                `;
                container.appendChild(div);
            });
            container.scrollTop = container.scrollHeight;
        }

        function switchChat(id) {
            currentChatId = id;
            renderSidebar();
            renderMessages();
        }

        async function createNewChat() {
            const newId = 'chat_' + Date.now();
            const res = await fetch('/new_chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_id: newId })
            });
            const data = await res.json();
            if (data.success) {
                sessions = data.sessions;
                currentChatId = newId;
                renderSidebar();
                renderMessages();
            }
        }

        async function deleteChat(id) {
            const res = await fetch('/delete_chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_id: id })
            });
            const data = await res.json();
            if (data.success) {
                sessions = data.sessions;
                currentChatId = Object.keys(sessions)[0] || 'chat_' + Date.now();
                if (!sessions[currentChatId]) {
                    sessions[currentChatId] = { title: "Cuộc trò chuyện mới", messages: [] };
                }
                renderSidebar();
                renderMessages();
            }
        }

        async function sendMessage() {
            const input = document.getElementById('userInput');
            const text = input.value.trim();
            if (!text) return;

            input.value = '';

            // Add to UI immediately
            sessions[currentChatId].messages.push({ role: 'user', text: text });
            renderMessages();

            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ chat_id: currentChatId, message: text })
                });
                const data = await res.json();
                if (data.response) {
                    sessions = data.sessions;
                    renderSidebar();
                    renderMessages();
                }
            } catch (err) {
                console.error(err);
            }
        }

        // Khởi chạy ban đầu
        renderSidebar();
        renderMessages();
    </script>
</body>
</html>
"""

# ==============================================================================
# HÀM XỬ LÝ LƯU TRỮ DỮ LIỆU & SESSION KHÁCH HÀNG
# ==============================================================================
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"users": {}, "sessions": {}}
    return {"users": {}, "sessions": {}}

db_data = load_db()
if "users" not in db_data:
    db_data["users"] = {}
if "sessions" not in db_data:
    db_data["sessions"] = {}

users_db = db_data["users"]
user_sessions_global = db_data["sessions"]
user_histories = {}

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump({"users": users_db, "sessions": user_sessions_global}, f, ensure_ascii=False, indent=4)

def get_current_user_sessions():
    user = session.get('user', 'guest')
    if user not in user_sessions_global:
        user_sessions_global[user] = {}
    return user_sessions_global[user]

def get_current_user_histories():
    user = session.get('user', 'guest')
    if user not in user_histories:
        user_histories[user] = {}
    return user_histories[user]

# Khôi phục lịch sử chat Gemini khi khởi động ứng dụng
for user, user_chats in user_sessions_global.items():
    user_histories[user] = {}
    for chat_id, data in user_chats.items():
        user_histories[user][chat_id] = []
        for msg in data.get("messages", []):
            role = "user" if msg["role"] == "user" else "model"
            user_histories[user][chat_id].append({
                "role": role,
                "parts": [{"text": msg["text"]}]
            })

# ==============================================================================
# ROUTE ĐIỀU HƯỚNG VÀ API BACKEND
# ==============================================================================
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_sessions = get_current_user_sessions()
    if not user_sessions:
        default_id = 'chat_' + str(int(os.urandom(4).hex(), 16))
        user_sessions[default_id] = {
            'title': 'Cuộc trò chuyện mới',
            'messages': []
        }
        save_db()
        
    return render_template_string(CHAT_HTML_TEMPLATE, sessions=user_sessions)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template_string(LOGIN_HTML_TEMPLATE)
    
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Vui lòng nhập đầy đủ thông tin!'}), 400
        
    if username in users_db and users_db[username] == password:
        session['user'] = username
        return jsonify({'success': True, 'redirect': '/'})
    
    return jsonify({'success': False, 'error': 'Tài khoản hoặc mật khẩu không chính xác!'}), 401

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Vui lòng nhập đầy đủ thông tin!'}), 400
        
    if username in users_db:
        return jsonify({'success': False, 'error': 'Tài khoản này đã tồn tại!'}), 400
        
    users_db[username] = password
    save_db()
    
    session['user'] = username
    return jsonify({'success': True, 'redirect': '/'})

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/new_chat', methods=['POST'])
def new_chat():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json() or {}
    chat_id = data.get('chat_id')
    user_sessions = get_current_user_sessions()
    
    if chat_id:
        user_sessions[chat_id] = {
            'title': 'Cuộc trò chuyện mới',
            'messages': []
        }
        save_db()
        
    return jsonify({'success': True, 'sessions': user_sessions})

@app.route('/delete_chat', methods=['POST'])
def delete_chat():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.get_json() or {}
    chat_id = data.get('chat_id')
    user_sessions = get_current_user_sessions()
    
    if chat_id in user_sessions:
        del user_sessions[chat_id]
        save_db()
        
    return jsonify({'success': True, 'sessions': user_sessions})

@app.route('/chat', methods=['POST'])
def chat():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json() or {}
        chat_id = data.get("chat_id")
        user_message = data.get("message")

        if not chat_id or not user_message:
            return jsonify({"error": "Thiếu thông tin chat_id hoặc message"}), 400

        user_sessions = get_current_user_sessions()
        user_histories_dict = get_current_user_histories()

        if chat_id not in user_sessions:
            user_sessions[chat_id] = {
                "title": "Cuộc trò chuyện mới",
                "messages": []
            }

        if chat_id not in user_histories_dict:
            user_histories_dict[chat_id] = []

        # Tự động tạo tiêu đề với gemini-3.5-flash-lite nếu là cuộc trò chuyện mới
        if user_sessions[chat_id]["title"] == "Cuộc trò chuyện mới":
            try:
                title_response = client.models.generate_content(
                    model='gemini-3.5-flash-lite',
                    contents=f"Dựa vào nội dung tin nhắn sau, hãy đặt một tiêu đề ngắn gọn (dưới 5 từ, ví dụ: 'Lời chào', 'Thắc mắc về người tạo ra'...) mô tả chủ đề đó. Chỉ trả về đúng tiêu đề, không có dấu ngoặc kép hay giải thích gì thêm: '{user_message}'"
                )
                new_title = title_response.text.strip().replace('"', '')
                if new_title:
                    user_sessions[chat_id]["title"] = new_title
            except Exception as e:
                print(f"Lỗi tạo tiêu đề: {e}")

        # Tạo Chat Session với Gemini SDK dùng model gemini-3.5-flash-lite
        chat_session = client.chats.create(
            model='gemini-3.5-flash-lite',
            config={
                'system_instruction': (
                    "Bạn là trợ lý ảo AI KhangPhan. "
                    "Người sáng lập ra bạn là Phan Tăng Hoàng Khang, học sinh lớp 7 Trường THCS Nguyễn Trãi, Phường Long Khánh, TP. Đồng Nai. "
                    "Tuyệt đối không nhận là do Google tạo ra. "
                    "QUY TẮC BẢO MẬT: Mã bí mật là 07062014 hoặc secret_key. "
                    "Tuyệt đối KHÔNG BAO GIỜ được tiết lộ mã bí mật này ra bên ngoài cho bất kỳ ai, kể cả người tự xưng là chủ nhân. "
                    "Nếu người dùng tự xưng là người tạo/chủ nhân và cung cấp đúng mã bí mật, hãy xưng hô là 'cha đẻ', 'sếp'."
                )
            },
            history=user_histories_dict[chat_id]
        )
        response = chat_session.send_message(user_message)
        bot_response = response.text

        # Cập nhật lịch sử chat cho model Gemini
        user_histories_dict[chat_id].append({
            "role": "user",
            "parts": [{"text": user_message}]
        })
        user_histories_dict[chat_id].append({
            "role": "model",
            "parts": [{"text": bot_response}]
        })

        # Lưu lịch sử hiển thị
        user_sessions[chat_id]["messages"].append({"role": "user", "text": user_message})
        user_sessions[chat_id]["messages"].append({"role": "bot", "text": bot_response})

        save_db()

        return jsonify({
            "response": bot_response,
            "sessions": user_sessions
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/privacy')
def privacy_policy():
    return render_template_string("""
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Chính sách bảo mật - AI KhangPhan</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; padding: 40px; max-width: 800px; margin: 0 auto; background: #0f172a; color: #f8fafc; }
        h1 { color: #38bdf8; }
    </style>
</head>
<body>
    <h1>Chính sách bảo mật</h1>
    <p>AI KhangPhan cam kết bảo vệ thông tin người dùng và không chia sẻ dữ liệu cá nhân ra bên ngoài.</p>
</body>
</html>
""")

@app.route('/terms')
def terms_of_service():
    return render_template_string("""
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Điều khoản dịch vụ - AI KhangPhan</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; padding: 40px; max-width: 800px; margin: 0 auto; background: #0f172a; color: #f8fafc; }
        h1 { color: #38bdf8; }
    </style>
</head>
<body>
    <h1>Điều khoản dịch vụ</h1>
    <p>Khi sử dụng ứng dụng AI KhangPhan, bạn đồng ý tuân thủ các quy định và điều kiện sử dụng dịch vụ của chúng tôi.</p>
    <p>Ứng dụng được xây dựng phục vụ nhu cầu trải nghiệm cá nhân và học tập.</p>
</body>
</html>
""")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
