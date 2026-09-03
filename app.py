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

        /* Chế độ Sáng (Light Mode) */
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

        /* Sidebar với hiệu ứng trượt mượt mà và an toàn cho mobile */
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
            gap: 10px;
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

        .history-text {
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
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

        /* Main Chat Area với hiệu ứng co giãn đều */
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

        /* Nút toggle mở/đóng sidebar dùng font icon */
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

        /* Responsive cho điện thoại (Màn hình nhỏ hơn 768px) */
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
    <!-- Sidebar -->
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
            <div class="history-item active">
                <i class="fa-regular fa-message"></i>
                <span class="history-text">Đoạn chat mẫu đầu tiên</span>
            </div>
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

    <!-- Main Chat Area -->
    <div class="main-chat" id="mainChat">
        <div class="chat-header">
            <button class="sidebar-toggle-btn" onclick="toggleSidebar()">
                <i id="toggleIcon" class="fa-solid fa-bars"></i>
            </button>
            <span>Trò chuyện cùng AI KhangPhan</span>
        </div>

        <div class="chat-messages" id="chatMessages">
            <div class="message bot">
                Chào bạn! Tôi có thể giúp gì cho bạn hôm nay?
            </div>
        </div>

        <div class="chat-input-container">
            <div class="chat-input-box">
                <textarea id="userInput" placeholder="Nhập tin nhắn..." rows="1" oninput="autoResize(this)" onkeydown="checkEnter(event)"></textarea>
                <button class="send-btn" onclick="sendMessage()"><i class="fa-solid fa-paper-plane"></i></button>
            </div>
        </div>
    </div>

    <script>
        let currentChatId = 1;

        // Hàm hiệu ứng đóng mở Sidebar linh hoạt cho cả PC và Mobile
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            const mainChat = document.getElementById('mainChat');
            const toggleIcon = document.getElementById('toggleIcon');

            if (window.innerWidth <= 768) {
                sidebar.classList.toggle('mobile-open');
                if (sidebar.classList.contains('mobile-open')) {
                    toggleIcon.className = "fa-solid fa-xmark";
                } else {
                    toggleIcon.className = "fa-solid fa-bars";
                }
            } else {
                sidebar.classList.toggle('closed');
                mainChat.classList.toggle('expanded');
                if (sidebar.classList.contains('closed')) {
                    toggleIcon.className = "fa-solid fa-arrow-right";
                } else {
                    toggleIcon.className = "fa-solid fa-bars";
                }
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

        function startNewChat() {
            document.getElementById('chatMessages').innerHTML = `
                <div class="message bot">Chào bạn! Tôi có thể giúp gì cho bạn hôm nay?</div>
            `;
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

            input.value = '';
            input.style.height = 'auto';
            chatMessages.scrollTop = chatMessages.scrollHeight;

            const botMsg = document.createElement('div');
            botMsg.className = 'message bot';
            botMsg.textContent = "Đang suy nghĩ...";
            chatMessages.appendChild(botMsg);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            // Cơ chế thử lại tự động ở phía Client nếu gặp lỗi mạng hoặc 503
            let retries = 3;
            let success = false;

            while (retries > 0 && !success) {
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: messageText, chat_id: currentChatId })
                    });

                    const data = await response.json();
                    
                    if (response.ok && data.response) {
                        botMsg.textContent = data.response;
                        success = true;
                    } else {
                        throw new Error(data.error || "Server quá tải");
                    }
                } catch (error) {
                    retries--;
                    if (retries === 0) {
                        botMsg.textContent = "Hệ thống đang quá tải tạm thời (Lỗi 503). Vui lòng thử lại sau ít phút!";
                    } else {
                        botMsg.textContent = `Đang thử kết nối lại lần thứ ${4 - retries}...`;
                        await new Promise(resolve => setTimeout(resolve, 2000)); // Đợi 2 giây rồi thử lại
                    }
                }
            }
            
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    </script>
</body>
</html>
