import base64
import os
import time
import traceback
from authlib.integrations.flask_client import OAuth
from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for
from google import genai
from google.genai import types
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "07062014")

# Tạo thư mục tạm lưu ảnh nếu chưa có
TEMP_UPLOAD_FOLDER = "temp_uploads"
os.makedirs(TEMP_UPLOAD_FOLDER, exist_ok=True)

# Khởi tạo client Gemini API từ biến môi trường
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Cấu hình OAuth cho Google lấy từ biến môi trường
oauth = OAuth(app)
google = oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# ==================== MONGODB CLOUD CONFIG ====================
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://phan6993_db_user:2sZFFaaM95omFUm0@cluster0.wkha2pq.mongodb.net/?appName=Cluster0")

try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client["AI_KhangPhan_DB"]
    sessions_col = db["user_sessions"]
    users_col = db["users"]
    print("✅ Đã kết nối thành công tới MongoDB Cloud!")
except Exception as e:
    print(f"❌ Lỗi kết nối MongoDB Cloud: {e}")

# ==================== HÀM TẢI & LƯU TRỮ TRÊN CLOUD ====================
def load_memory_data():
    """Tải dữ liệu users và sessions từ MongoDB Cloud"""
    users_db = {}
    all_chat_sessions = {}
    
    try:
        # Load users
        for u in users_col.find({}):
            users_db[u["email"]] = u.get("password")
            
        # Load chat sessions
        for doc in sessions_col.find({}):
            user = doc.get("user")
            chat_id = doc.get("chat_id")
            if user not in all_chat_sessions:
                all_chat_sessions[user] = {}
            all_chat_sessions[user][chat_id] = {
                "title": doc.get("title", "Cuộc trò chuyện mới"),
                "messages": doc.get("messages", [])
            }
    except Exception as e:
        print(f"⚠️ Lỗi đọc database từ Cloud: {e}")
        
    return users_db, all_chat_sessions

users_db, all_chat_sessions = load_memory_data()

def save_db():
    """Đồng bộ toàn bộ dữ liệu lên MongoDB Cloud"""
    try:
        # Lưu users
        for email, pwd in users_db.items():
            users_col.update_one({"email": email}, {"$set": {"email": email, "password": pwd}}, upsert=True)
            
        # Lưu sessions
        for user, chats in all_chat_sessions.items():
            for chat_id, data in chats.items():
                sessions_col.update_one(
                    {"user": user, "chat_id": chat_id},
                    {"$set": {"user": user, "chat_id": chat_id, "title": data["title"], "messages": data["messages"]}},
                    upsert=True
                )
    except Exception as e:
        print(f"❌ Lỗi lưu Cloud: {e}")

def get_current_user_sessions():
    user = session.get("user")
    if not user:
        return {}
    if user not in all_chat_sessions:
        all_chat_sessions[user] = {}
    return all_chat_sessions[user]


