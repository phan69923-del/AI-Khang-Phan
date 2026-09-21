import os
import time
import base64
import traceback
import certifi
from flask import Flask, request, jsonify, session, send_from_directory, redirect, url_for, render_template
from werkzeug.middleware.proxy_fix import ProxyFix
from google import genai
from google.genai import types
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from authlib.integrations.flask_client import OAuth
from flask import render_template

        
# Lấy chuỗi URI từ biến môi trường trên Render
uri = os.environ.get("MONGO_URI")

# Kết nối MongoDB Atlas (Đã fix SSL và cấu hình chuẩn)
mongo_client = MongoClient(
    uri, 
    server_api=ServerApi('1'),
    tlsCAFile=certifi.where()
)

db = mongo_client["ai_khangphan_db"]
users_collection = db["users"]          
sessions_collection = db["chat_sessions"] 

try:
    mongo_client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(f"Lỗi kết nối MongoDB: {e}")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret_key_khangphan_2026")

# Bật biến này thành True khi muốn đóng web bảo trì, False mở 
IS_MAINTENANCE = True 

@app.before_request
def before_request():
    # Ngoại trừ trang API kiểm tra bảo trì và file tĩnh, còn lại nếu bật bảo trì sẽ ép về trang maintenance.html
    if IS_MAINTENANCE and request.endpoint not in ['check_maintenance', 'static']:
        return render_template('maintenance.html')

# API đường dẫn để script ngầm ở index.html gọi hỏi trạng thái bảo trì
@app.route('/check-maintenance')
def check_maintenance():
    return jsonify({"is_maintenance": IS_MAINTENANCE})

# FIX LỖI PROXY VÀ COOKIE TRÊN RENDER
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['JSON_AS_ASCII'] = False  # Hỗ trợ hiển thị tiếng Việt chuẩn trong JSON response

