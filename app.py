import os
import json
import traceback
from flask import Flask, render_template_string, request, jsonify, session
from google import genai

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "khangphan_secret_key_2026")

# Khởi tạo client Gemini (sử dụng biến môi trường GEMINI_API_KEY)
client = genai.Client()

DB_FILE = "chat_database.json"

# Cấu trúc lưu trữ: { chat_id: { "title": "...", "messages": [...] } }
user_sessions = {}
# Lưu lịch sử thô để gửi cho Gemini chat API: { chat_id: [ { "role": "user", "parts": [...] }, ... ] }
user_histories = {}

def load_db():
    global user_sessions, user_histories
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                user_sessions = data.get("sessions", {})
                raw_histories = data.get("histories", {})
                # Phục hồi cấu trúc history chuẩn của Gemini SDK
                user_histories = {}
                for cid, h_list in raw_histories.items():
                    user_histories[cid] = []
                    for item in h_list:
                        user_histories[cid].append({
                            "role": item.get("role"),
                            "parts": [{"text": p.get("text")} for p in item.get("parts", [])]
                        })
        except Exception as e:
            print(f"Lỗi đọc cơ sở dữ liệu: {e}")
            user_sessions = {}
            user_histories = {}

def save_db():
    try:
        data = {
            "sessions": user_sessions,
            "histories": user_histories
        }
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Lỗi lưu cơ sở dữ liệu: {e}")

# Tải dữ liệu khi khởi động ứng dụng
load_db()

