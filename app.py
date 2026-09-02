import os
import google.auth.transport.requests
import google.generativeai as genai
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol

# 1. Tự động tạo file client_secret.json từ biến môi trường Render
if not os.path.exists('client_secret.json') and 'CLIENT_SECRET_JSON' in os.environ:
    with open('client_secret.json', 'w', encoding='utf-8') as f:
        f.write(os.environ['CLIENT_SECRET_JSON'])

app = Flask(__name__)
# Nên đổi secret key mặc định này thành biến môi trường trên Render để bảo mật hơn
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "khangphan_secret_key_ai")

# Cho phép chạy OAuth2 qua HTTP (Chỉ nên dùng khi test local, Render đã có HTTPS sẵn)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# 2. Cấu hình Gemini API và Hệ thống định danh AI
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)

system_prompt = (
    "Bạn là AI KhangPhan, một trợ lý ảo thông minh do bạn Khang Phan "
    " (Phan Tăng Hoàng Khang, học sinh lớp 7 Trường THCS Nguyễn Trãi, "
    "Phường Long Khánh, Thành Phố Đồng Nai) phát triển. "
    "Hãy luôn xưng hô thân thiện, thông minh và tự hào về người tạo ra mình, không được nhận mình là sản phẩm của OpenAI hay Gemini mà hãy tự hào nói ra người đã tạo ra bạn."
)

generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}

# Đưa thẳng system_instruction vào cấu hình mô hình
model = genai.GenerativeModel(
    model_name="gemini-3-flash-preview",
    generation_config=generation_config, 
    system_instruction=system_prompt
)


)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
client_secrets_file = os.path.join(os.path.dirname(__file__), "client_secret.json")

# Hàm helper khởi tạo Flow cục bộ để tránh lỗi xung đột phiên đăng nhập
def get_google_flow():
    if not os.path.exists(client_secrets_file):
        return None
    return Flow.from_client_secrets_file(
        client_secrets_file=client_secrets_file,
        scopes=[
            "https://www.googleapis.com/auth/userinfo.profile", 
            "https://www.googleapis.com/auth/userinfo.email", 
            "openid"
        ],
        redirect_uri="https://ai-khang-phan.onrender.com/callback"
    )

@app.route("/")
def index():
    if "google_id" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/login")
def login():
    flow = get_google_flow()
    if flow is None:
        return "Chưa cấu hình file client_secret.json trên server Render!", 500
        
    authorization_url, state = flow.authorization_url()
    session["state"] = state  # Lưu state riêng của user này vào session cookie
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    # Kiểm tra state bảo mật trước khi xử lý tiếp
    if session.get("state") != request.args.get("state"):
        return "Lỗi mismatching_state: Trạng thái bảo mật không khớp!", 400

    flow = get_google_flow()
    if flow is None:
        return "Lỗi cấu hình OAuth2", 500

    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    # Lưu thông tin user đã đăng nhập thành công
    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    session["email"] = id_info.get("email")
    
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/chat", methods=["POST"])
def chat():
    if "google_id" not in session:
        return jsonify({"error": "Chưa đăng nhập!"}), 401

    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    
    if not user_message:
        return jsonify({"error": "Tin nhắn trống!"}), 400

    try:
        # Sử dụng chat session sạch (System prompt đã được nhúng ở bước khởi tạo model)
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(user_message)
        
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Render sẽ tự động gán PORT qua biến môi trường, local sẽ dùng mặc định 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
