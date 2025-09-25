from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import sqlite3, os, csv, io
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pandas as pd

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'data.db')

app = Flask(__name__)
app.secret_key = 'replace-with-a-secret-key'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # users: id, username, password_hash, role, teacher_id (for students)
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT,
        role TEXT,
        full_name TEXT,
        teacher_id INTEGER,
        group_name TEXT
    )""")
    # entries: id, student_id, date, wake_time, prayer (csv), sport, food_notes, study_notes, community_notes, sleep_time, created_at
    c.execute("""CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        date TEXT,
        wake_time TEXT,
        prayer TEXT,
        sport TEXT,
        food_notes TEXT,
        study_notes TEXT,
        community_notes TEXT,
        sleep_time TEXT,
        created_at TEXT
    )""")
    conn.commit()
    # create default users if not exist
    c.execute("SELECT COUNT(*) as cnt FROM users")
    if c.fetchone()['cnt'] == 0:
        c.execute("INSERT INTO users (username, password_hash, role, full_name) VALUES (?,?,?,?)",
                  ('admin', generate_password_hash('admin123'), 'admin', 'Administrator')) 
        c.execute("INSERT INTO users (username, password_hash, role, full_name) VALUES (?,?,?,?)",
                  ('guru1', generate_password_hash('guru123'), 'guru', 'Guru Pembimbing 1')) 
        # create a sample student assigned to guru1
        c.execute("INSERT INTO users (username, password_hash, role, full_name, teacher_id) VALUES (?,?,?,?,?)",
                  ('siswa1', generate_password_hash('siswa123'), 'siswa', 'Siswa Contoh', 2))
        conn.commit()
    conn.close()

init_db()

# helpers
def current_user():
    uid = session.get('user_id')
    if not uid: return None
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id=?', (uid,))
    row = c.fetchone()
    conn.close()
    return row

@app.route('/')
def index():
    user = current_user()
    return render_template('index.html', user=user)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db(); c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username=?', (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            return redirect(url_for('dashboard'))
        flash('Login gagal. Periksa username/password.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    conn = get_db(); c = conn.cursor()
    if user['role'] == 'siswa':
        # show only student's own entries
        c.execute('SELECT * FROM entries WHERE student_id=? ORDER BY date DESC', (user['id'],))
        rows = c.fetchall()
        conn.close()
        return render_template('dashboard_siswa.html', user=user, entries=rows)
    elif user['role'] == 'guru':
        # show students assigned to this teacher
        c.execute('SELECT * FROM users WHERE role="siswa" AND teacher_id=?', (user['id'],))
        students = c.fetchall()
        # show recent entries for those students
        student_ids = [s['id'] for s in students]
        entries = []
        if student_ids:
            q = 'SELECT e.*, u.full_name FROM entries e JOIN users u ON e.student_id=u.id WHERE e.student_id IN ({seq}) ORDER BY e.date DESC'.format(seq=','.join(['?']*len(student_ids)))
            c.execute(q, student_ids)
            entries = c.fetchall()
        conn.close()
        return render_template('dashboard_guru.html', user=user, students=students, entries=entries)
    else:
        # admin - show summary
        c.execute('SELECT * FROM users WHERE role="guru"')
        gurus = c.fetchall()
        c.execute('SELECT * FROM users WHERE role="siswa"')
        siswa = c.fetchall()
        conn.close()
        return render_template('dashboard_admin.html', user=user, gurus=gurus, siswa=siswa)

@app.route('/student/input', methods=['GET','POST'])
def student_input():
    user = current_user()
    if not user or user['role'] != 'siswa':
        return redirect(url_for('login'))
    if request.method == 'POST':
        date = request.form['date'] or datetime.today().strftime('%Y-%m-%d')
        wake_time = request.form.get('wake_time','')
        prayer = ','.join(request.form.getlist('prayer'))
        sport = request.form.get('sport','')
        food_notes = request.form.get('food_notes','')
        study_notes = request.form.get('study_notes','')
        community_notes = request.form.get('community_notes','')
        sleep_time = request.form.get('sleep_time','')
        conn = get_db(); c = conn.cursor()
        c.execute("INSERT INTO entries (student_id, date, wake_time, prayer, sport, food_notes, study_notes, community_notes, sleep_time, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                  (user['id'], date, wake_time, prayer, sport, food_notes, study_notes, community_notes, sleep_time, datetime.now().isoformat()))
        conn.commit(); conn.close()
        flash('Data kegiatan tersimpan.')
        return redirect(url_for('dashboard'))
    return render_template('student_input.html', user=user, today=datetime.today().strftime('%Y-%m-%d'))

# teacher endpoints to manage students
@app.route('/guru/add_student', methods=['GET','POST'])
def add_student():
    user = current_user()
    if not user or user['role'] != 'guru':
        return redirect(url_for('login'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        conn = get_db(); c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, password_hash, role, full_name, teacher_id) VALUES (?,?,?,?,?)',
                      (username, generate_password_hash(password), 'siswa', full_name, user['id']))
            conn.commit()
            flash('Siswa ditambahkan.')
        except Exception as e:
            flash('Gagal menambah siswa: '+str(e))
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template('add_student.html', user=user)

@app.route('/guru/edit_student/<int:sid>', methods=['GET','POST'])
def edit_student(sid):
    user = current_user()
    if not user or user['role'] != 'guru':
        return redirect(url_for('login'))
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id=? AND teacher_id=?', (sid, user['id']))
    s = c.fetchone()
    if not s:
        conn.close()
        flash('Siswa tidak ditemukan atau bukan bimbingan Anda.')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        full = request.form['full_name']
        pwd = request.form.get('password','').strip()
        if pwd:
            c.execute('UPDATE users SET full_name=?, password_hash=? WHERE id=?', (full, generate_password_hash(pwd), sid))
        else:
            c.execute('UPDATE users SET full_name=? WHERE id=?', (full, sid))
        conn.commit(); conn.close()
        flash('Data siswa diperbarui.')
        return redirect(url_for('dashboard'))
    conn.close()
    return render_template('edit_student.html', user=user, s=s)

@app.route('/guru/delete_student/<int:sid>', methods=['POST'])
def delete_student(sid):
    user = current_user()
    if not user or user['role'] != 'guru':
        return redirect(url_for('login'))
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id=? AND teacher_id=?', (sid, user['id']))
    if not c.fetchone():
        conn.close(); flash('Not allowed'); return redirect(url_for('dashboard'))
    c.execute('DELETE FROM users WHERE id=?', (sid,))
    c.execute('DELETE FROM entries WHERE student_id=?', (sid,))
    conn.commit(); conn.close()
    flash('Siswa dan data terkait dihapus.')
    return redirect(url_for('dashboard'))

# admin: manage users
@app.route('/admin/manage', methods=['GET','POST'])
def admin_manage():
    user = current_user()
    if not user or user['role'] != 'admin':
        return redirect(url_for('login'))
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT * FROM users')
    users = c.fetchall()
    conn.close()
    return render_template('admin_manage.html', user=user, users=users)

@app.route('/admin/add_user', methods=['GET','POST'])
def admin_add_user():
    user = current_user()
    if not user or user['role'] != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        full_name = request.form.get('full_name','')
        teacher_id = request.form.get('teacher_id') or None
        conn = get_db(); c = conn.cursor()
        try:
            tid = int(teacher_id) if teacher_id else None
            c.execute('INSERT INTO users (username, password_hash, role, full_name, teacher_id) VALUES (?,?,?,?,?)', (username, generate_password_hash(password), role, full_name, tid))
            conn.commit(); flash('User ditambahkan.')
        except Exception as e:
            flash('Gagal: '+str(e))
        conn.close(); return redirect(url_for('admin_manage'))
    return render_template('admin_add_user.html', user=user)

@app.route('/export/teacher/<int:teacher_id>')
def export_teacher(teacher_id):
    user = current_user()
    if not user or user['role'] not in ('guru','admin'):
        return redirect(url_for('login'))
    # ensure guru can only export their own unless admin
    if user['role']=='guru' and user['id']!=teacher_id:
        flash('Tidak diizinkan'); return redirect(url_for('dashboard'))
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT u.full_name as student_name, e.* FROM entries e JOIN users u ON e.student_id=u.id WHERE u.teacher_id=? ORDER BY e.date', (teacher_id,))
    rows = c.fetchall()
    conn.close()
    # create DataFrame
    data = [dict(r) for r in rows]
    if not data:
        flash('Tidak ada data'); return redirect(url_for('dashboard'))
    df = pd.DataFrame(data)
    # prepare xlsx in memory
    output = io.BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)
    filename = f'rekap_teacher_{teacher_id}.xlsx'
    return send_file(
    output,
    download_name=filename,
    as_attachment=True,
    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)



# admin: edit any user
@app.route('/admin/edit_user/<int:uid>', methods=['GET','POST'])
def admin_edit_user(uid):
    user = current_user()
    if not user or user['role'] != 'admin':
        return redirect(url_for('login'))
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id=?', (uid,))
    u = c.fetchone()
    if not u:
        conn.close(); flash('User tidak ditemukan.'); return redirect(url_for('admin_manage'))
    if request.method == 'POST':
        username = request.form.get('username', u["username"])
        full_name = request.form.get('full_name', u["full_name"])
        role = request.form.get('role', u["role"])
        password = request.form.get('password','').strip()
        teacher_id = request.form.get('teacher_id') or None
        try:
            if password:
                c.execute('UPDATE users SET username=?, full_name=?, role=?, password_hash=? WHERE id=?',
                          (username, full_name, role, generate_password_hash(password), uid))
            else:
                c.execute('UPDATE users SET username=?, full_name=?, role=? WHERE id=?',
                          (username, full_name, role, uid))
            # update teacher_id if column exists
            try:
                tid = int(teacher_id) if teacher_id else None
                c.execute('UPDATE users SET teacher_id=? WHERE id=?', (tid, uid))
            except:
                pass
            conn.commit(); flash('User diperbarui.')
        except Exception as e:
            flash('Gagal: '+str(e))
        conn.close(); return redirect(url_for('admin_manage'))
    conn.close()
    return render_template('admin_edit_user.html', user=user, u=u)

# admin: delete any user
@app.route('/admin/delete_user/<int:uid>', methods=['POST'])
def admin_delete_user(uid):
    user = current_user()
    if not user or user['role'] != 'admin':
        return redirect(url_for('login'))
    conn = get_db(); c = conn.cursor()
    # prevent admin deleting themselves accidentally
    if uid == user['id']:
        conn.close(); flash('Tidak bisa menghapus diri sendiri.'); return redirect(url_for('admin_manage'))
    try:
        c.execute('DELETE FROM users WHERE id=?', (uid,))
        # remove related entries if table exists
        try:
            c.execute('DELETE FROM entries WHERE student_id=?', (uid,))
        except:
            pass
        conn.commit()
        flash('User dan data terkait dihapus.')
    except Exception as e:
        flash('Gagal: '+str(e))
    conn.close()
    return redirect(url_for('admin_manage'))

if __name__ == '__main__':
    app.run(port=5533)
