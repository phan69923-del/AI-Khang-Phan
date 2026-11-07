import sys
import os

# Thêm thư mục gốc vào đường dẫn hệ thống để Vercel tìm thấy app.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as application