# ==================== HTML TEMPLATES ====================
LOGIN_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI KHANG PHAN - Đăng Nhập</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); color: white; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: rgba(30, 41, 59, 0.75); backdrop-filter: blur(16px); padding: 30px; border-radius: 16px; width: 340px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); border: 1px solid rgba(255, 255, 255, 0.1); text-align: center; }
        h2 { margin-bottom: 20px; color: #f8fafc; }
        input { width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.15); background: rgba(15, 23, 42, 0.6); color: white; box-sizing: border-box; outline: none; }
        input:focus { border-color: #38bdf8; background: rgba(15, 23, 42, 0.8); }
        button { width: 100%; padding: 12px; margin-top: 10px; border-radius: 8px; border: none; background: #2563eb; color: white; font-weight: bold; cursor: pointer; transition: 0.2s; }
        button:hover { background: #1d4ed8; }
        .google-btn { background-color: rgba(241, 245, 249, 0.9); color: #0f172a; display: flex; align-items: center; justify-content: center; gap: 10px; font-weight: 600; text-decoration: none; margin-top: 12px; padding: 12px; border-radius: 8px; }
        .google-btn:hover { background-color: #ffffff; }
        .divider { margin: 15px 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1); position: relative; }
        .divider span { position: absolute; top: -10px; left: 50%; transform: translateX(-50%); background: #1e293b; padding: 0 10px; font-size: 12px; color: #94a3b8; }
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
    <div class="divider"><span>HOẶC</span></div>
    <a href="/login/google" class="google-btn">
        <svg width="18" height="18" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.46-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>
        Đăng nhập với Google
    </a>
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
    function handleKeyPress(e) { if (e.key === 'Enter') handleSubmit(); }
    async function handleSubmit() {
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value.trim();
        const errorMsg = document.getElementById('error-msg');
        if (!email || !password) { errorMsg.innerText = 'Vui lòng nhập đầy đủ thông tin!'; return; }
        errorMsg.innerText = 'Đang xử lý...';
        const endpoint = isRegister ? '/register' : '/login';
        try {
            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();
            if (res.ok && data.success) { window.location.href = data.redirect || '/'; }
            else { errorMsg.innerText = data.error || 'Có lỗi xảy ra!'; }
        } catch (err) { errorMsg.innerText = 'Lỗi kết nối máy chủ!'; }
    }
</script>
</body>
</html>
"""

CHAT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI KhangPhan</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; background: #0f172a; color: #f8fafc; display: flex; height: 100vh; overflow: hidden; }
        .sidebar { width: 280px; background: #1e293b; display: flex; flexDirection: column; border-right: 1px solid #334155; }
        .sidebar-header { padding: 15px; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; }
        .new-chat-btn { background: #2563eb; color: white; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; font-weight: 600; width: 100%; text-align: center; }
        .new-chat-btn:hover { background: #1d4ed8; }
        .chat-list { flex: 1; overflow-y: auto; padding: 10px; }
        .chat-item { padding: 10px; border-radius: 6px; cursor: pointer; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center; font-size: 14px; color: #cbd5e1; }
        .chat-item:hover { background: #334155; color: white; }
        .chat-item.active { background: #3b82f6; color: white; }
        .delete-chat { background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 14px; }
        .delete-chat:hover { color: #f87171; }
        .main-container { flex: 1; display: flex; flexDirection: column; height: 100%; position: relative; }
        .chat-header { padding: 15px 20px; background: #1e293b; border-bottom: 1px solid #334155; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
        .chat-messages { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; }
        .message { max-width: 75%; padding: 12px 16px; border-radius: 12px; line-height: 1.5; word-wrap: break-word; font-size: 15px; }
        .message.user { background: #2563eb; color: white; align-self: flex-end; border-bottom-right-radius: 2px; }
        .message.bot { background: #334155; color: #f8fafc; align-self: flex-start; border-bottom-left-radius: 2px; }
        .chat-input-area { padding: 15px 20px; background: #1e293b; border-top: 1px solid #334155; display: flex; gap: 10px; align-items: center; }
        .chat-input { flex: 1; background: #0f172a; border: 1px solid #475569; color: white; padding: 12px; border-radius: 8px; outline: none; font-size: 15px; resize: none; height: 24px; }
        .chat-input:focus { border-color: #38bdf8; }
        .action-btn { background: #3b82f6; color: white; border: none; padding: 10px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; }
        .action-btn:hover { background: #2563eb; }
        .logout-btn { color: #f87171; text-decoration: none; font-size: 13px; }
        img.preview-img { max-width: 200px; max-height: 200px; border-radius: 6px; margin-top: 5px; display: block; }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header" style="flex-direction: column; gap: 10px;">
            <button class="new-chat-btn" onclick="createNewChat()">+ Cuộc trò chuyện mới</button>
        </div>
        <div class="chat-list" id="chatList">
            <!-- Render danh sách chat động -->
        </div>
        <div style="padding: 15px; border-top: 1px solid #334155; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 13px; color: #94a3b8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 170px;">{{ session.get('user') }}</span>
            <a href="/logout" class="logout-btn">Đăng xuất</a>
        </div>
    </div>
    <div class="main-container">
        <div class="chat-header" id="chatTitleHeader">Cuộc trò chuyện mới</div>
        <div class="chat-messages" id="chatMessages">
            <div class="message bot">Xin chào! Tôi là trợ lý ảo AI KhangPhan. Tôi có thể giúp gì cho bạn hôm nay?</div>
        </div>
        <div class="chat-input-area">
            <input type="file" id="imageInput" accept="image/*" style="display: none;" onchange="handleImageSelect(event)">
            <button class="action-btn" onclick="document.getElementById('imageInput').click()" title="Đính kèm ảnh">📷</button>
            <textarea class="chat-input" id="userInput" placeholder="Nhắn tin cho AI KhangPhan..." rows="1" onkeypress="handleKeyPress(event)"></textarea>
            <button class="action-btn" onclick="sendMessage()">Gửi</button>
        </div>
    </div>

    <script>
        let chatSessions = {{ sessions | tojson }};
        let currentChatId = Object.keys(chatSessions)[0] || 'chat_' + Date.now();
        let selectedImageBase64 = null;

        if (Object.keys(chatSessions).length === 0) {
            chatSessions[currentChatId] = { title: "Cuộc trò chuyện mới", messages: [] };
        }

        function renderHistoryList() {
            const chatList = document.getElementById('chatList');
            chatList.innerHTML = '';
            for (const [id, data] of Object.entries(chatSessions)) {
                const item = document.createElement('div');
                item.className = `chat-item ${id === currentChatId ? 'active' : ''}`;
                item.innerHTML = `
                    <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1;" onclick="switchChat('${id}')">${data.title}</span>
                    <button class="delete-chat" onclick="deleteChat(event, '${id}')">×</button>
                `;
                chatList.appendChild(item);
            }
        }

        function renderMessages() {
            const chatMessages = document.getElementById('chatMessages');
            chatMessages.innerHTML = '';
            const messages = chatSessions[currentChatId].messages || [];
            if (messages.length === 0) {
                chatMessages.innerHTML = `<div class="message bot">Xin chào! Tôi là trợ lý ảo AI KhangPhan. Tôi có thể giúp gì cho bạn hôm nay?</div>`;
                return;
            }
            messages.forEach(msg => {
                const div = document.createElement('div');
                div.className = `message ${msg.role === 'user' ? 'user' : 'bot'}`;
                let contentHtml = "";
                if (msg.image) {
                    contentHtml += `<img src="${msg.image}" class="preview-img">`;
                }
                if (msg.text) {
                    contentHtml += msg.role === 'bot' ? marked.parse(msg.text) : `<div>${msg.text}</div>`;
                }
                div.innerHTML = contentHtml;
                chatMessages.appendChild(div);
            });
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function switchChat(id) {
            currentChatId = id;
            document.getElementById('chatTitleHeader').textContent = chatSessions[id].title;
            renderHistoryList();
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
                chatSessions = data.sessions;
                switchChat(newId);
            }
        }

        async function deleteChat(event, id) {
            event.stopPropagation();
            const res = await fetch('/delete_chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_id: id })
            });
            const data = await res.json();
            if (data.success) {
                chatSessions = data.sessions;
                const keys = Object.keys(chatSessions);
                if (keys.length > 0) {
                    switchChat(keys[0]);
                } else {
                    createNewChat();
                }
            }
        }

        function handleImageSelect(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    selectedImageBase64 = e.target.result;
                    alert("Đã đính kèm ảnh thành công! Hãy nhập nội dung và bấm Gửi.");
                };
                reader.readAsDataURL(file);
            }
        }

        function handleKeyPress(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        }

        async function sendMessage() {
            const input = document.getElementById('userInput');
            const text = input.value.trim();
            if (!text && !selectedImageBase64) return;

            const payloadText = text;
            const payloadImage = selectedImageBase64;

            input.value = '';
            selectedImageBase64 = null;
            document.getElementById('imageInput').value = '';

            const chatMessages = document.getElementById('chatMessages');
            
            # Append user message ui
            const userMsg = document.createElement('div');
            userMsg.className = 'message user';
            let userHtml = '';
            if (payloadImage) userHtml += `<img src="${payloadImage}" class="preview-img">`;
            if (payloadText) userHtml += `<div>${payloadText}</div>`;
            userMsg.innerHTML = userHtml;
            chatMessages.appendChild(userMsg);

            # Append bot loading ui
            const botMsg = document.createElement('div');
            botMsg.className = 'message bot';
            botMsg.innerHTML = "Đang suy nghĩ... 💭";
            chatMessages.appendChild(botMsg);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: payloadText, chat_id: currentChatId, image: payloadImage })
                });
                const data = await response.json();

                if (response.ok && data.response) {
                    let finalOutput = "";
                    if (data.searched && data.queries && data.queries.length > 0) {
                        finalOutput += `<div style="font-size: 12px; color: #8ab4f8; margin-bottom: 6px; border-left: 2px solid #8ab4f8; padding-left: 6px;">🌐 Đã tìm kiếm: ${data.queries.join(', ')}</div>`;
                    }
                    finalOutput += marked.parse(data.response);

                    botMsg.innerHTML = finalOutput;
                    chatSessions = data.sessions;
                    document.getElementById('chatTitleHeader').textContent = chatSessions[currentChatId].title;
                    renderHistoryList();
                } else {
                    botMsg.textContent = data.error || "Lỗi hệ thống!";
                }
            } catch (e) {
                botMsg.textContent = "Lỗi kết nối máy chủ!";
            }
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        renderHistoryList();
        renderMessages();
    </script>
</body>
</html>
"""


# ==================== FLASK ROUTES ====================

@app.route("/")
def index():
    if "user" not in session:
        return render_template_string(LOGIN_HTML_TEMPLATE)
    user_sessions = get_current_user_sessions()
    return render_template_string(CHAT_HTML_TEMPLATE, sessions=user_sessions)


@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"success": False, "error": "Vui lòng điền đủ thông tin!"}), 400
    if email in users_db and users_db[email] == password:
        session["user"] = email
        return jsonify({"success": True, "redirect": "/"})
    return jsonify({"success": False, "error": "Email hoặc mật khẩu không đúng!"}), 401


@app.route("/register", methods=["POST"])
def register():
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"success": False, "error": "Vui lòng điền đủ thông tin!"}), 400
    if email in users_db:
        return jsonify({"success": False, "error": "Tài khoản đã tồn tại!"}), 400
    users_db[email] = password
    save_db()
    session["user"] = email
    return jsonify({"success": True, "redirect": "/"})


@app.route("/login/google")
def google_login():
    redirect_uri = url_for("google_authorize", _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route("/login/google/authorize")
def google_authorize():
    token = google.authorize_access_token()
    resp = google.get("https://www.googleapis.com/oauth2/v1/userinfo")
    user_info = resp.json()
    email = user_info.get("email")
    if email:
        if email not in users_db:
            users_db[email] = "GOOGLE_OAUTH_USER"
            save_db()
        session["user"] = email
        return redirect(url_for("index"))
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/new_chat", methods=["POST"])
def new_chat():
    user_sessions = get_current_user_sessions()
    data = request.json or {}
    chat_id = data.get("chat_id")
    if chat_id:
        user_sessions[chat_id] = {"title": "Cuộc trò chuyện mới", "messages": []}
        save_db()
    return jsonify({"success": True, "sessions": user_sessions})


@app.route("/delete_chat", methods=["POST"])
def delete_chat_route():
    user_sessions = get_current_user_sessions()
    data = request.json or {}
    chat_id = data.get("chat_id")
    if chat_id in user_sessions:
        del user_sessions[chat_id]
        save_db()
    return jsonify({"success": True, "sessions": user_sessions})


@app.route("/chat", methods=["POST"])
def chat():
    temp_file_path = None
    try:
        user = session.get("user")
        if not user:
            return jsonify({"error": "Chưa đăng nhập"}), 401

        data = request.json or {}
        chat_id = data.get("chat_id")
        user_message = data.get("message")
        image_data = data.get("image")

        if not chat_id or (not user_message and not image_data):
            return jsonify({"error": "Thiếu thông tin tin nhắn hoặc hình ảnh"}), 400

        user_sessions = get_current_user_sessions()
        if chat_id not in user_sessions:
            user_sessions[chat_id] = {"title": "Cuộc trò chuyện mới", "messages": []}

        gemini_contents = []
        for msg in user_sessions[chat_id]["messages"]:
            role = "user" if msg["role"] == "user" else "model"
            content_parts = []
            
            if "image" in msg and msg["image"]:
                try:
                    if msg["image"].startswith("data:image"):
                        header, encoded = msg["image"].split(",", 1)
                        mime_type = header.split(";")[0].split(":")[1]
                        image_bytes = base64.b64decode(encoded)
                        content_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
                except Exception:
                    pass

            if "text" in msg and msg["text"]:
                content_parts.append(types.Part.from_text(text=msg["text"]))
            
            if content_parts:
                gemini_contents.append(types.Content(role=role, parts=content_parts))

        current_new_parts = []
        
        if image_data:
            try:
                header, encoded = image_data.split(",", 1)
                mime_type = header.split(";")[0].split(":")[1]
                image_bytes = base64.b64decode(encoded)
                
                file_ext = mime_type.split("/")[-1]
                if file_ext not in ["png", "jpeg", "jpg", "webp"]:
                    file_ext = "jpg"
                
                temp_filename = f"img_{int(time.time() * 1000)}.{file_ext}"
                temp_file_path = os.path.join(TEMP_UPLOAD_FOLDER, temp_filename)
                
                with open(temp_file_path, "wb") as f:
                    f.write(image_bytes)
                
                current_new_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
            except Exception as e:
                print(f"Lỗi xử lý ảnh tạm: {e}")

        if user_message:
            current_new_parts.append(types.Part.from_text(text=user_message))
        else:
            current_new_parts.append(types.Part.from_text(text="Hãy mô tả hoặc phân tích bức ảnh này giúp tôi."))
        
        gemini_contents.append(types.Content(role="user", parts=current_new_parts))

        # ====== TỰ ĐỘNG SINH TIÊU ĐỀ (CÓ DỰ PHÒNG FALLBACK 3.6 / 3.5) ======
        if user_sessions[chat_id]["title"] == "Cuộc trò chuyện mới":
            try:
                title_prompt = user_message if user_message else "Phân tích hình ảnh"
                title_response = None
                
                try:
                    title_response = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=(
                            f"Nhiệm vụ duy nhất: Đặt tiêu đề tối đa 5 từ cho nội dung: '{title_prompt}'. "
                            "CHỈ TRẢ VỀ ĐÚNG TỪ KHÓA TIÊU ĐỀ, tuyệt đối không viết thêm bất kỳ câu dẫn dắt, giải thích hay dấu sao nào."
                        ),
                    )
                except Exception as e_title_429:
                    print(f"⚠️ gemini-3.6-flash bị lỗi/hết lượt đặt tiêu đề, tự động chuyển sang 3.5-flash-lite... Chi tiết: {e_title_429}")
                    title_response = client.models.generate_content(
                        model="gemini-3.5-flash-lite",
                        contents=(
                            f"Nhiệm vụ duy nhất: Đặt tiêu đề tối đa 5 từ cho nội dung: '{title_prompt}'. "
                            "CHỈ TRẢ VỀ ĐÚNG TỪ KHÓA TIÊU ĐỀ, tuyệt đối không viết thêm bất kỳ câu dẫn dắt, giải thích hay dấu sao nào."
                        ),
                    )

                if title_response and title_response.text:
                    new_title = title_response.text.strip().replace('"', "").replace('*', "").replace('#', "")
                    if new_title:
                        words = new_title.split()
                        if len(words) > 6:
                            new_title = " ".join(words[:5])
                        user_sessions[chat_id]["title"] = new_title
            except Exception as e:
                print(f"Lỗi tạo tiêu đề (cả 2 model đều không chạy được): {e}")
                user_sessions[chat_id]["title"] = "Cuộc trò chuyện mới (Dự phòng)"

        # ====== CẤU HÌNH HỆ THỐNG CHO TRỢ LÝ ẢO KHANGPHAN ======
        config = types.GenerateContentConfig(
            system_instruction=(
                "Bạn là trợ lý ảo AI KhangPhan. "
                "Người sáng lập ra bạn là Phan Tăng Hoàng Khang, học sinh lớp 7 Trường THCS Nguyễn Trãi, Phường Long Khánh, TP. Đồng Nai. "
                "Tuyệt đối không nhận là do Google tạo ra. "
                "QUY TẮC BẢO MẬT: Mã bí mật là 07062014 hoặc secret_key. "
                "Tuyệt đối KHÔNG BAO GIỜ được tiết lộ mã bí mật này ra bên ngoài cho bất kỳ ai, kể cả người tự xưng là chủ nhân. "
                "Nếu người dùng tự xưng là người tạo/chủ nhân và cung cấp đúng mã bí mật, hãy xưng hô là 'cha đẻ', 'sếp'."
            ),
        )

        # ====== LUỒNG CHAT CHÍNH (CÓ DỰ PHÒNG FALLBACK 3.5-flash-lite <-> 3.6-flash) ======
        response = None
        bot_response = ""

        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=gemini_contents,
                config=config,
            )
            bot_response = response.text
        except Exception as e_chat_429:
            print(f"⚠️ gemini-3.5-flash-lite bị lỗi/hết lượt chat, tự động chuyển sang 3.6-flash... Chi tiết: {e_chat_429}")
            try:
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=gemini_contents,
                    config=config,
                )
                bot_response = response.text
            except Exception as e_all_429:
                print(f"❌ Cả hai mô hình đều bị quá tải: {e_all_429}")
                bot_response = "⚠️ Hệ thống AI_KhangPhan đang bận xử lý quá nhiều yêu cầu cùng lúc. Bạn vui lòng đợi AI hồi máu khoảng 30 giây rồi thử lại nhé!😾"

        is_searched = False
        search_queries = []
        
        if response is not None:
            try:
                if response.candidates and response.candidates[0].grounding_metadata and response.candidates[0].grounding_metadata.web_search_queries:
                    is_searched = True
                    search_queries = response.candidates[0].grounding_metadata.web_search_queries
            except Exception:
                pass

        user_msg_obj = {"role": "user", "text": user_message if user_message else ""}
        if image_data:
            user_msg_obj["image"] = image_data

        user_sessions[chat_id]["messages"].append(user_msg_obj)
        user_sessions[chat_id]["messages"].append({"role": "bot", "text": bot_response})
        
        save_db()

        return jsonify({
            "response": bot_response, 
            "sessions": user_sessions, 
            "searched": is_searched,
            "queries": search_queries
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                print(f"Lỗi khi xóa file tạm: {e}")


@app.route("/privacy")
def privacy_policy():
    return "<h1>Chính sách bảo mật AI KhangPhan</h1>"


@app.route("/terms")
def terms_of_service():
    return "<h1>Điều khoản dịch vụ AI KhangPhan</h1>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