# Khởi tạo OAuth cho Google Login
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Khởi tạo client Gemini đọc trực tiếp từ biến môi trường Render
api_key = os.environ.get("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=api_key)

TEMP_UPLOAD_FOLDER = "temp_uploads"
os.makedirs(TEMP_UPLOAD_FOLDER, exist_ok=True)

gemini_main_locked_until = 0

def get_current_user_sessions():
    username = session.get("user")
    if not username:
        return {}
    
    user_data = sessions_collection.find_one({"username": username})
    if user_data and "sessions" in user_data:
        return user_data["sessions"]
    else:
        initial_id = f"chat_{int(time.time() * 1000)}"
        default_sessions = {
            initial_id: { 
                "title": "Lời chào", 
                "messages": [{"role": "bot", "text": "Chào bạn! Tôi có thể giúp gì cho bạn hôm nay?"}] 
            }
        }
        sessions_collection.update_one(
            {"username": username},
            {"$set": {"sessions": default_sessions}},
            upsert=True
        )
        return default_sessions

def save_user_sessions(user_sessions):
    username = session.get("user")
    if not username:
        return
    try:
        sessions_collection.update_one(
            {"username": username},
            {"$set": {"sessions": user_sessions}},
            upsert=True
        )
    except Exception as e:
        print(f"Lỗi khi lưu lịch sử chat vào MongoDB: {e}")

@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login_page"))
    return render_template("index.html")

@app.route("/login-page")
def login_page():
    return render_template("login.html")

@app.route("/register-page")
def register_page():
    return render_template("register.html")

# Cho phép cả GET và POST cho login để tránh lỗi 405 nếu gõ trực tiếp /login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    if request.is_json:
        data = request.get_json() or {}
        username = data.get("username") or data.get("email")
        password = data.get("password")
    else:
        username = request.form.get("username") or request.form.get("email")
        password = request.form.get("password")

    if not username or not password:
        if request.is_json:
            return jsonify({"success": False, "error": "Thiếu thông tin đăng nhập!"}), 400
        return render_template("login.html", error="Thiếu thông tin đăng nhập!")

    user_in_db = users_collection.find_one({"username": username})
    if user_in_db and user_in_db.get("password") == password:
        session["user"] = username
        if request.is_json:
            return jsonify({"success": True, "redirect": "/"})
        return redirect(url_for("index"))

    if request.is_json:
        return jsonify({"success": False, "error": "Tài khoản hoặc mật khẩu không chính xác!"}), 401
    
    return render_template("login.html", error="Tài khoản hoặc mật khẩu không chính xác!")

# Cho phép cả GET và POST cho register
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    if request.is_json:
        data = request.get_json() or {}
        username = data.get("username") or data.get("email")
        password = data.get("password")
    else:
        username = request.form.get("username") or request.form.get("email")
        password = request.form.get("password")

    if not username or not password:
        if request.is_json:
            return jsonify({"success": False, "error": "Thiếu thông tin đăng ký!"}), 400
        return render_template("register.html", error="Thiếu thông tin đăng ký!")

    existing_user = users_collection.find_one({"username": username})
    if existing_user:
        if request.is_json:
            return jsonify({"success": False, "error": "Tài khoản này đã tồn tại!"}), 400
        return render_template("register.html", error="Tài khoản này đã tồn tại!")

    users_collection.insert_one({"username": username, "password": password})
    session["user"] = username
    
    if request.is_json:
        return jsonify({"success": True, "redirect": "/"})
    return redirect(url_for("index"))

@app.route("/login/google")
def login_google():
    redirect_uri = url_for("google_callback", _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/login/google/callback")
def google_callback():
    try:
        code = request.args.get("code")
        if not code:
            return "Không tìm thấy mã xác thực từ Google", 400
        
        token = google.fetch_access_token(
            code=code,
            redirect_uri=url_for("google_callback", _external=True)
        )
        
        resp = google.get("https://openidconnect.googleapis.com/v1/userinfo", token=token)
        user_info = resp.json()
        email = user_info.get("email") or user_info.get("name")
        
        if not users_collection.find_one({"username": email}):
            users_collection.insert_one({"username": email, "auth_type": "google"})
            
        session["user"] = email
        return redirect("/")
    except Exception as e:
        return f"Lỗi xác thực Google: {str(e)}"

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login_page"))

@app.route("/chat", methods=["POST"])
def chat():
    global gemini_main_locked_until
    temp_file_path = None
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

        gemini_contents = []
        for msg in user_sessions[chat_id]["messages"]:
            role = "user" if msg["role"] == "user" else "model"
            content_parts = []
            if "image" in msg and msg["image"]:
                try:
                    if msg["image"].startswith("data:image"):
                        header, encoded = msg["image"].split(",", 1)
                        mime_type = header.split(";")[0].split(":")[1]
                        image_bytes = base64.b64decode(encoded)
                        content_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
                except Exception:
                    pass
            if "text" in msg and msg["text"]:
                content_parts.append(types.Part.from_text(text=msg["text"]))
            
            if content_parts:
                gemini_contents.append(types.Content(role=role, parts=content_parts))

        current_new_parts = []
        if image_data:
            try:
                header, encoded = image_data.split(",", 1)
                mime_type = header.split(";")[0].split(":")[1]
                image_bytes = base64.b64decode(encoded)
                file_ext = mime_type.split("/")[-1]
                if file_ext not in ["png", "jpeg", "jpg", "webp"]:
                    file_ext = "jpg"
                temp_filename = f"img_{int(time.time() * 1000)}.{file_ext}"
                temp_file_path = os.path.join(TEMP_UPLOAD_FOLDER, temp_filename)
                with open(temp_file_path, "wb") as f:
                    f.write(image_bytes)
                current_new_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
            except Exception as e:
                print(f"Lỗi xử lý ảnh tạm: {e}")

        if user_message:
            current_new_parts.append(types.Part.from_text(text=user_message))
        else:
            current_new_parts.append(types.Part.from_text(text="Hãy mô tả hoặc phân tích bức ảnh này giúp tôi."))

        gemini_contents.append(types.Content(role="user", parts=current_new_parts))

        if user_sessions[chat_id]["title"] == "Cuộc trò chuyện mới":
            try:
                title_prompt = user_message if user_message else "Phân tích hình ảnh"
                title_response = gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=(
                        f"Nhiệm vụ duy nhất: Đặt tiêu đề tối đa 5 từ cho nội dung: '{title_prompt}'. "
                        "CHỈ TRẢ VỀ ĐÚNG TỪ KHÓA TIÊU ĐỀ, tuyệt đối không viết thêm bất kỳ câu dẫn dắt, giải thích hay dấu sao nào."
                    ),
                )
                if title_response and title_response.text:
                    new_title = title_response.text.strip().replace('"', "").replace('*', "").replace('#', "")
                    if new_title:
                        words = new_title.split()
                        if len(words) > 6:
                            new_title = " ".join(words[:5])
                        user_sessions[chat_id]["title"] = new_title
            except Exception as e:
                print(f"Lỗi tạo tiêu đề: {e}")
                user_sessions[chat_id]["title"] = "Cuộc trò chuyện mới"

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

        response = None
        bot_response = ""
        current_time = time.time()
        
        is_main_locked = current_time < gemini_main_locked_until

        if not is_main_locked:
            try:
                response = gemini_client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=gemini_contents,
                    config=config,
                )
                bot_response = response.text
            except Exception as e:
                print(f"⚠️ Model chính lỗi: {e}")
                gemini_main_locked_until = time.time() + 60
                is_main_locked = True

        if is_main_locked:
            try:
                response = gemini_client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=gemini_contents,
                    config=config,
                )
                bot_response = response.text
            except Exception as e2:
                print(f"⚠️ Model dự phòng lỗi: {e2}")
                bot_response = "⚠️ Hệ thống AI_KhangPhan đang bận. Vui lòng đợi 30 giây rồi thử lại nhé!😥"

        is_searched = False
        search_queries = []
        if response is not None:
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

        save_user_sessions(user_sessions)

        return jsonify({
            "response": bot_response,
            "sessions": user_sessions,
            "searched": is_searched,
            "queries": search_queries
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                print(f"Lỗi khi xóa file tạm: {e}")

@app.route("/privacy")
def privacy_policy():
    return "<h1>Chính sách bảo mật AI KhangPhan</h1>"

@app.route("/terms")
def terms_of_service():
    return "<h1>Điều khoản dịch vụ AI KhangPhan</h1>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