# Giao diện HTML + CSS + JavaScript tích hợp sẵn trong file
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trợ lý ảo KhangPhan</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.js"></script>
    <style>
        :root {
            --bg-color: #0f172a;
            --sidebar-bg: #1e293b;
            --chat-bg: #0f172a;
            --input-bg: #334155;
            --text-color: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-color: #38bdf8;
            --accent-hover: #0ea5e9;
            --user-bubble: #2563eb;
            --bot-bubble: #1e293b;
            --border-color: #334155;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: var(--bg-color); color: var(--text-color); display: flex; height: 100vh; overflow: hidden; }
        
        /* Sidebar */
        .sidebar { width: 280px; background-color: var(--sidebar-bg); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; height: 100%; transition: transform 0.3s ease; }
        .sidebar-header { padding: 20px; border-bottom: 1px solid var(--border-color); display: flex; flex-direction: column; gap: 12px; }
        .new-chat-btn { background-color: var(--accent-color); color: #0f172a; border: none; padding: 10px 15px; border-radius: 6px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: background 0.2s; }
        .new-chat-btn:hover { background-color: var(--accent-hover); }
        
        .session-list { flex: 1; overflow-y: auto; padding: 10px; display: flex; flex-direction: column; gap: 6px; }
        .session-item { padding: 10px 12px; border-radius: 6px; cursor: pointer; color: var(--text-secondary); font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; transition: all 0.2s; }
        .session-item:hover { background-color: rgba(255,255,255,0.05); color: var(--text-color); }
        .session-item.active { background-color: rgba(56, 189, 248, 0.15); color: var(--accent-color); font-weight: 500; }
        
        .sidebar-footer { padding: 15px 20px; border-top: 1px solid var(--border-color); font-size: 12px; color: var(--text-secondary); display: flex; justify-content: space-between; align-items: center; }
        .sidebar-footer a { color: var(--text-secondary); text-decoration: none; }
        .sidebar-footer a:hover { color: var(--accent-color); text-decoration: underline; }

        /* Main Chat Area */
        .main-chat { flex: 1; display: flex; flex-direction: column; height: 100%; background-color: var(--chat-bg); }
        .chat-header { padding: 15px 25px; border-bottom: 1px solid var(--border-color); background-color: var(--sidebar-bg); font-size: 16px; font-weight: 600; display: flex; align-items: center; justify-content: space-between; }
        
        .chat-messages { flex: 1; overflow-y: auto; padding: 25px; display: flex; flex-direction: column; gap: 20px; scroll-behavior: smooth; }
        
        .message { max-width: 75%; padding: 12px 16px; border-radius: 12px; line-height: 1.5; font-size: 15px; word-wrap: break-word; }
        .message.user { background-color: var(--user-bubble); color: white; align-self: flex-end; border-bottom-right-radius: 2px; }
        .message.bot { background-color: var(--bot-bubble); color: var(--text-color); align-self: flex-start; border-bottom-left-radius: 2px; border: 1px solid var(--border-color); }
        
        .message p { margin-bottom: 8px; }
        .message p:last-child { margin-bottom: 0; }
        .message pre { background: #090d16; padding: 10px; border-radius: 6px; overflow-x: auto; margin: 8px 0; }
        .message code { font-family: Consolas, Monaco, monospace; font-size: 13px; }

        .chat-input-container { padding: 20px 25px; background-color: var(--sidebar-bg); border-top: 1px solid var(--border-color); }
        .chat-input-wrapper { display: flex; background-color: var(--input-bg); border-radius: 8px; border: 1px solid var(--border-color); overflow: hidden; transition: border-color 0.2s; }
        .chat-input-wrapper:focus-within { border-color: var(--accent-color); }
        
        textarea { flex: 1; background: transparent; border: none; padding: 12px 15px; color: var(--text-color); font-size: 15px; resize: none; max-height: 150px; outline: none; font-family: inherit; }
        .send-btn { background-color: transparent; border: none; color: var(--accent-color); padding: 0 15px; cursor: pointer; font-size: 18px; display: flex; align-items: center; justify-content: center; transition: color 0.2s; }
        .send-btn:hover { color: var(--accent-hover); }

        .welcome-screen { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-secondary); text-align: center; gap: 10px; }
        .welcome-screen h2 { color: var(--text-color); font-size: 24px; }
    </style>
</head>
<body>

    <!-- Sidebar -->
    <div class="sidebar">
        <div class="sidebar-header">
            <h2 style="color: var(--accent-color); font-size: 18px;">KhangPhan AI</h2>
            <button class="new-chat-btn" onclick="startNewChat()">+ Cuộc trò chuyện mới</button>
        </div>
        <div class="session-list" id="sessionList">
            <!-- Danh sách session render bằng JS -->
        </div>
        <div class="sidebar-footer">
            <span>&copy; 2026 KhangPhan</span>
            <div>
                <a href="/terms" target="_blank">Điều khoản</a> &bull; 
                <a href="/privacy" target="_blank">Bảo mật</a>
            </div>
        </div>
    </div>

    <!-- Main Chat -->
    <div class="main-chat">
        <div class="chat-header" id="chatHeader">Trợ lý ảo KhangPhan</div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="welcome-screen">
                <h2>Xin chào! Tôi có thể giúp gì cho bạn hôm nay?</h2>
                <p>Hãy nhắn gì đó để bắt đầu cuộc trò chuyện với trợ lý ảo KhangPhan.</p>
            </div>
        </div>

        <div class="chat-input-container">
            <div class="chat-input-wrapper">
                <textarea id="userInput" placeholder="Nhắn tin cho KhangPhan..." rows="1" onkeydown="handleKeyPress(event)"></textarea>
                <button class="send-btn" onclick="sendMessage()">&#10148;</button>
            </div>
        </div>
    </div>

    <script>
        let sessions = {{ sessions|tojson }};
        let currentChatId = "{{ current_chat_id }}";

        function renderSessions() {
            const listEl = document.getElementById('sessionList');
            listEl.innerHTML = '';
            
            const sortedIds = Object.keys(sessions).reverse();
            if (sortedIds.length === 0) {
                listEl.innerHTML = '<div style="padding: 10px; color: #64748b; font-size: 13px; text-align: center;">Chưa có lịch sử</div>';
                return;
            }

            sortedIds.forEach(id => {
                const session = sessions[id];
                const div = document.createElement('div');
                div.className = `session-item ${id === currentChatId ? 'active' : ''}`;
                div.innerText = session.title || "Cuộc trò chuyện mới";
                div.onclick = () => switchSession(id);
                listEl.appendChild(div);
            });
        }

        function renderMessages() {
            const chatMessages = document.getElementById('chatMessages');
            chatMessages.innerHTML = '';

            if (!sessions[currentChatId] || sessions[currentChatId].messages.length === 0) {
                chatMessages.innerHTML = `
                    <div class="welcome-screen">
                        <h2>Xin chào! Tôi có thể giúp gì cho bạn hôm nay?</h2>
                        <p>Hãy nhắn gì đó để bắt đầu cuộc trò chuyện với trợ lý ảo KhangPhan.</p>
                    </div>
                `;
                document.getElementById('chatHeader').innerText = "Trợ lý ảo KhangPhan";
                return;
            }

            document.getElementById('chatHeader').innerText = sessions[currentChatId].title || "Trợ lý ảo KhangPhan";

            sessions[currentChatId].messages.forEach(msg => {
                const msgDiv = document.createElement('div');
                msgDiv.className = `message ${msg.role === 'user' ? 'user' : 'bot'}`;
                
                if (msg.role === 'bot') {
                    msgDiv.innerHTML = marked.parse(msg.text);
                } else {
                    msgDiv.innerText = msg.text;
                }
                chatMessages.appendChild(msgDiv);
            });
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function startNewChat() {
            fetch('/new_chat', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                sessions = data.sessions;
                currentChatId = data.current_chat_id;
                renderSessions();
                renderMessages();
            });
        }

        function switchSession(id) {
            fetch(`/switch_chat/${id}`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                currentChatId = data.current_chat_id;
                renderSessions();
                renderMessages();
            });
        }

        function sendMessage() {
            const inputEl = document.getElementById('userInput');
            const text = inputEl.value.trim();
            if (!text) return;

            inputEl.value = '';
            inputEl.style.height = 'auto';

            // Hiển thị tin nhắn user ngay lập tức
            if (!sessions[currentChatId]) {
                sessions[currentChatId] = { title: "Cuộc trò chuyện mới", messages: [] };
            }
            sessions[currentChatId].messages.push({ role: 'user', text: text });
            renderMessages();

            fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, chat_id: currentChatId })
            })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    alert("Lỗi: " + data.error);
                    return;
                }
                sessions = data.sessions;
                renderSessions();
                renderMessages();
            })
            .catch(err => {
                console.error(err);
                alert("Đã xảy ra lỗi kết nối.");
            });
        }

        function handleKeyPress(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }

        // Tự động co giãn textarea
        const textarea = document.getElementById('userInput');
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });

        // Khởi tạo lần đầu
        renderSessions();
        renderMessages();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    if "current_chat_id" not in session or session["current_chat_id"] not in user_sessions:
        # Tạo phiên chat mặc định nếu chưa có
        import uuid
        new_id = str(uuid.uuid4())[:8]
        user_sessions[new_id] = {"title": "Cuộc trò chuyện mới", "messages": []}
        user_histories[new_id] = []
        session["current_chat_id"] = new_id
        save_db()
    
    return render_template_string(HTML_TEMPLATE, sessions=user_sessions, current_chat_id=session["current_chat_id"])

