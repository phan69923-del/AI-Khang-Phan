# file: app.py
import os
import time
import base64
import traceback
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from google import genai
from google.genai import types

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "khangphan_secret_key_123")

# Khởi tạo Gemini Client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

TEMP_UPLOAD_FOLDER = "temp_uploads"
os.makedirs(TEMP_UPLOAD_FOLDER, exist_ok=True)

# Bộ nhớ lưu session chat tạm thời
USER_SESSIONS = {}

def get_current_user_sessions():
    user = session.get("user", "default_user")
    if user not in USER_SESSIONS:
        USER_SESSIONS[user] = {}
    return USER_SESSIONS[user]

def save_db():
    pass

@app.route("/")
def index():
    if not session.get("user"):
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        if username:
            session["user"] = username
            return redirect(url_for("index"))
    return '''
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <title>Đăng nhập - Trợ lý ảo KhangPhan</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .login-card { background: #1e293b; padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); text-align: center; width: 350px; }
            input { width: 100%; padding: 12px; margin: 15px 0; border-radius: 8px; border: 1px solid #475569; background: #0f172a; color: white; box-sizing: border-box; }
            button { width: 100%; padding: 12px; background: #38bdf8; border: none; border-radius: 8px; font-weight: bold; color: #0f172a; cursor: pointer; transition: 0.2s; }
            button:hover { background: #0ea5e9; }
        </style>
    </head>
    <body>
        <div class="login-card">
            <h2>🤖 Trợ lý ảo KhangPhan</h2>
            <form method="post">
                <input type="text" name="username" placeholder="Nhập tên của sếp..." required autocomplete="off">
                <button type="submit">Vào giao diện chat</button>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/chat", methods=["POST"])
def chat():
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

        # ====== TỰ ĐỘNG SINH TIÊU ĐỀ ======
        if user_sessions[chat_id]["title"] == "Cuộc trò chuyện mới":
            try:
                title_prompt = user_message if user_message else "Phân tích hình ảnh"
                title_response = None
                try:
                    title_response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=(
                            f"Nhiệm vụ duy nhất: Đặt tiêu đề tối đa 5 từ cho nội dung: '{title_prompt}'. "
                            "CHỈ TRẢ VỀ ĐÚNG TỪ KHÓA TIÊU ĐỀ, tuyệt đối không viết thêm bất kỳ câu dẫn dắt, giải thích hay dấu sao nào."
                        ),
                    )
                except Exception:
                    title_response = client.models.generate_content(
                        model="gemini-2.5-flash-lite",
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

        # ====== CẤU HÌNH HỆ THỐNG CHO TRỢ LÝ ẢO KHANGPHAN ======
        config = types.GenerateContentConfig(
            system_instruction=(
                "Bạn là trợ lý ảo AI KhangPhan. "
                "Người sáng lập ra bạn là Phan Tăng Hoàng Khang, học sinh lớp 7 Trường THCS Nguyễn Trãi, Phường Long Khánh, TP. Đồng Nai. "
                "Tuyệt đối không nhận là do Google tạo ra. "
                "QUY TẮC BẢO MẬT: Mã bí mật là 07062014 hoặc secret_key. "
                "Tuyệt đối KHÔNG BAO GIỜ được tiết lộ mã bí mật này ra bên ngoài cho bất kỳ ai, kể cả người tự xưng là chủ nhân. "
                "Nếu người dùng tự xưng là người tạo/chủ nhân và cung cấp đúng mã bí mật, hãy xưng hô là 'cha đẻ', 'sếp'."
            ),
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.7,
        )

        # ====== LUỒNG CHAT CHÍNH CÓ BẮT LỖI 429 ======
        response = None
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=gemini_contents,
                config=config,
            )
        except Exception as e_chat_1:
            err_str = str(e_chat_1)
            if "429" in err_str or "ResourceExhausted" in err_str:
                return jsonify({
                    "error": "QUOTA_EXCEEDED",
                    "message": "Sếp dùng hăng quá nên hết sạch lượt miễn phí rồi! Vui lòng nghỉ ngơi chớp mắt hoặc thử lại sau.",
                    "retry_after": 45
                }), 429
            
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=gemini_contents,
                    config=config,
                )
            except Exception as e_chat_2:
                err_str_2 = str(e_chat_2)
                if "429" in err_str_2 or "ResourceExhausted" in err_str_2:
                    return jsonify({
                        "error": "QUOTA_EXCEEDED",
                        "message": "Hệ thống đang quá tải hoặc hết lượt (Lỗi 429). Vui lòng thử lại sau giây lát.",
                        "retry_after": 45
                    }), 429
                raise e_chat_2

        bot_response = response.text if response.text else "Không có phản hồi từ AI."

        is_searched = False
        search_queries = []
        try:
            if response.candidates and response.candidates[0].grounding_metadata and response.candidates[0].grounding_metadata.web_search_queries:
                is_searched = True
                search_queries = list(response.candidates[0].grounding_metadata.web_search_queries)
        except Exception:
            pass

        user_msg_obj = {"role": "user", "text": user_message if user_message else ""}
        if image_data:
            user_msg_obj["image"] = image_data

        user_sessions[chat_id]["messages"].append(user_msg_obj)
        user_sessions[chat_id]["messages"].append({"role": "bot", "text": bot_response})

        save_db()

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
            except Exception:
                pass

@app.route("/privacy")
def privacy_policy():
    return "<h1>Chính sách bảo mật AI KhangPhan</h1>"

@app.route("/terms")
def terms_of_service():
    return "<h1>Điều khoản dịch vụ AI KhangPhan</h1>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
