<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Đăng nhập - AI_KhangPhan</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .login-card { background-color: #1e293b; padding: 32px; border-radius: 16px; border: 1px solid #334155; width: 100%; max-width: 420px; box-shadow: 0 10px 25px rgba(0,0,0,0.4); }
        h2 { text-align: center; margin-bottom: 20px; color: #f8fafc; font-size: 22px; }
        .social-btn { width: 100%; padding: 12px; border-radius: 8px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 10px; font-size: 14px; border: none; margin-bottom: 12px; text-decoration: none; }
        .google-btn { background-color: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; }
        .zalo-btn { background-color: #0068ff; color: #ffffff; }
        .divider { display: flex; align-items: center; text-align: center; margin: 16px 0; color: #64748b; font-size: 13px; }
        .divider::before, .divider::after { content: ''; flex: 1; border-bottom: 1px solid #334155; }
        .divider::before { margin-right: 10px; } .divider::after { margin-left: 10px; }
        .form-group { margin-bottom: 14px; }
        label { display: block; margin-bottom: 6px; font-size: 13px; color: #94a3b8; }
        input { width: 100%; padding: 11px 14px; background-color: #0f172a; border: 1px solid #475569; border-radius: 8px; color: white; font-size: 14px; outline: none; }
        input:focus { border-color: #3b82f6; }
        .submit-btn { width: 100%; padding: 12px; background-color: #3b82f6; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; margin-top: 6px; }
        .submit-btn:hover { background-color: #2563eb; }
        .switch-text { text-align: center; margin-top: 14px; font-size: 13px; color: #94a3b8; }
        .switch-text a { color: #3b82f6; text-decoration: none; cursor: pointer; }
        .error-msg { color: #ef4444; font-size: 13px; text-align: center; margin-bottom: 10px; display: none; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2 id="formTitle">Chào mừng đến với AI</h2>
        <div class="error-msg" id="errorMsg"></div>
        
        <button class="social-btn google-btn" onclick="alert('Tính năng Google OAuth đang phát triển!')">
            <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#EA4335" d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.8 14.8 1 12 1 7.4 1 3.5 3.6 1.6 7.4l3.7 2.9C6.2 7.1 8.9 5 12 5z"/><path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z"/><path fill="#FBBC05" d="M5.3 14.7c-.2-.7-.4-1.5-.4-2.7s.2-2 .4-2.7L1.6 6.4C.6 8.4 0 10.6 0 13s.6 4.6 1.6 6.6l3.7-2.9z"/><path fill="#34A853" d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3.1 0-5.8-2.1-6.7-5.3L1.6 15.9C3.5 19.7 7.4 23 12 23z"/></svg>
            Đăng nhập bằng Google
        </button>

        <button class="social-btn zalo-btn" onclick="alert('Tính năng Zalo Login đang phát triển!')">
            <svg width="18" height="18" viewBox="0 0 48 48"><path fill="#fff" d="M24 4C12.95 4 4 12.95 4 24s8.95 20 20 20 20-8.95 20-20S35.05 4 24 4zm2.14 28.52c-2.41 0-4.48-1.54-5.18-3.72l-.24-.76h-3.41v4.06H14V17.5h4.11v11.02c.51 1.25 1.76 2.08 3.2 2.08h1.83v-1.89h-2.11zm10.74-6.42h-3.56v-3.05h3.56v-1.89h-3.56v-2.9h3.56V17.5h-5.67v11.02h5.67v-1.92z"/></svg>
            Đăng nhập bằng Zalo
        </button>

        <div class="divider">hoặc bằng tài khoản riêng</div>

        <div class="form-group">
            <label>Tên đăng nhập</label>
            <input type="text" id="username" placeholder="Nhập tài khoản...">
        </div>
        <div class="form-group">
            <label>Mật khẩu</label>
            <input type="password" id="password" placeholder="Nhập mật khẩu...">
        </div>
        
        <button class="submit-btn" id="submitBtn" onclick="handleSubmit()">Đăng Nhập</button>
        
        <div class="switch-text" id="switchText">
            Chưa có tài khoản? <a onclick="toggleMode()">Tạo tài khoản ngay</a>
        </div>
    </div>

    <script>
        let isLoginMode = true;
        function toggleMode() {
            isLoginMode = !isLoginMode;
            document.getElementById('formTitle').textContent = isLoginMode ? 'Đăng Nhập AI' : 'Tạo Tài Khoản Mới';
            document.getElementById('submitBtn').textContent = isLoginMode ? 'Đăng Nhập' : 'Đăng Ký Tài Khoản';
            document.getElementById('switchText').innerHTML = isLoginMode ? 
                'Chưa có tài khoản? <a onclick="toggleMode()">Tạo tài khoản ngay</a>' : 
                'Đã có tài khoản? <a onclick="toggleMode()">Đăng nhập</a>';
            document.getElementById('errorMsg').style.display = 'none';
        }

        async function handleSubmit() {
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value.trim();
            const errorMsg = document.getElementById('errorMsg');

            if (!username || !password) {
                errorMsg.textContent = 'Vui lòng nhập đầy đủ thông tin!';
                errorMsg.style.display = 'block';
                return;
            }

            const endpoint = isLoginMode ? '/login' : '/register';
            try {
                const res = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                const data = await res.json();
                if (res.ok) {
                    if (isLoginMode) { window.location.href = '/'; }
                    else { alert(data.message); toggleMode(); }
                } else {
                    errorMsg.textContent = data.message || 'Có lỗi xảy ra!';
                    errorMsg.style.display = 'block';
                }
            } catch (err) {
                errorMsg.textContent = 'Lỗi kết nối máy chủ!';
                errorMsg.style.display = 'block';
            }
        }
    </script>
</body>
</html>
