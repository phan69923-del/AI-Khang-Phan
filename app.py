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
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "khangphan_secret_key_ai")

# Cho phép chạy OAuth2 qua HTTP khi test
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# 2. Cấu hình Gemini API và Hệ thống định danh AI
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)

system_prompt = (
    "Bạn là AI KhangPhan, một trợ lý ảo thông minh do bạn Khang Phan "
    "(Phan Tăng Hoàng Khang, học sinh lớp 7 Trường THCS Nguyễn Trãi, Phường Long Khánh, Thành Phố Đồng Nai) phát triển. "
    "Hãy luôn xưng hô thân thiện, thông minh và tự hào về người tạo ra mình."
)

generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}

# Sử dụng model gemini-3-flash-preview chính xác nhất
model = genai.GenerativeModel(
    model_name="gemini-3-flash-preview", 
    generation_config=generation_config,
    system_instruction=system_prompt
)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
client_secrets_file = os.path.join(os.path.dirname(__file__), "client_secret.json")

def get_google_flow():
    if not os.path.exists(client_secrets_file):
        return None
    return Flow.from_client_secrets_file(
        client_secrets_file=client_secrets_file,
        scopes=[
            "https://googleapis.com", 
            "https://googleapis.com", 
            "openid"
        ],
        redirect_uri="https://onrender.com"
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
    session["state"] = state
    return redirect(authorization_url)

@app.route("/callback")
def callback():
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

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    session["email"] = id_info.get("email")
    
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- ĐOẠN XỬ LÝ CHAT MỚI ĐỒNG BỘ 100% VỚI INDEX.HTML ---

@app.route("/chat", methods=["POST"])
def chat():
    if "google_id" not in session:
        return jsonify({"error": "Chưa đăng nhập!"}), 401

    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    chat_id = data.get("chat_id")  # Nhận đúng chat_id từ JavaScript gửi lên
    
    if not user_message or not chat_id:
        return jsonify({"error": "Thiếu tin nhắn hoặc mã đoạn chat!"}), 400

    if "conversations" not in session:
        session["conversations"] = {}
    
    # Nếu chat_id mới hoàn toàn, khởi tạo lịch sử rỗng cho nó
    if chat_id not in session["conversations"]:
        session["conversations"][chat_id] = {
            "title": user_message[:15] + "..." if len(user_message) > 15 else user_message,
            "history": []
        }

    try:
        # Lấy lịch sử chat hiện tại để gửi cho Gemini ghi nhớ ngữ cảnh
        current_history = session["conversations"][chat_id]["history"]
        
        chat_session = model.start_chat(history=current_history)
        response = chat_session.send_message(user_message)
        
        # Cập nhật cả tin nhắn user và AI vào session
        current_history.append({"role": "user", "parts": [user_message]})
        current_history.append({"role": "model", "parts": [response.text]})
        
        session["conversations"][chat_id]["history"] = current_history
        session.modified = True
        
        return jsonify({
            "response": response.text,
            "suggested_title": session["conversations"][chat_id]["title"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/rename_chat", methods=["POST"])
def rename_chat():
    if "google_id" not in session:
        return jsonify({"error": "Chưa đăng nhập!"}), 401
        
    data = request.get_json() or {}
    chat_id = data.get("chat_id")
    new_title = data.get("title", "").strip()
    
    if not chat_id or not new_title:
        return jsonify({"error": "Thông tin không hợp lệ!"}), 400
        
    if "conversations" in session and chat_id in session["conversations"]:
        session["conversations"][chat_id]["title"] = new_title
        session.modified = True
        return jsonify({"success": True})
        
    return jsonify({"error": "Không tìm thấy đoạn chat!"}), 404

@app.route("/get_chats", methods=["GET"])
def get_chats():
    if "google_id" not in session:
        return jsonify({"error": "Chưa đăng nhập!"}), 401
    return jsonify(session.get("conversations", {}))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
