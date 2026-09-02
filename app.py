import os

# Tự động tạo file client_secret.json từ biến môi trường trên Render trước khi Flask khởi tạo
if not os.path.exists('client_secret.json') and 'CLIENT_SECRET_JSON' in os.environ:
    with open('client_secret.json', 'w', encoding='utf-8') as f:
        f.write(os.environ['CLIENT_SECRET_JSON'])

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
import google.generativeai as genai
import requests

app = Flask(__name__)
app.secret_key = "khangphan_secret_key_ai"

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "ĐIỀN_API_KEY_GEMINI_VÀO_ĐÂY_NẾU_CẦN")
genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}
model = genai.GenerativeModel(model_name="gemini-2.5-flash", generation_config=generation_config)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "ĐIỀN_CLIENT_ID_CỦA_BRO")
client_secrets_file = os.path.join(os.path.dirname(__file__), "client_secret.json")

try:
    flow = Flow.from_client_secrets_file(
        client_secrets_file=client_secrets_file,
        scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
        redirect_uri="https://ai-khang-phan.onrender.com/callback"
    )
except Exception:
    flow = None

@app.route("/")
def index():
    if "google_id" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/login")
def login():
    if flow is None:
        return "Chưa cấu hình file client_secret.json trên server Render!", 500
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)
    if session["state"] != request.args.get("state"):
        return "Lỗi mismatching_state: Trạng thái bảo mật không khớp!", 400

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

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

    data = request.get_json()
    user_message = data.get("message", "")
    
    if not user_message:
        return jsonify({"error": "Tin nhắn trống!"}), 400

    try:
        system_prompt = (
            "Bạn là AI KhangPhan, một trợ lý ảo thông minh do bạn Khang Phan "
            "(Phan Tăng Hoàng Khang, học sinh lớp 7 Trường THCS Nguyễn Trãi, Phường Long Khánh, Tỉnh Đồng Nai) phát triển. "
            "Hãy luôn xưng hô thân thiện, thông minh và tự hào về người tạo ra mình."
        )
        
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(f"{system_prompt}\n\nNgười dùng hỏi: {user_message}")
        
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
