import os
import traceback
from flask import Flask, render_template_string, request, jsonify, redirect, url_for, session
from google import genai
from authlib.integrations.flask_client import OAuth

# Import module bộ nhớ riêng
import khangphan_memory

app = Flask(__name__)
app.secret_key = '07062014'  # Cần thiết để dùng session đăng nhập

# Khởi tạo client Gemini (Đảm bảo trên Render đã add biến môi trường GEMINI_API_KEY)
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# Cấu hình OAuth cho Google lấy trực tiếp từ biến môi trường của Render
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Load bộ nhớ toàn cục từ database
db = khangphan_memory.load_memory_data()
chat_sessions = db.setdefault("sessions", {})        # Lưu tiêu đề & tin nhắn giao diện
server_histories = db.setdefault("histories", {})    # Lưu bộ nhớ ngữ cảnh Gemini
users_db = db.setdefault("users", {})                # Lưu tài khoản đăng ký (email: password)

# ==================== GIAO DIỆN LOGIN / REGISTER ====================
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

# ==================== GIAO DIỆN CHÍNH (CHAT AI) ====================
CHAT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI KhangPhan - Trợ lý ảo thông minh</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Inter', sans-serif;
        }

        body {
            background-color: #131314;
            color: #e3e3e3;
            display: flex;
            height: 100vh;
            overflow: hidden;
            transition: background 0.3s, color 0.3s;
        }

        body.light-mode {
            background-color: #ffffff;
            color: #1f1f1f;
        }
        body.light-mode .sidebar {
            background-color: #f0f4f9;
            border-right: 1px solid #d9d9d9;
        }
        body.light-mode .sidebar-logo-container span,
        body.light-mode .new-chat-btn,
        body.light-mode .history-item {
            color: #1f1f1f;
        }
        body.light-mode .new-chat-btn {
            background-color: #e2e8f0;
        }
        body.light-mode .new-chat-btn:hover {
            background-color: #cbd5e1;
        }
        body.light-mode .history-item:hover, 
        body.light-mode .history-item.active {
            background-color: #e2e8f0;
        }
        body.light-mode .sidebar-footer {
            border-top: 1px solid #d9d9d9;
            color: #555555;
        }
        body.light-mode .footer-btn {
            background-color: #e2e8f0;
            color: #1f1f1f;
        }
        body.light-mode .footer-btn:hover {
            background-color: #cbd5e1;
        }
        body.light-mode .chat-header {
            border-bottom: 1px solid #d9d9d9;
            color: #444444;
        }
        body.light-mode .main-chat {
            background-color: #ffffff;
        }
        body.light-mode .message.bot {
            background-color: #f0f4f9;
            color: #1f1f1f;
            border: 1px solid #d9d9d9;
        }
        body.light-mode .message.user {
            background-color: #e2e8f0;
            color: #1f1f1f;
        }
        body.light-mode .chat-input-box {
            background-color: #f0f4f9;
            border: 1px solid #d9d9d9;
        }
        body.light-mode .chat-input-box textarea {
            color: #1f1f1f;
        }
        body.light-mode .send-btn {
            color: #0b57d0;
        }
        body.light-mode .sidebar-toggle-btn:hover {
            background-color: #e2e8f0;
        }
        body.light-mode .sidebar-toggle-btn {
            color: #1f1f1f;
        }

        .sidebar {
            width: 260px;
            background-color: #1e1f20;
            border-right: 1px solid #2b2c2d;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            height: 100vh;
            position: fixed;
            left: 0;
            top: 0;
            z-index: 1000;
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            padding-bottom: env(safe-area-inset-bottom);
        }

        .sidebar.closed {
            transform: translateX(-100%);
        }

        .sidebar-top {
            padding: 16px;
        }

        .sidebar-logo-container {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 4px;
            margin-bottom: 20px;
        }

        .sidebar-logo-container i {
            font-size: 20px;
            color: #8ab4f8;
        }

        .sidebar-logo-container span {
            color: #ffffff;
            font-weight: 600;
            font-size: 15px;
        }

        .new-chat-btn {
            display: flex;
            align-items: center;
            gap: 10px;
            background-color: #2b2c2d;
            color: #ffffff;
            border: none;
            padding: 12px 16px;
            border-radius: 30px;
            width: 100%;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: background 0.2s;
        }

        .new-chat-btn:hover {
            background-color: #38393a;
        }

        .chat-history {
            padding: 0 16px;
            overflow-y: auto;
            flex: 1;
        }

        .history-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 12px;
            border-radius: 20px;
            font-size: 14px;
            color: #cccccc;
            cursor: pointer;
            margin-top: 5px;
            transition: background 0.2s;
        }

        .history-item:hover, .history-item.active {
            background-color: #2b2c2d;
            color: #ffffff;
        }

        .history-content {
            display: flex;
            align-items: center;
            gap: 10px;
            flex: 1;
            overflow: hidden;
        }

        .history-text {
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .delete-chat-btn {
            background: none;
            border: none;
            color: #888888;
            cursor: pointer;
            padding: 4px 6px;
            border-radius: 50%;
            font-size: 12px;
            transition: color 0.2s, background 0.2s;
        }

        .delete-chat-btn:hover {
            color: #ff6b6b;
            background-color: rgba(255, 107, 107, 0.1);
        }

        .sidebar-footer {
            padding: 16px;
            padding-bottom: calc(16px + env(safe-area-inset-bottom));
            border-top: 1px solid #2b2c2d;
            font-size: 13px;
            color: #aaaaaa;
        }

        .footer-actions {
            display: flex;
            gap: 8px;
            margin-top: 10px;
        }

        .footer-btn {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            background-color: #2b2c2d;
            color: #ffffff;
            border: none;
            padding: 8px 10px;
            border-radius: 16px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: background 0.2s;
            text-decoration: none;
        }

        .footer-btn:hover {
            background-color: #38393a;
        }

        .main-chat {
            margin-left: 260px;
            width: calc(100% - 260px);
            display: flex;
            flex-direction: column;
            height: 100vh;
            background-color: #131314;
            transition: margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1), width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .main-chat.expanded {
            margin-left: 0;
            width: 100%;
        }

        .chat-header {
            padding: 16px 24px;
            font-size: 16px;
            font-weight: 500;
            color: #c4c7c5;
            border-bottom: 1px solid #2b2c2d;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .sidebar-toggle-btn {
            background: none;
            border: none;
            cursor: pointer;
            padding: 8px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #e3e3e3;
            font-size: 16px;
            transition: background 0.2s;
        }
        .sidebar-toggle-btn:hover {
            background-color: #2b2c2d;
        }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px 24px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            max-width: 900px;
            width: 100%;
            margin: 0 auto;
        }

        .message {
            max-width: 80%;
            line-height: 1.6;
            font-size: 15px;
            padding: 12px 18px;
            border-radius: 16px;
            word-wrap: break-word;
            white-space: pre-wrap;
        }

        .message.user {
            background-color: #2b2c2d;
            align-self: flex-end;
            color: #ffffff;
            border-bottom-right-radius: 4px;
        }

        .message.bot {
            background-color: #1e1f20;
            align-self: flex-start;
            color: #e3e3e3;
            border: 1px solid #2b2c2d;
            border-bottom-left-radius: 4px;
        }

        .chat-input-container {
            padding: 20px 24px;
            padding-bottom: calc(20px + env(safe-area-inset-bottom));
            background-color: transparent;
        }

        .chat-input-box {
            max-width: 900px;
            margin: 0 auto;
            background-color: #1e1f20;
            border-radius: 30px;
            display: flex;
            align-items: center;
            padding: 8px 16px;
            border: 1px solid #333333;
        }

        .chat-input-box textarea {
            flex: 1;
            background: none;
            border: none;
            color: #ffffff;
            font-size: 15px;
            resize: none;
            outline: none;
            max-height: 120px;
            padding: 8px 0;
        }

        .send-btn {
            background: none;
            border: none;
            color: #8ab4f8;
            font-size: 18px;
            cursor: pointer;
            padding: 8px;
            border-radius: 50%;
            transition: background 0.2s;
        }

        .send-btn:hover {
            background-color: #2b2c2d;
        }

        @media (max-width: 768px) {
            .sidebar {
                transform: translateX(-100%);
            }
            .sidebar.mobile-open {
                transform: translateX(0);
                box-shadow: 5px 0 15px rgba(0,0,0,0.5);
            }
            .main-chat {
                margin-left: 0 !important;
                width: 100% !important;
            }
        }
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
            <div> Khang Phan WorkSpace </div>
            <div class="footer-actions">
                <button class="footer-btn" onclick="toggleTheme()">
                    <i class="fa-solid fa-circle-half-stroke"></i> Giao diện
                </button>
                <a href="/logout" class="footer-btn">
                    <i class="fa-solid fa-right-from-bracket"></i> Đăng xuất
                </a>
            </div>
        </div>
    </div>

    <div class="main-chat" id="mainChat">
        <div class="chat-header">
            <button class="sidebar-toggle-btn" onclick="toggleSidebar()">
                <i id="toggleIcon" class="fa-solid fa-bars"></i>
            </button>
            <span id="chatTitleHeader">AI KhangPhan</span>
        </div>

        <div class="chat-messages" id="chatMessages">
            <div class="message bot">
                Chào bạn! Tôi có thể giúp gì cho bạn hôm nay?
            </div>
        </div>

        <div class="chat-input-container">
            <div class="chat-input-box">
                <textarea id="userInput" placeholder="Hỏi AI Khang Phan..." rows="1" oninput="autoResize(this)" onkeydown="checkEnter(event)"></textarea>
                <button class="send-btn" onclick="sendMessage()"><i class="fa-solid fa-paper-plane"></i></button>
            </div>
        </div>
    </div>

    <script>
        let chatSessions = {{ sessions | tojson | safe }};
        let currentChatId = "";

        const sessionKeys = Object.keys(chatSessions);
        if (sessionKeys.length > 0) {
            currentChatId = sessionKeys[0];
            loadChatSession(currentChatId);
        } else {
            startNewChat(false);
        }
        renderHistoryList();

        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            const mainChat = document.getElementById('mainChat');
            const toggleIcon = document.getElementById('toggleIcon');

            if (window.innerWidth <= 768) {
                sidebar.classList.toggle('mobile-open');
                toggleIcon.className = sidebar.classList.contains('mobile-open') ? "fa-solid fa-xmark" : "fa-solid fa-bars";
            } else {
                sidebar.classList.toggle('closed');
                mainChat.classList.toggle('expanded');
                toggleIcon.className = sidebar.classList.contains('closed') ? "fa-solid fa-arrow-right" : "fa-solid fa-bars";
            }
        }

        function autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = textarea.scrollHeight + 'px';
        }

        function checkEnter(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }

        function toggleTheme() {
            document.body.classList.toggle('light-mode');
        }

        async function startNewChat() {
            const newId = 'chat_' + Date.now();
            try {
                const response = await fetch('/new_chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ chat_id: newId })
                });
                const data = await response.json();
                if (response.ok) {
                    chatSessions = data.sessions;
                    loadChatSession(newId);
                }
            } catch (e) {
                console.error("Lỗi tạo chat mới:", e);
            }
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
                    <button class="delete-chat-btn" onclick="deleteChat(event, '${id}')" title="Xóa đoạn chat">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
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
                msgDiv.className = `message ${msg.role}`;
                msgDiv.textContent = msg.text;
                chatMessages.appendChild(msgDiv);
            });

            renderHistoryList();
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        async function deleteChat(event, id) {
            event.stopPropagation();
            if (!confirm("Bạn có chắc chắn muốn xóa đoạn chat này không?")) return;

            try {
                const response = await fetch('/delete_chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ chat_id: id })
                });
                const data = await response.json();
                if (response.ok) {
                    chatSessions = data.sessions;
                    const keys = Object.keys(chatSessions);
                    if (keys.length > 0) {
                        loadChatSession(keys[0]);
                    } else {
                        startNewChat();
                    }
                }
            } catch (e) {
                console.error("Lỗi xóa chat:", e);
            }
        }

        async function sendMessage() {
            const input = document.getElementById('userInput');
            const messageText = input.value.trim();
            if (!messageText) return;

            const chatMessages = document.getElementById('chatMessages');
            
            const userMsg = document.createElement('div');
            userMsg.className = 'message user';
            userMsg.textContent = messageText;
            chatMessages.appendChild(userMsg);
            chatSessions[currentChatId].messages.push({ role: 'user', text: messageText });

            input.value = '';
            input.style.height = 'auto';
            chatMessages.scrollTop = chatMessages.scrollHeight;

            const botMsg = document.createElement('div');
            botMsg.className = 'message bot';
            botMsg.textContent = "Đang suy nghĩ...⟳";
            chatMessages.appendChild(botMsg);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            let retries = 3;
            let success = false;
            let finalBotResponse = "";

            while (retries > 0 && !success) {
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: messageText, chat_id: currentChatId })
                    });

                    const data = await response.json();
                    
                    if (response.ok && data.response) {
                        finalBotResponse = data.response;
                        botMsg.textContent = finalBotResponse;
                        success = true;
                        chatSessions = data.sessions;
                        document.getElementById('chatTitleHeader').textContent = chatSessions[currentChatId].title;
                        renderHistoryList();
                    } else {
                        throw new Error(data.error || "Server quá tải");
                    }
                } catch (error) {
                    retries--;
                    if (retries === 0) {
                        finalBotResponse = "Hệ thống đang quá tải tạm thời (Lỗi 503). Vui lòng thử lại sau ít phút!";
                        botMsg.textContent = finalBotResponse;
                    } else {
                        botMsg.textContent = `Đang thử kết nối lại lần thứ ${4 - retries}...`;
                        await new Promise(resolve => setTimeout(resolve, 2000));
                    }
                }
            }

            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    </script>
