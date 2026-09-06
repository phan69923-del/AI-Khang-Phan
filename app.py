from flask import Flask, render_template_string, request, session, redirect, url_for
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Danh sách phiên chat lưu trữ tạm thời trong bộ nhớ
chat_sessions = {}

# Giao diện HTML tích hợp sẵn
CHAT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>AI Chat App</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; display: flex; height: 100vh; }
        .sidebar { width: 260px; background: #202123; color: white; display: flex; flex-direction: column; padding: 10px; }
        .sidebar a { color: white; text-decoration: none; padding: 10px; margin-bottom: 5px; border-radius: 5px; display: block; background: #2a2b32; }
        .sidebar a:hover { background: #343541; }
        .main { flex: 1; display: flex; flex-direction: column; background: #ffffff; }
        .chat-box { flex: 1; padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 15px; }
        .message { padding: 12px 16px; border-radius: 8px; max-width: 70%; line-height: 1.5; }
        .user { background: #007bff; color: white; align-self: flex-end; }
        .bot { background: #e9ecef; color: black; align-self: flex-start; }
        .input-box { display: flex; padding: 15px; background: #fff; border-top: 1px solid #ddd; }
        .input-box input { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 4px; outline: none; }
        .input-box button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; margin-left: 10px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h3>Lịch sử Chat</h3>
        <a href="{{ url_for('new_chat') }}">+ Cuộc trò chuyện mới</a>
        <hr style="border-color: #444;">
        <div style="overflow-y: auto; flex: 1;">
            {% for s_id in sessions.keys() %}
                <a href="{{ url_for('switch_chat', session_id=s_id) }}">Phiên chat {{ s_id[:4] }}</a>
            {% endfor %}
        </div>
        <a href="{{ url_for('logout') }}" style="background: #dc3545; text-align: center;">Đăng xuất</a>
    </div>
    
    <div class="main">
        <div class="chat-box">
            {% if session.get('user') and session.get('current_session') in sessions %}
                {% for msg in sessions[session['current_session']] %}
                    <div class="message {{ msg.role }}">{{ msg.text }}</div>
                {% endfor %}
            {% else %}
                <div class="message bot">Chào bạn! Hãy gửi tin nhắn để bắt đầu trò chuyện.</div>
            {% endif %}
        </div>
        
        <form class="input-box" method="POST" action="{{ url_for('send_message') }}">
            <input type="text" name="message" placeholder="Nhập tin nhắn của bạn..." required autocomplete="off">
            <button type="submit">Gửi</button>
        </form>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # Đảm bảo người dùng có một phiên chat hiện tại hợp lệ
    current_s_id = session.get('current_session')
    if not current_s_id or current_s_id not in chat_sessions:
        if chat_sessions:
            session['current_session'] = list(chat_sessions.keys())[0]
        else:
            return redirect(url_for('new_chat'))
            
    return render_template_string(CHAT_HTML_TEMPLATE, sessions=chat_sessions)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        if username:
            session['user'] = username
            if not chat_sessions:
                # Tạo phiên chat đầu tiên nếu chưa có
                import uuid
                s_id = str(uuid.uuid4())
                chat_sessions[s_id] = []
                session['current_session'] = s_id
            return redirect(url_for('index'))
            
    return '''
        <form method="POST" style="max-width: 300px; margin: 100px auto; font-family: Arial;">
            <h2>Đăng nhập</h2>
            <input type="text" name="username" placeholder="Nhập tên của sếp..." required style="width: 100%; padding: 8px; margin-bottom: 10px;">
            <button type="submit" style="width: 100%; padding: 8px; background: #007bff; color: white; border: none;">Vào ứng dụng</button>
        </form>
    '''

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('current_session', None)
    return redirect(url_for('login'))

@app.route('/new_chat')
def new_chat():
    if 'user' not in session:
        return redirect(url_for('login'))
    import uuid
    s_id = str(uuid.uuid4())
    chat_sessions[s_id] = []
    session['current_session'] = s_id
    return redirect(url_for('index'))

@app.route('/switch/<session_id>')
def switch_chat(session_id):
    if session_id in chat_sessions:
        session['current_session'] = session_id
    return redirect(url_for('index'))

@app.route('/send', methods=['POST'])
def send_message():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    user_msg = request.form.get('message')
    current_s_id = session.get('current_session')
    
    if user_msg and current_s_id in chat_sessions:
        # Lưu tin nhắn của người dùng
        chat_sessions[current_s_id].append({'role': 'user', 'text': user_msg})
        
        # Giả lập AI phản hồi (Sếp có thể thay thế đoạn này bằng gọi API OpenAI/Gemini tùy ý)
        bot_reply = f"AI đã nhận được câu hỏi: '{user_msg}'"
        chat_sessions[current_s_id].append({'role': 'bot', 'text': bot_reply})
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
