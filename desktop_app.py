import webview

def main():
    target_url = "https://ai-khang-phan.onrender.com" 
    window = webview.create_window('AI_KhangPhan Desktop', target_url, width=1280, height=768)
    # Bật debug=True để dùng được F12 trên app
    webview.start(debug=True)

if __name__ == '__main__':
    main()