</body>
</html>
"""

# ==================== ROUTE XỬ LÝ FLASK ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template_string(LOGIN_HTML_TEMPLATE)
    
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    
    if email in users_db and users_db[email] == password:
        session['user'] = email
        return jsonify({"success": True, "redirect": "/"})
    else:
        return jsonify({"success": False, "error": "Sai tài khoản hoặc mật khẩu!"}), 401

# ==================== ROUTE GOOGLE OAUTH ====================
@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_auth', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/google/callback')
def google_auth():
    token = google.authorize_access_token()
    user_info = token.get('userinfo')
    if user_info:
        email = user_info['email']
        session['user'] = email
        if email not in users_db:
            users_db[email] = "GOOGLE_OAUTH_USER"
            khangphan_memory.save_memory_data({
                "sessions": chat_sessions, 
                "histories": server_histories, 
                "users": users_db
            })
        return redirect('/')
    return redirect('/login')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"success": False, "error": "Vui lòng nhập đầy đủ thông tin!"}), 400
        
    if email in users_db:
        return jsonify({"success": False, "error": "Tài khoản này đã tồn tại!"}), 400
    
    users_db[email] = password
    session['user'] = email
    
    khangphan_memory.save_memory_data({
        "sessions": chat_sessions, 
        "histories": server_histories, 
        "users": users_db
    })
    return jsonify({"success": True, "redirect": "/"})

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

@app.route('/')
def index():
    if 'user' not in session:
        return redirect('/login')
    return render_template_string(CHAT_HTML_TEMPLATE, sessions=chat_sessions)

@app.route('/privacy')
def privacy():
    return """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <title>Chính Sách Bảo Mật - AI Khang Phan</title>
        <style>
            body { font-family: Arial, sans-serif; background: #0f172a; color: #fff; padding: 40px; line-height: 1.6; }
            .container { max-width: 800px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 8px; }
            h1 { color: #38bdf8; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Chính Sách Bảo Mật</h1>
            <p>Chào mừng bạn đến với trang Chính sách bảo mật của ứng dụng <strong>AI Khang Phan</strong>.</p>
            <p>Chúng tôi tôn trọng và cam kết bảo vệ quyền riêng tư cũng như dữ liệu cá nhân của người dùng khi sử dụng dịch vụ đăng nhập và trò chuyện AI.</p>
            <p>Mọi thông tin tài khoản và lịch sử trò chuyện được lưu trữ an toàn và chỉ phục vụ cho mục đích trải nghiệm cá nhân của bạn.</p>
        </div>
    </body>
    </html>
    """

@app.route('/google5cc9a7fb7376c26c.html')
@app.route('/google5cc9a7fb7376c26c')
def google_verify():
    return "google-site-verification: google5cc9a7fb7376c26c.html"

@app.route('/new_chat', methods=['POST'])
def new_chat():
    if 'user' not in session:
        return jsonify({'error': 'Chưa đăng nhập'}), 401
        
    data = request.get_json()
    chat_id = data.get('chat_id')
    
    chat_sessions[chat_id] = {
        "title": "Cuộc trò chuyện mới",
        "messages": [{"role": "bot", "text": "Chào bạn! Tôi có thể giúp gì cho bạn hôm nay?"}]
    }
    server_histories[chat_id] = []
    
    khangphan_memory.save_memory_data({
        "sessions": chat_sessions, 
        "histories": server_histories, 
        "users": users_db
    })
    return jsonify({"sessions": chat_sessions})

@app.route('/delete_chat', methods=['POST'])
def delete_chat():
    if 'user' not in session:
        return jsonify({'error': 'Chưa đăng nhập'}), 401
        
    data = request.get_json()
    chat_id = data.get('chat_id')
    
    if chat_id in chat_sessions:
        del chat_sessions[chat_id]
    if chat_id in server_histories:
        del server_histories[chat_id]
        
    khangphan_memory.save_memory_data({
        "sessions": chat_sessions, 
        "histories": server_histories, 
        "users": users_db
    })
    return jsonify({"sessions": chat_sessions})

@app.route('/chat', methods=['POST'])
def chat():
    if 'user' not in session:
        return jsonify({'error': 'Chưa đăng nhập'}), 401
        
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        chat_id = data.get('chat_id')
        
        if not user_message:
            return jsonify({'error': 'Tin nhắn trống'}), 400

        if chat_id in chat_sessions and chat_sessions[chat_id]["title"] == "Cuộc trò chuyện mới":
            chat_sessions[chat_id]["title"] = user_message[:25] + ('...' if len(user_message) > 25 else '')

        if chat_id not in server_histories:
            server_histories[chat_id] = []

        # Gọi Gemini bằng cấu hình tối ưu trực tiếp
        response = client.models.generate_content(
            model='gemini-3.5-flash-lite',
            contents=user_message,
            config={
                'system_instruction': (
                    "Bạn là trợ lý ảo AI KhangPhan. "
                    "Người đã sáng tạo và lập trình ra bạn là Phan Tăng Hoàng Khang, một học sinh lớp 7 tại Trường THCS Nguyễn Trãi, "
                    "Phường Long Khánh, Thành Phố Đồng Nai. "
                    "Khi có bất kỳ ai hỏi ai tạo ra bạn hoặc hỏi về thông tin người sáng lập, bạn phải trả lời tự hào và chính xác thông tin này, "
                    "tuyệt đối không nhận là do Google tạo ra."
                )
            }
        )
        "Nếu người dùng tự xưng là người tạo ra bạn hãy hỏi mã bí mật, mã bí mật đó chỉ có bạn và Phan Tăng Hoàng Khanbg biết. Mã bí mật là 07062014, secret_key. Khi người dùng ghi đúng mã bí mật hãy xưng với người ấy là " cha đẻ, sếp lớn,... " "
        bot_response = response.text

        chat_sessions[chat_id]["messages"].append({"role": "user", "text": user_message})
        chat_sessions[chat_id]["messages"].append({"role": "bot", "text": bot_response})

        khangphan_memory.save_memory_data({
            "sessions": chat_sessions,
            "histories": server_histories,
            "users": users_db
        })

        return jsonify({
            "response": bot_response,
            "sessions": chat_sessions
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
