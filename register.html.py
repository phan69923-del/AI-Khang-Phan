@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # Thêm logic lưu tài khoản vào database của bạn ở đây
        return redirect(url_for('login')) # Hoặc trang login của bạn
    return render_template('register.html')