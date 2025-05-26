
from flask import Flask, render_template, request, redirect, session, send_file
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'secret_key_for_session'

# In-memory user and block data
users = {}
user_blocks = {}

# Create empty data for all blocks (A–Z), 7 floors each
def create_empty_block_data():
    return {chr(65 + i): [False] * 7 for i in range(26)}

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['logged_in'] = True
            session['username'] = username
            if username not in user_blocks:
                user_blocks[username] = create_empty_block_data()
            return redirect('/dashboard')
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            return render_template('register.html', error="Username already exists")
        users[username] = password
        user_blocks[username] = create_empty_block_data()
        return redirect('/')
    return render_template('register.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('logged_in'):
        return redirect('/')

    username = session['username']
    blocks = user_blocks.get(username, create_empty_block_data())
    user_blocks[username] = blocks  # ensure saved

    if request.method == 'POST':
        block = request.form.get('block')
        floors = request.form.getlist('floors')
        if block:
            blocks[block] = [False] * 7
            for f in floors:
                try:
                    idx = int(f)
                    if 0 <= idx < 7:
                        blocks[block][idx] = True
                except ValueError:
                    pass

        # Save to Excel
        data_rows = []
        for blk, floors in blocks.items():
            for i, done in enumerate(floors):
                data_rows.append({
                    'Username': username,
                    'Block': blk,
                    'Floor': i,
                    'Completed': done
                })

        df = pd.DataFrame(data_rows)
        excel_file = f'service_data_{username}.xlsx'
        df.to_excel(excel_file, index=False, engine='openpyxl')

    completed_blocks = {block: all(floors) for block, floors in blocks.items()}

    return render_template(
        'dashboard.html',
        block_data=blocks,
        completed_blocks=completed_blocks,
        enumerate=enumerate
    )

@app.route('/download')
def download():
    if not session.get('logged_in'):
        return redirect('/')
    username = session['username']
    filename = f'service_data_{username}.xlsx'
    if os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    return "File not found", 404

@app.route('/report')
def report():
    if not session.get('logged_in'):
        return redirect('/')

    username = session['username']
    filename = f'service_data_{username}.xlsx'

    if os.path.exists(filename):
        df = pd.read_excel(filename, engine='openpyxl')

        # Summary: progress per block
        summary = []
        blocks = df['Block'].unique()
        for blk in sorted(blocks):
            block_df = df[df['Block'] == blk]
            completed_floors = block_df['Completed'].sum()
            percent = int((completed_floors / 7) * 100)
            summary.append({
                'block': blk,
                'completed_floors': int(completed_floors),
                'percent': percent
            })

        return render_template('report.html', block_summary=summary)

    return "No report found. Please save some data first.", 404

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
