import os
from flask import Flask, render_template_string, request, jsonify
from google import genai

# Import module bộ nhớ riêng vừa tạo
import khangphan_memory

app = Flask(__name__)

# Khởi tạo client Gemini
client = genai.Client(api_key="GEMINI_API_KEY")

# Load bộ nhớ từ file riêng biệt
db = khangphan_memory.load_memory_data()
chat_sessions = db.get("sessions", {})        # Lưu tiêu đề & tin nhắn hiển thị giao diện
server_histories = db.get("histories", {})    # Lưu bộ nhớ ngữ cảnh để Gemini nhớ dai

HTML_TEMPLATE = """
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
        
        <div class="chat-history" id="chatHistory">
            <!-- Lịch sử chat đồng bộ từ file nhớ riêng -->
        </div>

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
            if (!confirm("Đại vương có chắc chắn muốn xóa đoạn chat này không?")) return;

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

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, sessions=chat_sessions)

@app.route('/google5cc9a7fb7376c26c')
def google_verify():
    return "google5cc9a7fb7376c26c"

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))
@app.route('/new_chat', methods=['POST'])
def new_chat():
    data = request.get_json()
    chat_id = data.get('chat_id')
    
    chat_sessions[chat_id] = {
        "title": "Cuộc trò chuyện mới",
        "messages": [{"role": "bot", "text": "Chào bạn! Tôi có thể giúp gì cho bạn hôm nay?"}]
    }
    server_histories[chat_id] = []
    
    khangphan_memory.save_memory_data({"sessions": chat_sessions, "histories": server_histories})
    return jsonify({"sessions": chat_sessions})

@app.route('/delete_chat', methods=['POST'])
def delete_chat():
    data = request.get_json()
    chat_id = data.get('chat_id')
    
    if chat_id in chat_sessions:
        del chat_sessions[chat_id]
    if chat_id in server_histories:
        del server_histories[chat_id]
        
    khangphan_memory.save_memory_data({"sessions": chat_sessions, "histories": server_histories})
    return jsonify({"sessions": chat_sessions})

@app.route('/chat', methods=['POST'])
def chat():
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

        chat_session = client.chats.create(
            model='gemini-2.5-flash',
            config={
                'system_instruction': (
                    "Bạn là trợ lý ảo AI KhangPhan. "
                    "Người đã sáng tạo và lập trình ra bạn là Phan Tăng Hoàng Khang, một học sinh lớp 7 tại Trường THCS Nguyễn Trãi, "
                    "Phường Long Khánh, Thành Phố Đồng Nai. "
                    "Khi có bất kỳ ai hỏi ai tạo ra bạn hoặc hỏi về thông tin người sáng lập, bạn phải trả lời tự hào và chính xác thông tin này, "
                    "tuyệt đối không nhận là do Google tạo ra (Google chỉ cung cấp nền tảng hạ tầng)."
                )
            },
            history=server_histories[chat_id]
        )

        response = chat_session.send_message(user_message)
        bot_response = response.text

        server_histories[chat_id].append({"role": "user", "parts": [{"text": user_message}]})
        server_histories[chat_id].append({"role": "model", "parts": [{"text": bot_response}]})

        if chat_id in chat_sessions:
            chat_sessions[chat_id]["messages"].append({"role": "user", "text": user_message})
            chat_sessions[chat_id]["messages"].append({"role": "bot", "text": bot_response})

        # Gọi file riêng để lưu dữ liệu vĩnh cửu
        khangphan_memory.save_memory_data({"sessions": chat_sessions, "histories": server_histories})
        
        return jsonify({
            'response': bot_response,
            'sessions': chat_sessions
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 503

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