@app.route('/new_chat', methods=['POST'])
def new_chat():
    import uuid
    new_id = str(uuid.uuid4())[:8]
    user_sessions[new_id] = {"title": "Cuộc trò chuyện mới", "messages": []}
    user_histories[new_id] = []
    session["current_chat_id"] = new_id
    save_db()
    return jsonify({"current_chat_id": new_id, "sessions": user_sessions})

@app.route('/switch_chat/<chat_id>', methods=['POST'])
def switch_chat(chat_id):
    if chat_id in user_sessions:
        session["current_chat_id"] = chat_id
    return jsonify({"current_chat_id": session.get("current_chat_id")})

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()
        chat_id = data.get("chat_id")

        if not chat_id or chat_id not in user_sessions:
            return jsonify({'error': 'Phiên chat không hợp lệ'}), 400

        if chat_id not in user_histories:
            user_histories[chat_id] = []

        # CHỈ ĐỔI TÊN ĐÚNG 1 LẦN DUY NHẤT NẾU ĐANG LÀ "Cuộc trò chuyện mới"
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
            history=user_histories[chat_id]
        )

        response = chat_session.send_message(user_message)
        bot_response = response.text

        user_histories[chat_id].append({
            "role": "user",
            "parts": [{"text": user_message}]
        })
        user_histories[chat_id].append({
            "role": "model",
            "parts": [{"text": bot_response}]
        })

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

# ==================== TRANG ĐIỀU KHOẢN SỬ DỤNG ====================
@app.route('/terms')
def terms_of_service():
    return """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <title>Điều khoản sử dụng - Trợ lý ảo KhangPhan</title>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #fff; background-color: #0f172a; }
            h1 { color: #38bdf8; }
            .container { background: #1e293b; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.4); }
            a { color: #38bdf8; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Điều khoản sử dụng</h1>
            <p>Chào mừng bạn đến với trợ lý ảo KhangPhan được sáng lập và phát triển bởi <strong>Phan Tăng Hoàng Khang</strong>.</p>
            <p>Bằng việc truy cập và sử dụng ứng dụng này, bạn đồng ý tuân thủ các quy định và điều khoản sử dụng dịch vụ.</p>
            <br>
            <p><a href="/">&larr; Quay lại trang chủ chat</a></p>
        </div>
    </body>
    </html>
    """

# ==================== TRANG CHÍNH SÁCH BẢO MẬT ====================
@app.route('/privacy')
def privacy_policy():
    return """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <title>Chính sách bảo mật - Trợ lý ảo KhangPhan</title>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #fff; background-color: #0f172a; }
            h1 { color: #38bdf8; }
            .container { background: #1e293b; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.4); }
            a { color: #38bdf8; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Chính sách bảo mật</h1>
            <p>Chúng tôi tôn trọng và cam kết bảo mật thông tin cũng như lịch sử trò chuyện của bạn trên hệ thống trợ lý ảo KhangPhan.</p>
            <p>Dữ liệu lịch sử được lưu trữ bảo mật nhằm mục đích duy trì phiên làm việc và cải thiện trải nghiệm cá nhân của người dùng.</p>
            <br>
            <p><a href="/">&larr; Quay lại trang chủ chat</a></p>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
