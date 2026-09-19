import os
import time
import base64
import traceback
from flask import Flask, request, jsonify, session, send_from_directory, redirect, url_for
from google import genai
from google.genai import types
from pymongo import MongoClient
from pymongo.server_api import ServerApi

# Lấy chuỗi URI trực tiếp từ biến môi trường trên Render
uri = os.environ.get("MONGO_URI")

# Kết nối MongoDB Atlas
client = MongoClient(uri, server_api=ServerApi('1'))

# Kiểm tra kết nối thử xem có mượt không
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(f"Lỗi kết nối MongoDB: {e}")


app = Flask(__name__)
app.secret_key = "secret_key"

# Khởi tạo client Gemini đọc trực tiếp từ biến môi trường Render
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

TEMP_UPLOAD_FOLDER = "temp_uploads"
os.makedirs(TEMP_UPLOAD_FOLDER, exist_ok=True)

DATABASE_SESSIONS = {}

def get_current_user_sessions():
    user = session.get("user", "default_user")
    if user not in DATABASE_SESSIONS:
        DATABASE_SESSIONS[user] = {}
    return DATABASE_SESSIONS[user]

def save_db():
    pass

def save_memory_data(data=None):
    """Hàm lưu trữ bộ nhớ phụ trợ (tránh lỗi name 'save_memory_data' is not defined)"""
    try:
        pass
    except Exception as e:
        print(f"Lỗi khi lưu bộ nhớ: {e}")
        
@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/chat", methods=["POST"])
def chat():
    temp_file_path = None
    try:
        if "user" not in session:
            session["user"] = "khangphan_admin"

        user = session.get("user")
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

        # TỰ ĐỘNG SINH TIÊU ĐỀ
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
                except Exception as e_title_429:
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

        # CẤU HÌNH TRỢ LÝ ẢO KHANGPHAN
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

        # LUỒNG CHAT CHÍNH
        response = None
        bot_response = ""

        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=gemini_contents,
                config=config,
            )
            bot_response = response.text
        except Exception as e_chat_429:
            try:
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=gemini_contents,
                    config=config,
                )
                bot_response = response.text
            except Exception as e_all_429:
                bot_response = "⚠️ Hệ thống AI_KhangPhan đang bận xử lý quá nhiều yêu cầu cùng lúc. Bạn vui lòng đợi AI hồi máu khoảng 30 giây rồi thử lại nhé!😾"

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
        
        save_memory_data(user_sessions[chat_id])
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
