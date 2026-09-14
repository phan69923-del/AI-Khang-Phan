import base64
import json
import os
import traceback
from authlib.integrations.flask_client import OAuth
from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for
from google import genai
from google.genai import types
import khangphan_memory

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "07062014")

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

# Tải bộ nhớ dữ liệu toàn cục qua khangphan_memory
db = khangphan_memory.load_memory_data()
users_db = db.setdefault("users", {})
all_chat_sessions = db.setdefault("sessions", {})
all_server_histories = db.setdefault("histories", {})


def get_current_user_sessions():
    user = session.get("user")
    if not user:
        return {}
    if user not in all_chat_sessions:
        all_chat_sessions[user] = {}
    return all_chat_sessions[user]


def get_current_user_histories():
    user = session.get("user")
    if not user:
        return {}
    if user not in all_server_histories:
        all_server_histories[user] = {}
    return all_server_histories[user]


def save_db():
    khangphan_memory.save_memory_data(
        {"sessions": all_chat_sessions, "histories": all_server_histories, "users": users_db}
    )


# ==================== HTML TEMPLATES ====================

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
            width: 340px; 
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
        .google-btn {
            background-color: #f1f5f9;
            color: #0f172a;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            font-weight: 600;
            text-decoration: none;
            margin-top: 12px;
            padding: 12px;
            border-radius: 6px;
        }
        .google-btn:hover { background-color: #e2e8f0; }
        .divider {
            margin: 15px 0;
            border-bottom: 1px solid #334155;
            position: relative;
        }
        .divider span {
            position: absolute;
            top: -10px;
            left: 50%;
            transform: translateX(-50%);
            background: #1e293b;
            padding: 0 10px;
            font-size: 12px;
            color: #94a3b8;
        }
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
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();

            if (res.ok && data.success) {
                window.location.href = data.redirect || '/';
            } else {
                errorMsg.innerText = data.error || 'Có lỗi xảy ra!';
            }
        } catch (err) {
            errorMsg.innerText = 'Lỗi kết nối máy chủ!';
        }
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
    <title>AI KhangPhan - Trợ lý ảo thông minh</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: #131314; color: #e3e3e3; display: flex; height: 100vh; overflow: hidden; }
        .sidebar { width: 260px; background-color: #1e1f20; border-right: 1px solid #2b2c2d; display: flex; flex-direction: column; justify-content: space-between; height: 100vh; position: fixed; left: 0; top: 0; z-index: 1000; transition: transform 0.3s ease; }
        .sidebar.closed { transform: translateX(-100%); }
        .sidebar-top { padding: 16px; }
        .sidebar-logo-container { display: flex; align-items: center; gap: 10px; padding: 8px 4px; margin-bottom: 20px; }
        .sidebar-logo-container i { font-size: 20px; color: #8ab4f8; }
        .sidebar-logo-container span { color: #ffffff; font-weight: 600; font-size: 15px; }
        .new-chat-btn { display: flex; align-items: center; gap: 10px; background-color: #2b2c2d; color: #ffffff; border: none; padding: 12px 16px; border-radius: 30px; width: 100%; cursor: pointer; font-size: 14px; font-weight: 500; }
        .new-chat-btn:hover { background-color: #38393a; }
        .chat-history { padding: 0 16px; overflow-y: auto; flex: 1; }
        .history-item { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-radius: 20px; font-size: 14px; color: #cccccc; cursor: pointer; margin-top: 5px; }
        .history-item:hover, .history-item.active { background-color: #2b2c2d; color: #ffffff; }
        .history-content { display: flex; align-items: center; gap: 10px; flex: 1; overflow: hidden; }
        .history-text { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .delete-chat-btn { background: none; border: none; color: #888888; cursor: pointer; padding: 4px 6px; border-radius: 50%; font-size: 12px; }
        .delete-chat-btn:hover { color: #ff6b6b; background-color: rgba(255, 107, 107, 0.1); }
        .sidebar-footer { padding: 16px; border-top: 1px solid #2b2c2d; font-size: 13px; color: #aaaaaa; }
        .footer-actions { display: flex; gap: 8px; margin-top: 10px; }
        .footer-btn { flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px; background-color: #2b2c2d; color: #ffffff; border: none; padding: 8px 10px; border-radius: 16px; cursor: pointer; font-size: 13px; text-decoration: none; }
        .main-chat { margin-left: 260px; width: calc(100% - 260px); display: flex; flex-direction: column; height: 100vh; background-color: #131314; transition: margin-left 0.3s ease, width 0.3s ease; }
        .main-chat.expanded { margin-left: 0; width: 100%; }
        .chat-header { padding: 16px 24px; font-size: 16px; font-weight: 500; color: #c4c7c5; border-bottom: 1px solid #2b2c2d; display: flex; align-items: center; gap: 12px; }
        .sidebar-toggle-btn { background: none; border: none; cursor: pointer; padding: 8px; border-radius: 50%; color: #e3e3e3; }
        .chat-messages { flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 20px; max-width: 900px; width: 100%; margin: 0 auto; }
        .message { max-width: 80%; line-height: 1.6; font-size: 15px; padding: 12px 18px; border-radius: 16px; word-wrap: break-word; }
        .message.user { background-color: #2b2c2d; align-self: flex-end; color: #ffffff; border-bottom-right-radius: 4px; }
        .message.bot { background-color: #1e1f20; align-self: flex-start; color: #e3e3e3; border: 1px solid #2b2c2d; border-bottom-left-radius: 4px; }
        .message.bot p { margin-bottom: 8px; }
        .message.bot p:last-child { margin-bottom: 0; }
        .chat-input-container { padding: 20px 24px; }
        .chat-input-box { max-width: 900px; margin: 0 auto; background-color: #1e1f20; border-radius: 30px; display: flex; align-items: center; padding: 8px 16px; border: 1px solid #333333; }
        .chat-input-box textarea { flex: 1; background: none; border: none; color: #ffffff; font-size: 15px; resize: none; outline: none; max-height: 120px; padding: 8px 0; }
        .send-btn { background: none; border: none; color: #8ab4f8; font-size: 18px; cursor: pointer; padding: 8px; border-radius: 50%; }
    </style>
</head>
<body>
    <div class="sidebar" id="sidebar">
        <div class="sidebar-top">
            <div class="sidebar-logo-container">
                <i class="fa-solid fa-brain"></i>
                <span>AI KhangPhan</span>
            </div>
            <button class="new-chat-btn" onclick="startNewChat()">
                <i class="fa-solid fa-plus"></i> Cuộc trò chuyện mới
            </button>
        </div>
        <div class="chat-history" id="chatHistory"></div>
        <div class="sidebar-footer">
            <div>Khang Phan WorkSpace</div>
            <div class="footer-actions">
                <a href="/logout" class="footer-btn"><i class="fa-solid fa-right-from-bracket"></i> Đăng xuất</a>
            </div>
        </div>
    </div>

    <div class="main-chat" id="mainChat">
        <div class="chat-header">
            <button class="sidebar-toggle-btn" onclick="toggleSidebar()"><i id="toggleIcon" class="fa-solid fa-bars"></i></button>
            <span id="chatTitleHeader">AI KhangPhan</span>
        </div>
        <div class="chat-messages" id="chatMessages">
            <div class="message bot">Chào bạn! Tôi có thể giúp gì cho bạn hôm nay?</div>
        </div>
        <div class="chat-input-container">
            <div id="imagePreviewContainer" style="display: none; padding: 5px 10px; align-items: center; gap: 10px; background: #1e1f20; border-radius: 12px 12px 0 0; max-width: 900px; margin: 0 auto; border-left: 1px solid #333; border-right: 1px solid #333; border-top: 1px solid #333;">
                <img id="imagePreview" src="" alt="Preview" style="height: 50px; border-radius: 6px; object-fit: cover;">
                <span style="font-size: 13px; color: #aaa; flex: 1;">Đã đính kèm ảnh</span>
                <button onclick="removeAttachedImage()" style="background: none; border: none; color: #ff6b6b; cursor: pointer; font-size: 14px;"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div class="chat-input-box" id="chatInputBox">
                <textarea id="userInput" placeholder="Hỏi AI Khang Phan hoặc dán ảnh (Ctrl + V)..." rows="1" onkeydown="checkEnter(event)"></textarea>
                <button class="send-btn" onclick="sendMessage()"><i class="fa-solid fa-paper-plane"></i></button>
            </div>
        </div>
    </div>

    <script>
        let chatSessions = {{ sessions | tojson | safe }};
        let currentChatId = "";
        let attachedImageBase64 = null;

        const sessionKeys = Object.keys(chatSessions);
        if (sessionKeys.length > 0) {
            currentChatId = sessionKeys[0];
            loadChatSession(currentChatId);
        } else {
            currentChatId = 'chat_' + Date.now();
            chatSessions[currentChatId] = { title: "Cuộc trò chuyện mới", messages: [] };
        }
        renderHistoryList();

        document.getElementById('userInput').addEventListener('paste', function(event) {
            const items = (event.clipboardData || event.originalEvent.clipboardData).items;
            for (let index in items) {
                let item = items[index];
                if (item.kind === 'file' && item.type.startsWith('image/')) {
                    let blob = item.getAsFile();
                    let reader = new FileReader();
                    reader.onload = function(e) {
                        attachedImageBase64 = e.target.result;
                        document.getElementById('imagePreview').src = attachedImageBase64;
                        document.getElementById('imagePreviewContainer').style.display = 'flex';
                        document.getElementById('chatInputBox').style.borderTopLeftRadius = '0';
                        document.getElementById('chatInputBox').style.borderTopRightRadius = '0';
                    };
                    reader.readAsDataURL(blob);
                    break;
                }
            }
        });

        function removeAttachedImage() {
            attachedImageBase64 = null;
            document.getElementById('imagePreviewContainer').style.display = 'none';
            document.getElementById('imagePreview').src = '';
            document.getElementById('chatInputBox').style.borderTopLeftRadius = '30px';
            document.getElementById('chatInputBox').style.borderTopRightRadius = '30px';
        }

        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            const mainChat = document.getElementById('mainChat');
            sidebar.classList.toggle('closed');
            mainChat.classList.toggle('expanded');
        }

        function checkEnter(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }

        async function startNewChat(autoRender = true) {
            const newId = 'chat_' + Date.now();
            currentChatId = newId;
            chatSessions[newId] = { title: "Cuộc trò chuyện mới", messages: [] };
            if (autoRender) {
                loadChatSession(newId);
            }
            renderHistoryList();
            try {
                await fetch('/new_chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ chat_id: newId })
                });
            } catch (e) { console.error(e); }
        }

        function renderHistoryList() {
            const historyContainer = document.getElementById('chatHistory');
            historyContainer.innerHTML = '';
            for (let id in chatSessions) {
                const item = document.createElement('div');
                item.className = `history-item ${id === currentChatId ? 'active' : ''}`;
                item.innerHTML = `
                    <div class="history-content" onclick="loadChatSession('${id}')">
                        <i class="fa-regular fa-message"></i>
                        <span class="history-text">${chatSessions[id].title}</span>
                    </div>
                    <button class="delete-chat-btn" onclick="deleteChat(event, '${id}')"><i class="fa-solid fa-trash-can"></i></button>
                `;
                historyContainer.appendChild(item);
            }
        }

        function loadChatSession(id) {
            currentChatId = id;
            if (!chatSessions[id]) return;
            document.getElementById('chatTitleHeader').textContent = chatSessions[id].title;
            const chatMessages = document.getElementById('chatMessages');
            chatMessages.innerHTML = '';
            chatSessions[id].messages.forEach(msg => {
                const msgDiv = document.createElement('div');
                msgDiv.className = `message ${msg.role === 'user' ? 'user' : 'bot'}`;

                let htmlContent = '';
                if (msg.image) {
                    htmlContent += `<img src="${msg.image}" style="max-width: 200px; display: block; margin-bottom: 8px; border-radius: 8px;">`;
                }
                if (msg.text) {
                    if (msg.role === 'bot') {
                        htmlContent += marked.parse(msg.text);
                    } else {
                        const textSpan = document.createElement('span');
                        textSpan.textContent = msg.text;
                        htmlContent += textSpan.outerHTML;
                    }
                }
                msgDiv.innerHTML = htmlContent;
                chatMessages.appendChild(msgDiv);
            });
            renderHistoryList();
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        async function deleteChat(event, id) {
            event.stopPropagation();
            if (!confirm("Bạn có chắc muốn xóa đoạn chat này?")) return;
            const response = await fetch('/delete_chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_id: id })
            });
            const data = await response.json();
            if (response.ok) {
                chatSessions = data.sessions;
                const keys = Object.keys(chatSessions);
                if (keys.length > 0) loadChatSession(keys[0]);
                else startNewChat();
            }
        }

        async function sendMessage() {
            const input = document.getElementById('userInput');
            const messageText = input.value.trim();
            if (!messageText && !attachedImageBase64) return;

            if (!currentChatId) {
                currentChatId = 'chat_' + Date.now();
                chatSessions[currentChatId] = { title: "Cuộc trò chuyện mới", messages: [] };
            }

            const chatMessages = document.getElementById('chatMessages');
            const userMsg = document.createElement('div');
            userMsg.className = 'message user';

            let htmlContent = '';
            if (attachedImageBase64) {
                htmlContent += `<img src="${attachedImageBase64}" style="max-width: 200px; display: block; margin-bottom: 8px; border-radius: 8px;">`;
            }
            if (messageText) {
                htmlContent += `<span>${messageText}</span>`;
            }
            userMsg.innerHTML = htmlContent;
            chatMessages.appendChild(userMsg);

            const payloadText = messageText;
            const payloadImage = attachedImageBase64;

            input.value = '';
            removeAttachedImage();
            chatMessages.scrollTop = chatMessages.scrollHeight;

            const botMsg = document.createElement('div');
            botMsg.className = 'message bot';
            botMsg.innerHTML = "Đang suy nghĩ... 💭";
            chatMessages.appendChild(botMsg);

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

        # Xây dựng lại ngữ cảnh chat cũ từ bộ nhớ để AI nhớ lịch sử trò chuyện
        gemini_contents = []
        for msg in user_sessions[chat_id]["messages"]:
            role = "user" if msg["role"] == "user" else "model"
            content_parts = []
            if "image" in msg and msg["image"]:
                try:
                    header, encoded = msg["image"].split(",", 1)
                    mime_type = header.split(";")[0].split(":")[1]
                    image_bytes = base64.b64decode(encoded)
                    content_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
                except Exception:
                    pass
            if "text" in msg and msg["text"]:
                content_parts.append(msg["text"])
            
            if content_parts:
                gemini_contents.append(types.Content(role=role, parts=content_parts))

        # Thêm tin nhắn mới nhất của người dùng
        current_new_parts = []
        if image_data:
            header, encoded = image_data.split(",", 1)
            mime_type = header.split(";")[0].split(":")[1]
            image_bytes = base64.b64decode(encoded)
            current_new_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))

        if user_message:
            current_new_parts.append(user_message)
        else:
            current_new_parts.append("Hãy mô tả hoặc phân tích bức ảnh này giúp tôi.")
        
        gemini_contents.append(types.Content(role="user", parts=current_new_parts))

        # Tạo tiêu đề tự động gọn gàng nếu là cuộc trò chuyện mới
        if user_sessions[chat_id]["title"] == "Cuộc trò chuyện mới":
            try:
                title_prompt = user_message if user_message else "Phân tích hình ảnh"
                title_response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=(
                        f"Nhiệm vụ duy nhất: Đặt tiêu đề tối đa 5 từ cho nội dung: '{title_prompt}'. "
                        "CHỈ TRẢ VỀ ĐÚNG TỪ KHÓA TIÊU ĐỀ, tuyệt đối không viết thêm bất kỳ câu dẫn dắt, giải thích hay dấu sao nào."
                    ),
                )
                new_title = title_response.text.strip().replace('"', "").replace('*', "").replace('#', "")
                if new_title:
                    words = new_title.split()
                    if len(words) > 6:
                        new_title = " ".join(words[:5])
                    user_sessions[chat_id]["title"] = new_title
            except Exception as e:
                print(f"Lỗi tạo tiêu đề: {e}")

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

        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=gemini_contents,
            config=config,
        )

        bot_response = response.text

        is_searched = False
        search_queries = []
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


@app.route("/privacy")
def privacy_policy():
    return "<h1>Chính sách bảo mật AI KhangPhan</h1>"


@app.route("/terms")
def terms_of_service():
    return "<h1>Điều khoản dịch vụ AI KhangPhan</h1>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
