import os
import json

MEMORY_DIR = "khangphan_memory"
MEMORY_FILE = os.path.join(MEMORY_DIR, "chat_database.json")

def init_memory():
    """Khởi tạo thư mục và file database nếu chưa có"""
    if not os.path.exists(MEMORY_DIR):
        os.makedirs(MEMORY_DIR)
    if not os.path.exists(MEMORY_FILE):
        default_data = {"sessions": {}, "histories": {}}
        save_memory_data(default_data)

def load_memory_data():
    """Đọc toàn bộ dữ liệu lịch sử từ file JSON"""
    init_memory()
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"sessions": {}, "histories": {}}

def save_memory_data(data):
    """Lưu toàn bộ dữ liệu vào file JSON"""
    if not os.path.exists(MEMORY_DIR):
        os.makedirs(MEMORY_DIR)
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)