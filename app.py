from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from functools import wraps
from config import Config
from utils import generate_id, get_db_cursor
import datetime
import random
import string
import os
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

app = Flask(__name__)
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = 'static/uploads/certificates'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

mysql = MySQL(app)
bcrypt = Bcrypt(app)
mail = Mail(app)

# -------------------------------------------------------------------
# DECORATORS
# -------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# -------------------------------------------------------------------
# HELPER DEFS
# -------------------------------------------------------------------
def update_user_balance(cursor, user_id):
    cursor.execute("SELECT COALESCE(SUM(amount), 0) as sm FROM credit_transactions WHERE user_id=%s", (user_id,))
    new_bal = int(cursor.fetchone()['sm'])
    
    cursor.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN amount > 0 AND tx_type != 'session_refund' THEN amount ELSE 0 END), 0) as earned,
            COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0) as spent
        FROM credit_transactions WHERE user_id=%s
    """, (user_id,))
    stats = cursor.fetchone()
    
    cursor.execute("""
        UPDATE users 
        SET credits_balance=%s, credits_earned=%s, credits_spent=%s
        WHERE id=%s
    """, (new_bal, int(stats['earned']), int(stats['spent']), user_id))

def record_transaction(cursor, user_id, tx_type, amount, reference_note=None, session_id=None):
    cursor.execute("SELECT credits_balance FROM users WHERE id=%s", (user_id,))
    curr_bal = cursor.fetchone()['credits_balance']
    balance_after = curr_bal + amount
    txn_id = generate_id(mysql, 'TXN', 'CRD', cursor=cursor)
    
    cursor.execute("""
        INSERT INTO credit_transactions (id, user_id, tx_type, amount, balance_after, session_id, reference_note)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (txn_id, user_id, tx_type, amount, balance_after, session_id, reference_note))
    update_user_balance(cursor, user_id)

def create_notification(cursor, user_id, notif_type, title, message, action_url=None):
    notif_id = generate_id(mysql, 'NTF', cursor=cursor)
    cursor.execute("""
        INSERT INTO notifications (id, user_id, notif_type, title, message, action_url)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (notif_id, user_id, notif_type, title, message, action_url))

# -------------------------------------------------------------------
# MATCHING ALGORITHM
# -------------------------------------------------------------------
def find_matches_for_user(user_id):
    with get_db_cursor(mysql) as cursor:
        cursor.execute("SELECT * FROM skills WHERE user_id=%s AND skill_type='teach' AND is_active=1", (user_id,))
        my_teach_cat = {s['category_id']: s for s in cursor.fetchall()}
        
        cursor.execute("SELECT * FROM skills WHERE user_id=%s AND skill_type='learn' AND is_active=1", (user_id,))
        my_learn_cat = {s['category_id']: s for s in cursor.fetchall()}
        
        cursor.execute("""
            SELECT teacher_id, learner_id FROM matches 
            WHERE status IN ('pending', 'accepted') AND (teacher_id=%s OR learner_id=%s)
        """, (user_id, user_id))
        existing_partners = {m['teacher_id'] for m in cursor.fetchall()} | {m['learner_id'] for m in cursor.fetchall()}
        existing_partners.discard(user_id)
            
        cursor.execute("""
            SELECT u.id as user_id, u.full_name, u.username, u.university, u.credits_balance,
                   (SELECT COALESCE(AVG(rating),0) FROM reviews WHERE reviewee_id=u.id) as avg_rating,
                   (SELECT COUNT(*) FROM sessions WHERE teacher_id=u.id AND status='completed') as total_sessions,
                   s.id as skill_id, s.category_id, s.skill_type, s.level, s.preferred_mode, s.available_days, s.skill_name
            FROM users u
            JOIN skills s ON u.id = s.user_id
            WHERE u.id != %s AND u.is_active=1 AND s.is_active=1
        """, (user_id,))
        all_other_skills = cursor.fetchall()
        
    users_teach = {}
    users_learn = {}
    other_user_info = {}
    
    for row in all_other_skills:
        uid = row['user_id']
        other_user_info[uid] = {
            'full_name': row['full_name'], 'username': row['username'], 'university': row['university'],
            'credits_balance': row['credits_balance'], 'avg_rating': float(row['avg_rating']), 'total_sessions': row['total_sessions']
        }
        if row['skill_type'] == 'teach':
            if uid not in users_teach: users_teach[uid] = []
            users_teach[uid].append(row)
        else:
            if uid not in users_learn: users_learn[uid] = []
            users_learn[uid].append(row)
            
    matches = []
    level_map = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
    
    for uid, info in other_user_info.items():
        for t_skill in users_teach.get(uid, []):
            if t_skill['category_id'] in my_learn_cat:
                my_l_skill = my_learn_cat[t_skill['category_id']]
                
                score = 50
                is_mutual = any(l['category_id'] in my_teach_cat for l in users_learn.get(uid, []))
                if is_mutual:
                    score += 20
                    
                t_lvl = level_map.get(t_skill['level'], 2)
                l_lvl = level_map.get(my_l_skill['level'], 1)
                if t_lvl > l_lvl:
                    score += 15
                    
                if t_skill['preferred_mode'] == 'both' or my_l_skill['preferred_mode'] == 'both' or t_skill['preferred_mode'] == my_l_skill['preferred_mode']:
                    score += 10
                    
                if (t_skill['available_days'] & my_l_skill['available_days']) > 0:
                    score += 5
                    
                if uid in existing_partners:
                    score -= 10
                    
                matches.append({
                    'user_id': uid,
                    'full_name': info['full_name'],
                    'username': info['username'],
                    'university': info['university'],
                    'their_teach_skill': t_skill['skill_name'],
                    'their_teach_skill_id': t_skill['skill_id'],
                    'your_learn_skill': my_l_skill['skill_name'],
                    'your_learn_skill_id': my_l_skill['id'],
                    'match_score': score,
                    'is_mutual': is_mutual,
                    'credits_balance': info['credits_balance'],
                    'avg_rating': round(info['avg_rating'], 1),
                    'total_sessions': info['total_sessions']
                })
                
    matches.sort(key=lambda x: x['match_score'], reverse=True)
    return matches[:20]

# -------------------------------------------------------------------
# GLOBAL INJECTORS
# -------------------------------------------------------------------
@app.context_processor
def inject_globals():
    if 'user_id' in session:
        with get_db_cursor(mysql) as cursor:
            cursor.execute("SELECT credits_balance, role, full_name, username FROM users WHERE id=%s", (session['user_id'],))
            user = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(*) as c FROM notifications WHERE user_id=%s AND is_read=0", (session['user_id'],))
            unreads = cursor.fetchone()['c']
            
            return {'current_user': user, 'unread_notifications': unreads, 'now': datetime.datetime.now()}
    return {'now': datetime.datetime.now()}

@app.template_filter('fmt_date')
def fmt_date(value):
    if not value: return ""
    if isinstance(value, str):
        try:
            value = datetime.datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError:
            pass
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime('%d %B %Y')
    return value

@app.template_filter('fmt_time')
def fmt_time(value):
    if not value: return ""
    if isinstance(value, str):
        try:
            return datetime.datetime.strptime(value[:5], '%H:%M').strftime('%I:%M %p')
        except ValueError:
            pass
    if isinstance(value, datetime.timedelta):
        hours, remainder = divmod(value.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return datetime.time(hours, minutes).strftime('%I:%M %p')
    if isinstance(value, (datetime.time, datetime.datetime)):
        return value.strftime('%I:%M %p')
    return value

# -------------------------------------------------------------------
# AUTH ROUTES
# -------------------------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        university = request.form.get('university')
        
        if not all([full_name, username, email, password]):
            flash("Please fill in all required fields.", "error")
            return redirect(url_for('register'))

        pass_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        
        with get_db_cursor(mysql) as cursor:
            cursor.execute("SELECT id FROM users WHERE username=%s OR email=%s", (username, email))
            if cursor.fetchone():
                flash("Username or email already exists.", "error")
                return redirect(url_for('register'))
            
            otp = ''.join(random.choices(string.digits, k=6))
            otp_exp = datetime.datetime.now() + datetime.timedelta(minutes=10)
            
            session['pending_registration'] = {
                'full_name': full_name,
                'username': username,
                'email': email,
                'password_hash': pass_hash,
                'university': university,
                'otp_code': otp,
                'otp_expires_at': otp_exp.timestamp()
            }
            
        try:
            import socket
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(20.0)
            msg = Message("Your SkillSwap OTP", recipients=[email])
            msg.body = f"Hello {full_name},\n\nYour OTP for SkillSwap is {otp}. It is valid for 10 minutes."
            mail.send(msg)
            socket.setdefaulttimeout(old_timeout)
            flash("Registration step 1 complete! Please check your email for the OTP.", "success")
        except Exception as e:
            try: socket.setdefaulttimeout(old_timeout)
            except: pass
            flash(f"Registration step 1 complete, but email failed. Your OTP is: {otp}", "warning")
            print(f"OTP Email failure: {e}", flush=True)
            
        return redirect(url_for('verify_email'))
        
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        with get_db_cursor(mysql) as cursor:
            cursor.execute("SELECT * FROM users WHERE email=%s AND is_active=1", (email,))
            user = cursor.fetchone()
            
            if user:
                if user['locked_until'] and user['locked_until'] > datetime.datetime.now():
                    retry_time = user['locked_until'].strftime('%I:%M %p')
                    flash(f"Account locked due to too many failed attempts. You can retry at {retry_time}.", "error")
                    return render_template('auth/login.html')

                if bcrypt.check_password_hash(user['password_hash'], password):
                    # User is fully verified if they exist.

                    session['user_id'] = user['id']
                    session['role'] = user['role']
                    session['username'] = user['username']
                    
                    cursor.execute("UPDATE users SET last_login_at=CURRENT_TIMESTAMP, failed_login_attempts=0, locked_until=NULL WHERE id=%s", (user['id'],))
                    flash("Welcome back, " + user['full_name'] + "!", "success")
                    if user['role'] == 'admin':
                        return redirect(url_for('admin_dashboard'))
                    return redirect(url_for('dashboard'))
                else:
                    failed_attempts = user.get('failed_login_attempts', 0) + 1
                    if failed_attempts >= 3:
                        locked_until = datetime.datetime.now() + datetime.timedelta(minutes=15)
                        cursor.execute("UPDATE users SET failed_login_attempts=%s, locked_until=%s WHERE id=%s", (failed_attempts, locked_until, user['id']))
                        retry_time = locked_until.strftime('%I:%M %p')
                        flash(f"Account locked! Too many failed attempts. You can retry at {retry_time}.", "error")
                    else:
                        cursor.execute("UPDATE users SET failed_login_attempts=%s WHERE id=%s", (failed_attempts, user['id']))
                        flash(f"Invalid credentials. You have {3 - failed_attempts} attempt(s) left.", "error")
            else:
                flash("Invalid credentials or account disabled.", "error")
                
    return render_template('auth/login.html')

@app.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    if request.method == 'POST':
        otp = request.form.get('otp', '')
        
        pending = session.get('pending_registration')
        if not pending:
            flash("No pending registration found. Please register.", "error")
            return redirect(url_for('register'))
            
        if datetime.datetime.now().timestamp() > pending['otp_expires_at']:
            session.pop('pending_registration', None)
            flash("OTP has expired. Please register again.", "error")
            return redirect(url_for('register'))
            
        if str(pending['otp_code']) == str(otp):
            with get_db_cursor(mysql) as cursor:
                cursor.execute("SELECT id FROM users WHERE username=%s OR email=%s", (pending['username'], pending['email']))
                if cursor.fetchone():
                    session.pop('pending_registration', None)
                    flash("Username or email was taken while you were verifying. Please register again.", "error")
                    return redirect(url_for('register'))
                    
                user_id = generate_id(mysql, 'USR', 'STU', cursor=cursor)
                cursor.execute("""
                    INSERT INTO users (id, full_name, username, email, password_hash, role, credits_balance, university, email_verified)
                    VALUES (%s, %s, %s, %s, %s, 'student', 10, %s, 1)
                """, (user_id, pending['full_name'], pending['username'], pending['email'], pending['password_hash'], pending['university']))
                
                record_transaction(cursor, user_id, 'signup_bonus', 10, 'Signup Bonus')
                
            session.pop('pending_registration', None)
            flash("Email verified successfully! You can now log in.", "success")
            return redirect(url_for('login'))
        else:
            flash("Invalid OTP. Please try again.", "error")
            
    email = session.get('pending_registration', {}).get('email', '')
    return render_template('auth/verify_email.html', email=email)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        with get_db_cursor(mysql) as cursor:
            cursor.execute("SELECT id, full_name FROM users WHERE email=%s", (email,))
            user = cursor.fetchone()
            
            if user:
                otp = ''.join(random.choices(string.digits, k=6))
                otp_exp = datetime.datetime.now() + datetime.timedelta(minutes=10)
                cursor.execute("UPDATE users SET otp_code=%s, otp_expires_at=%s WHERE id=%s", (otp, otp_exp, user['id']))
                
                try:
                    import socket
                    old_timeout = socket.getdefaulttimeout()
                    socket.setdefaulttimeout(20.0)
                    msg = Message("SkillSwap Password Reset OTP", recipients=[email])
                    msg.body = f"Hello {user['full_name']},\n\nYour OTP to reset your password is {otp}. It is valid for 10 minutes."
                    mail.send(msg)
                    socket.setdefaulttimeout(old_timeout)
                    flash("An OTP has been sent to your email address.", "success")
                except Exception as e:
                    try: socket.setdefaulttimeout(old_timeout)
                    except: pass
                    flash(f"Failed to send email. Your OTP is: {otp}", "warning")
                    print(f"OTP Email failure: {e}", flush=True)
                
                session['reset_email'] = email
                return redirect(url_for('reset_password'))
            else:
                flash("If an account exists with that email, an OTP will be sent.", "info")
                return redirect(url_for('forgot_password'))
                
    return render_template('auth/forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email = session.get('reset_email', '')
    if request.method == 'POST':
        email = request.form.get('email', '')
        otp = request.form.get('otp', '')
        new_password = request.form.get('new_password', '')
        
        with get_db_cursor(mysql) as cursor:
            cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
            user = cursor.fetchone()
            
            if user:
                if str(user.get('otp_code')) == str(otp):
                    if user['otp_expires_at'] and user['otp_expires_at'] > datetime.datetime.now():
                        pass_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
                        cursor.execute("UPDATE users SET password_hash=%s, otp_code=NULL, otp_expires_at=NULL, locked_until=NULL, failed_login_attempts=0 WHERE id=%s", (pass_hash, user['id']))
                        flash("Password reset successfully! You can now log in.", "success")
                        session.pop('reset_email', None)
                        return redirect(url_for('login'))
                    else:
                        flash("OTP has expired. Please request a new one.", "error")
                        return redirect(url_for('forgot_password'))
                else:
                    flash("Invalid OTP. Please try again.", "error")
            else:
                flash("Invalid request.", "error")
                
    return render_template('auth/reset_password.html', email=email)

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been successfully logged out.", "success")
    return redirect(url_for('login'))

# -------------------------------------------------------------------
# PUBLIC ROUTES
# -------------------------------------------------------------------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# -------------------------------------------------------------------
# USER ROUTES
# -------------------------------------------------------------------
@app.route('/dashboard')
@login_required
def dashboard():
    uid = session['user_id']
    with get_db_cursor(mysql) as cursor:
        cursor.execute("SELECT COUNT(*) as c FROM matches WHERE status='accepted' AND (teacher_id=%s OR learner_id=%s)", (uid, uid))
        active_matches = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM sessions WHERE status IN ('scheduled', 'in_progress') AND (teacher_id=%s OR learner_id=%s)", (uid, uid))
        upcoming_sessions = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM skills WHERE user_id=%s AND is_active=1", (uid,))
        skills_listed = cursor.fetchone()['c']
        
        cursor.execute("""
            SELECT m.*, 
                   s1.skill_name as t_skill, s2.skill_name as l_skill,
                   u1.full_name as teacher, u2.full_name as learner
            FROM matches m
            JOIN skills s1 ON m.teacher_skill_id = s1.id
            JOIN skills s2 ON m.learner_skill_id = s2.id
            JOIN users u1 ON m.teacher_id = u1.id
            JOIN users u2 ON m.learner_id = u2.id
            WHERE (m.teacher_id=%s OR m.learner_id=%s)
            ORDER BY m.created_at DESC LIMIT 5
        """, (uid, uid))
        recent_matches = cursor.fetchall()
        
    suggested_matches = find_matches_for_user(uid)  # For Tinder UI
        
    return render_template('user/dashboard.html', 
                           active_matches=active_matches, 
                           upcoming_sessions=upcoming_sessions,
                           skills_listed=skills_listed,
                           recent_matches=recent_matches,
                           suggested_matches=suggested_matches)

@app.route('/skills', methods=['GET', 'POST'])
@login_required
def my_skills():
    uid = session['user_id']
    if request.method == 'POST':
        category_id = request.form.get('category_id')
        skill_name = request.form.get('skill_name')
        skill_type = request.form.get('skill_type')
        level = request.form.get('level')
        description = request.form.get('description')
        tags = request.form.get('tags')
        preferred_mode = request.form.get('preferred_mode')
        
        days = request.form.getlist('days')
        available_days = sum(int(d) for d in days) if days else 127

        skill_id = generate_id(mysql, 'SKL', category_id.split('-')[1] if category_id else 'UNK')
        is_active = 0 if skill_type == 'teach' else 1
        
        with get_db_cursor(mysql) as cursor:
            cursor.execute("""
                INSERT INTO skills (id, user_id, category_id, skill_name, skill_type, level, description, tags, available_days, preferred_mode, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (skill_id, uid, category_id, skill_name, skill_type, level, description, tags, available_days, preferred_mode, is_active))
            
            if skill_type == 'teach':
                certificate = request.files.get('certificate')
                if certificate and certificate.filename:
                    filename = secure_filename(f"{uid}_{skill_id}_{certificate.filename}")
                    cert_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    certificate.save(cert_path)
                    
                    cert_id = generate_id(mysql, 'CRT', cursor=cursor)
                    cursor.execute("""
                        INSERT INTO certificates (id, user_id, skill_id, file_path, status)
                        VALUES (%s, %s, %s, %s, 'pending')
                    """, (cert_id, uid, skill_id, filename))
                    
                    cursor.execute("SELECT full_name FROM users WHERE id=%s", (uid,))
                    user_row = cursor.fetchone()
                    user_name = user_row['full_name'] if user_row else uid
                    
                    try:
                        import socket
                        old_timeout = socket.getdefaulttimeout()
                        socket.setdefaulttimeout(20.0)
                        msg = Message("New Certificate Uploaded - SkillSwap Admin", 
                                      sender=app.config['MAIL_DEFAULT_SENDER'], 
                                      recipients=["skillswap050@gmail.com"])
                        msg.body = f"Hello Admin,\n\nA new certificate has been uploaded by user '{user_name}' for the skill '{skill_name}'.\nPlease log in to the admin panel to verify it.\n\nBest,\nSkillSwap System"
                        mail.send(msg)
                        socket.setdefaulttimeout(old_timeout)
                    except Exception as e:
                        try: socket.setdefaulttimeout(old_timeout)
                        except: pass
                        print(f"Failed to send email to admin: {e}", flush=True)
                else:
                    flash("Certificate is required for teaching skills. Your skill is currently inactive.", "warning")
            
        flash("Skill added successfully! Pending admin approval." if skill_type == 'teach' else "Skill added successfully!", "success")
        return redirect(url_for('my_skills'))
        
    with get_db_cursor(mysql) as cursor:
        cursor.execute("""
            SELECT s.*, c.name as category_name, c.icon, cert.status as cert_status 
            FROM skills s 
            JOIN skill_categories c ON s.category_id = c.id 
            LEFT JOIN certificates cert ON s.id = cert.skill_id
            WHERE s.user_id=%s AND (s.is_active=1 OR cert.status IN ('pending', 'rejected'))
        """, (uid,))
        skills = cursor.fetchall()
        cursor.execute("SELECT * FROM skill_categories WHERE is_active=1")
        categories = cursor.fetchall()
        
    return render_template('user/my_skills.html', skills=skills, categories=categories)

@app.route('/skills/delete/<id>', methods=['POST'])
@login_required
def delete_skill(id):
    with get_db_cursor(mysql) as cursor:
        cursor.execute("UPDATE skills SET is_active=0 WHERE id=%s AND user_id=%s", (id, session['user_id']))
        cursor.execute("DELETE FROM certificates WHERE skill_id=%s", (id,))
    flash("Skill deleted.", "success")
    return redirect(url_for('my_skills'))

@app.route('/browse', methods=['GET'])
@login_required
def browse():
    q = request.args.get('q', '')
    cat = request.args.get('category', '')
    mode = request.args.get('mode', '')
    
    query = "SELECT s.*, u.full_name, u.university, c.icon, c.name as cat_name FROM skills s JOIN users u ON s.user_id=u.id JOIN skill_categories c ON s.category_id=c.id WHERE s.skill_type='teach' AND s.is_active=1 AND u.is_active=1 AND s.user_id != %s"
    params = [session['user_id']]
    
    if q:
        query += " AND (s.skill_name LIKE %s OR s.description LIKE %s OR IFNULL(s.tags, '') LIKE %s OR u.full_name LIKE %s)"
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"])
        
    if cat:
        query += " AND s.category_id=%s"
        params.append(cat)
        
    if mode:
        query += " AND s.preferred_mode=%s"
        params.append(mode)
        
    query += " ORDER BY s.created_at DESC"
    
    grid = []
    suggested_matches = []
    with get_db_cursor(mysql) as cursor:
        if q or cat or mode:
            cursor.execute(query, tuple(params))
            grid = cursor.fetchall()
        else:
            suggested_matches = find_matches_for_user(session['user_id'])
            
        cursor.execute("SELECT * FROM skill_categories WHERE is_active=1")
        categories = cursor.fetchall()
        
        cursor.execute("SELECT id as my_skill_id, skill_name FROM skills WHERE user_id=%s AND skill_type='learn' AND is_active=1", (session['user_id'],))
        my_learn_skills = cursor.fetchall()
        
    return render_template('user/browse.html', grid=grid, matches=suggested_matches, categories=categories, my_learn_skills=my_learn_skills)

@app.route('/matches')
@login_required
def matches():
    uid = session['user_id']
    pref_cat = session.get('preferred_category')
    with get_db_cursor(mysql) as cursor:
        cursor.execute("SELECT * FROM skill_categories WHERE is_active=1")
        categories = cursor.fetchall()
        
        cursor.execute("""
            SELECT m.*, u1.full_name as teacher_name, u2.full_name as learner_name,
                   s1.skill_name as t_skill_name, s2.skill_name as l_skill_name
            FROM matches m
            JOIN users u1 ON m.teacher_id = u1.id
            JOIN users u2 ON m.learner_id = u2.id
            JOIN skills s1 ON m.teacher_skill_id = s1.id
            JOIN skills s2 ON m.learner_skill_id = s2.id
            WHERE m.teacher_id=%s OR m.learner_id=%s
            ORDER BY m.created_at DESC
        """, (uid, uid))
        all_m = cursor.fetchall()
        
        learn_query = """
            SELECT s.id as their_skill_id, s.skill_name as their_teach_skill, s.description, u.full_name, u.university, u.id as user_id, c.icon,
                   (SELECT COALESCE(AVG(rating),0) FROM reviews WHERE reviewee_id=u.id) as avg_rating
            FROM skills s JOIN users u ON s.user_id = u.id JOIN skill_categories c ON s.category_id = c.id
            WHERE s.skill_type='teach' AND s.is_active=1 AND u.id != %s
            AND s.id NOT IN (SELECT teacher_skill_id FROM matches WHERE learner_id=%s)
            AND s.id NOT IN (SELECT teacher_skill_id FROM matches WHERE learner_id=%s)
        """
        learn_params = [uid, uid, uid]
        if pref_cat and pref_cat != 'any':
            learn_query += " AND s.category_id = %s"
            learn_params.append(pref_cat)
        learn_query += " ORDER BY RAND() LIMIT 20"
        cursor.execute(learn_query, tuple(learn_params))
        swipe_learn = cursor.fetchall()
        
        teach_query = """
            SELECT s.id as their_skill_id, s.skill_name as their_teach_skill, s.description, u.full_name, u.university, u.id as user_id, c.icon,
                   (SELECT COALESCE(AVG(rating),0) FROM reviews WHERE reviewee_id=u.id) as avg_rating
            FROM skills s JOIN users u ON s.user_id = u.id JOIN skill_categories c ON s.category_id = c.id
            WHERE s.skill_type='learn' AND s.is_active=1 AND u.id != %s
            AND s.id NOT IN (SELECT learner_skill_id FROM matches WHERE teacher_id=%s)
            AND s.id NOT IN (SELECT learner_skill_id FROM matches WHERE teacher_id=%s)
        """
        teach_params = [uid, uid, uid]
        if pref_cat and pref_cat != 'any':
            teach_query += " AND s.category_id = %s"
            teach_params.append(pref_cat)
        teach_query += " ORDER BY RAND() LIMIT 20"
        cursor.execute(teach_query, tuple(teach_params))
        swipe_teach = cursor.fetchall()
        
    return render_template('user/matches.html', matches=all_m, swipe_learn=swipe_learn, swipe_teach=swipe_teach, uid=uid, categories=categories, pref_cat=pref_cat)

@app.route('/matches/pass', methods=['POST'])
@login_required
def swipe_pass():
    session['swipe_rejections'] = session.get('swipe_rejections', 0) + 1
    prompt = session['swipe_rejections'] >= 5
    return jsonify({'prompt_category': prompt, 'count': session['swipe_rejections']})

@app.route('/matches/set_preference', methods=['POST'])
@login_required
def set_preference():
    cat = request.form.get('category_id')
    if cat:
        session['preferred_category'] = cat
        session['swipe_rejections'] = 0
        if cat == 'any':
            flash("Feed generalized to all categories.", "success")
        else:
            flash("Feed category preference updated!", "success")
    return redirect(url_for('matches'))

@app.route('/matches/<id>/accept', methods=['POST'])
@login_required
def accept_match(id):
    uid = session['user_id']
    with get_db_cursor(mysql) as cursor:
        cursor.execute("SELECT * FROM matches WHERE id=%s", (id,))
        m = cursor.fetchone()
        if not m or (m['teacher_id'] != uid and m['learner_id'] != uid): return "Unauthorized", 403
        
        cursor.execute("UPDATE matches SET status='accepted', responded_at=CURRENT_TIMESTAMP WHERE id=%s", (id,))
        other_user = m['teacher_id'] if m['learner_id'] == uid else m['learner_id']
        create_notification(cursor, other_user, 'match_accepted', 'Match Accepted!', 'Someone accepted your match request.', f"/matches")
        
    flash("Match accepted! You can now schedule a session.", "success")
    return redirect(url_for('matches'))

@app.route('/matches/<id>/reject', methods=['POST'])
@login_required
def reject_match(id):
    uid = session['user_id']
    reason = request.form.get('reason', '')
    with get_db_cursor(mysql) as cursor:
        cursor.execute("UPDATE matches SET status='rejected', rejected_reason=%s, responded_at=CURRENT_TIMESTAMP WHERE id=%s AND (teacher_id=%s OR learner_id=%s)", (reason, id, uid, uid))
    flash("Match rejected.", "success")
    return redirect(url_for('matches'))

@app.route('/matches/create', methods=['POST'])
@login_required
def create_match():
    uid = session['user_id']
    session['swipe_rejections'] = 0
    their_skill_id = request.form.get('their_skill_id')
    
    with get_db_cursor(mysql) as cursor:
        cursor.execute("SELECT user_id, category_id, skill_name, skill_type FROM skills WHERE id=%s", (their_skill_id,))
        their_skill = cursor.fetchone()
        their_uid = their_skill['user_id']
        
        if their_skill['skill_type'] == 'teach':
            my_action = 'learn'
        else:
            my_action = 'teach'
            
        cursor.execute("SELECT id FROM skills WHERE user_id=%s AND skill_type=%s AND category_id=%s LIMIT 1", (uid, my_action, their_skill['category_id']))
        my_skill = cursor.fetchone()
        if not my_skill:
            my_skill_id = generate_id(mysql, 'SKL', 'AUT')
            desc = "I am eager to dive deep and learn everything I can about this subject!" if my_action == 'learn' else "I have great practical experience and I am excited to help you master this skill!"
            cursor.execute("INSERT INTO skills (id, user_id, category_id, skill_name, skill_type, description) VALUES (%s, %s, %s, %s, %s, %s)", 
                           (my_skill_id, uid, their_skill['category_id'], ('Learn ' if my_action=='learn' else 'Teach ') + their_skill['skill_name'], my_action, desc))
        else:
            my_skill_id = my_skill['id']
            
        if my_action == 'learn':
            t_id, l_id = their_uid, uid
            ts_id, ls_id = their_skill_id, my_skill_id
        else:
            t_id, l_id = uid, their_uid
            ts_id, ls_id = my_skill_id, their_skill_id
            
        match_id = generate_id(mysql, 'MCH', cursor=cursor)
        try:
            cursor.execute("INSERT INTO matches (id, teacher_id, learner_id, teacher_skill_id, learner_skill_id, initiated_by) VALUES (%s, %s, %s, %s, %s, %s)", 
                           (match_id, t_id, l_id, ts_id, ls_id, uid))
            create_notification(cursor, their_uid, 'new_match', 'New Match Request', 'Someone wants to connect!', '/matches')
            flash("Match requested successfully!", "success")
        except:
            flash("Match already exists.", "warning")
            
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'success'})
    return redirect(request.referrer or url_for('browse'))


@app.route('/sessions', methods=['GET', 'POST'])
@login_required
def sessions():
    uid = session['user_id']
    if request.method == 'POST':
        match_id = request.form.get('match_id')
        session_date = request.form.get('session_date')
        session_time = request.form.get('session_time')
        mode = request.form.get('mode')
        meeting_link = request.form.get('meeting_link')
        location = request.form.get('location')
        
        with get_db_cursor(mysql) as cursor:
            cursor.execute("SELECT * FROM matches WHERE id=%s AND status='accepted'", (match_id,))
            m = cursor.fetchone()
            if not m:
                flash("Invalid match for scheduling.", "error")
                return redirect(url_for('sessions'))
                
            teacher_id = m['teacher_id']
            learner_id = m['learner_id']
            
            # Ensure no overlapping sessions for either user (sessions are 1 hour long)
            cursor.execute("""
                SELECT id FROM sessions 
                WHERE status IN ('scheduled', 'in_progress')
                AND session_date = %s
                AND (teacher_id IN (%s, %s) OR learner_id IN (%s, %s))
                AND ABS(TIME_TO_SEC(TIMEDIFF(session_time, CAST(%s AS TIME)))) < 3600
            """, (session_date, teacher_id, learner_id, teacher_id, learner_id, session_time))
            
            if cursor.fetchone():
                flash("Schedule conflict! One of the participants already has a session scheduled within 1 hour of this time.", "error")
                return redirect(url_for('sessions'))
                
            ses_id = generate_id(mysql, 'SES', 'ONL' if mode=='online' else 'OFL', cursor=cursor)
            
            cursor.execute("""
                INSERT INTO sessions (id, match_id, teacher_id, learner_id, skill_id, session_date, session_time, mode, meeting_link, location, credits_cost, credits_paid)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, 1)
            """, (ses_id, match_id, m['teacher_id'], m['learner_id'], m['teacher_skill_id'], session_date, session_time, mode, meeting_link, location))
            
            formatted_date = fmt_date(session_date)
            formatted_time = fmt_time(session_time)
            create_notification(cursor, m['teacher_id'], 'session_scheduled', 'New Session', f'Session scheduled for {formatted_date} at {formatted_time}', f"/sessions")
            create_notification(cursor, m['learner_id'], 'session_scheduled', 'Session Booked', f'You booked a session for {formatted_date} at {formatted_time}', f"/sessions")
            
        flash("Session scheduled successfully!", "success")
        return redirect(url_for('sessions'))
        
    with get_db_cursor(mysql) as cursor:
        cursor.execute("""
            SELECT s.*, u1.full_name as teacher, u2.full_name as learner, sk.skill_name
            FROM sessions s
            JOIN users u1 ON s.teacher_id = u1.id
            JOIN users u2 ON s.learner_id = u2.id
            JOIN skills sk ON s.skill_id = sk.id
            WHERE s.teacher_id=%s OR s.learner_id=%s
            ORDER BY s.session_date DESC, s.session_time DESC
        """, (uid, uid))
        my_sessions = cursor.fetchall()
        
        cursor.execute("""
            SELECT m.*, u.full_name as partner_name, s.skill_name 
            FROM matches m 
            JOIN users u ON (CASE WHEN m.teacher_id=%s THEN m.learner_id ELSE m.teacher_id END) = u.id
            JOIN skills s ON m.teacher_skill_id = s.id
            WHERE (m.teacher_id=%s OR m.learner_id=%s) AND m.status='accepted'
        """, (uid, uid, uid))
        accepted_matches = cursor.fetchall()
        
    return render_template('user/sessions.html', sessions=my_sessions, matches=accepted_matches, uid=uid)

@app.route('/sessions/<id>/complete', methods=['POST'])
@login_required
def complete_session(id):
    uid = session['user_id']
    with get_db_cursor(mysql) as cursor:
        cursor.execute("SELECT * FROM sessions WHERE id=%s AND (teacher_id=%s OR learner_id=%s)", (id, uid, uid))
        ses = cursor.fetchone()
        if ses and ses['status'] in ('scheduled', 'in_progress'):
            cursor.execute("UPDATE sessions SET status='completed', completed_at=CURRENT_TIMESTAMP WHERE id=%s", (id,))
            record_transaction(cursor, ses['teacher_id'], 'session_receipt', 5, 'Session completed', id)
            create_notification(cursor, ses['teacher_id'], 'session_completed', 'Session Complete', 'You earned 5 credits!', f'/profile')
            create_notification(cursor, ses['learner_id'], 'session_completed', 'Session Complete', 'Please leave a review.', f'/review/{id}')
            flash("Session marked as complete.", "success")
        else:
            flash("Cannot complete this session.", "error")
    return redirect(url_for('sessions'))

@app.route('/sessions/<id>/cancel', methods=['POST'])
@login_required
def cancel_session(id):
    uid = session['user_id']
    reason = request.form.get('reason', 'User cancelled')
    with get_db_cursor(mysql) as cursor:
        cursor.execute("SELECT * FROM sessions WHERE id=%s AND (teacher_id=%s OR learner_id=%s)", (id, uid, uid))
        ses = cursor.fetchone()
        if ses and ses['status'] == 'scheduled':
            cursor.execute("UPDATE sessions SET status='cancelled', cancelled_by=%s, cancel_reason=%s, cancelled_at=CURRENT_TIMESTAMP WHERE id=%s", (uid, reason, id))
            flash("Session cancelled.", "success")
            
            other = ses['teacher_id'] if ses['learner_id'] == uid else ses['learner_id']
            create_notification(cursor, other, 'session_cancelled', 'Session Cancelled', f'Session was cancelled: {reason}')
    return redirect(url_for('sessions'))

@app.route('/sessions/<id>/export_calendar')
@login_required
def export_calendar(id):
    import urllib.parse
    uid = session['user_id']
    with get_db_cursor(mysql) as cursor:
        cursor.execute("""
            SELECT s.*, u.full_name as partner_name, sk.skill_name 
            FROM sessions s
            JOIN users u ON (CASE WHEN s.teacher_id=%s THEN s.learner_id ELSE s.teacher_id END) = u.id
            JOIN skills sk ON s.skill_id = sk.id
            WHERE s.id=%s AND (s.teacher_id=%s OR s.learner_id=%s)
        """, (uid, id, uid, uid))
        ses = cursor.fetchone()
        
    if not ses:
        flash("Session not found.", "error")
        return redirect(url_for('sessions'))
        
    start_dt = str(ses['session_date']) + ' ' + str(ses['session_time'])
    try:
        dt = datetime.datetime.strptime(start_dt, '%Y-%m-%d %H:%M:%S')
    except:
        dt = datetime.datetime.now()
    
    end_dt = dt + datetime.timedelta(hours=1)
    fmt_start = dt.strftime('%Y%m%dT%H%M%SZ')
    fmt_end = end_dt.strftime('%Y%m%dT%H%M%SZ')
    
    title = f"SkillSwap: {ses['skill_name']} with {ses['partner_name']}"
    details = f"SkillSwap Session.\nPartner: {ses['partner_name']}\nMode: {ses['mode']}\nLocation/Link: {ses['meeting_link']}"
    
    params = {
        'action': 'TEMPLATE',
        'text': title,
        'dates': f"{fmt_start}/{fmt_end}",
        'details': details,
        'location': ses['meeting_link'] or 'Online'
    }
    url = "https://calendar.google.com/calendar/render?" + urllib.parse.urlencode(params)
    return redirect(url)

@app.route('/review/<session_id>', methods=['GET', 'POST'])
@login_required
def review(session_id):
    uid = session['user_id']
    if request.method == 'POST':
        rating = request.form.get('rating')
        comment = request.form.get('comment')
        
        with get_db_cursor(mysql) as cursor:
            cursor.execute("SELECT * FROM sessions WHERE id=%s AND (teacher_id=%s OR learner_id=%s)", (session_id, uid, uid))
            ses = cursor.fetchone()
            if not ses: return "Invalid session", 400
            
            reviewee = ses['teacher_id'] if ses['learner_id'] == uid else ses['learner_id']
            rev_id = generate_id(mysql, 'REV', cursor=cursor)
            
            try:
                cursor.execute("""
                    INSERT INTO reviews (id, session_id, reviewer_id, reviewee_id, rating, comment)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (rev_id, session_id, uid, reviewee, rating, comment))
                create_notification(cursor, reviewee, 'new_review', 'New Review Received', f'Someone left you a {rating}-star review!', f"/profile")
                flash("Review submitted!", "success")
            except:
                flash("You have already reviewed this session.", "error")
                
        return redirect(url_for('sessions'))
        
    return render_template('user/review.html', session_id=session_id)



@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    uid = session['user_id']
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        bio = request.form.get('bio')
        university = request.form.get('university')
        with get_db_cursor(mysql) as cursor:
            cursor.execute("UPDATE users SET full_name=%s, bio=%s, university=%s WHERE id=%s", (full_name, bio, university, uid))
            session['username'] = full_name # Used for display maybe
        flash("Profile updated.", "success")
        return redirect(url_for('profile'))
        
    with get_db_cursor(mysql) as cursor:
        cursor.execute("SELECT * FROM users WHERE id=%s", (uid,))
        user_info = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as c FROM sessions WHERE teacher_id=%s AND status='completed'", (uid,))
        completed_teach = cursor.fetchone()['c']
        
        cursor.execute("SELECT COUNT(*) as c FROM sessions WHERE (teacher_id=%s OR learner_id=%s) AND status='completed'", (uid, uid))
        total_sessions = cursor.fetchone()['c']
        
        if completed_teach >= 3 and not user_info['is_verified']:
            cursor.execute("UPDATE users SET is_verified=1 WHERE id=%s", (uid,))
            user_info['is_verified'] = 1
            
        cursor.execute("SELECT r.*, u.full_name as reviewer_name FROM reviews r JOIN users u ON r.reviewer_id=u.id WHERE r.reviewee_id=%s ORDER BY r.created_at DESC", (uid,))
        reviews = cursor.fetchall()
        
        badges = []
        if total_sessions >= 1: badges.append({'name': 'First Step', 'icon': 'sprout', 'color': 'var(--success)'})
        if total_sessions >= 5: badges.append({'name': 'Active Swapper', 'icon': 'zap', 'color': 'var(--primary)'})
        if total_sessions >= 15: badges.append({'name': 'Elite Legend', 'icon': 'gem', 'color': '#38BDF8'})
        
        if completed_teach >= 1: badges.append({'name': 'Instructor', 'icon': 'book', 'color': '#EF4444'})
        if completed_teach >= 5: badges.append({'name': 'Master Mentor', 'icon': 'crown', 'color': '#F59E0B'})
        
    return render_template('user/profile.html', user=user_info, reviews=reviews, completed_teach=completed_teach, badges=badges)

@app.route('/leaderboard')
@login_required
def leaderboard():
    with get_db_cursor(mysql) as cursor:
        cursor.execute("""
            SELECT u.username, u.full_name, u.university, u.credits_earned, u.id,
                   (SELECT COUNT(*) FROM sessions WHERE teacher_id=u.id AND status='completed') as sessions_completed,
                   (SELECT COALESCE(AVG(rating), 0) FROM reviews WHERE reviewee_id=u.id) as avg_rating
            FROM users u WHERE role='student'
        """)
        users = cursor.fetchall()
        
    top_sessions = sorted(users, key=lambda x: x['sessions_completed'], reverse=True)[:10]
    top_rating = sorted(users, key=lambda x: x['avg_rating'], reverse=True)[:10]
    top_credits = sorted(users, key=lambda x: x['credits_earned'], reverse=True)[:10]
    
    return render_template('user/leaderboard.html', top_sessions=top_sessions, top_rating=top_rating, top_credits=top_credits)

@app.route('/notifications', methods=['GET'])
@login_required
def notifications():
    with get_db_cursor(mysql) as cursor:
        cursor.execute("SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC LIMIT 50", (session['user_id'],))
        notifs = cursor.fetchall()
    return render_template('user/notifications.html', notifications=notifs)

@app.route('/notifications/mark-read', methods=['POST'])
@login_required
def mark_read():
    with get_db_cursor(mysql) as cursor:
        cursor.execute("UPDATE notifications SET is_read=1, read_at=CURRENT_TIMESTAMP WHERE user_id=%s AND is_read=0", (session['user_id'],))
    return redirect(url_for('notifications'))

# -------------------------------------------------------------------
# ADMIN ROUTES
# -------------------------------------------------------------------
@app.route('/admin')
@admin_required
def admin_dashboard():
    with get_db_cursor(mysql) as cursor:
        cursor.execute("SELECT COUNT(*) as c FROM users WHERE role='student'")
        tot_users = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM sessions WHERE status='completed'")
        tot_sessions = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM matches")
        tot_matches = cursor.fetchone()['c']
        cursor.execute("SELECT SUM(amount) as c FROM credit_transactions WHERE tx_type='signup_bonus'")
        circulating = cursor.fetchone()['c']
        
        cursor.execute("""
            SELECT c.name, COUNT(s.id) as count 
            FROM sessions s JOIN skills sk ON s.skill_id = sk.id 
            JOIN skill_categories c ON sk.category_id = c.id
            GROUP BY c.id
        """)
        cat_stats = cursor.fetchall()
        
        cursor.execute("SELECT * FROM notifications ORDER BY created_at DESC LIMIT 20")
        feed = cursor.fetchall()
        
    return render_template('admin/dashboard.html', tot_users=tot_users, tot_sessions=tot_sessions, 
                           tot_matches=tot_matches, circulating=circulating, cat_stats=cat_stats, feed=feed)

@app.route('/admin/users')
@admin_required
def admin_users():
    with get_db_cursor(mysql) as cursor:
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/<id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(id):
    with get_db_cursor(mysql) as cursor:
        cursor.execute("DELETE FROM credit_transactions WHERE user_id=%s", (id,))
        cursor.execute("DELETE FROM sessions WHERE teacher_id=%s OR learner_id=%s", (id, id))
        cursor.execute("DELETE FROM certificates WHERE user_id=%s", (id,))
        cursor.execute("DELETE FROM users WHERE id=%s", (id,))
    flash("User deleted.", "success")
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<id>/toggle_admin', methods=['POST'])
@admin_required
def admin_toggle_admin(id):
    with get_db_cursor(mysql) as cursor:
        cursor.execute("UPDATE users SET role = IF(role='admin', 'student', 'admin') WHERE id=%s", (id,))
    flash("Role updated.", "success")
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<id>/grant_credits', methods=['POST'])
@admin_required
def admin_grant_credits(id):
    amount = int(request.form.get('amount', 0))
    if amount != 0:
        with get_db_cursor(mysql) as cursor:
            record_transaction(cursor, id, 'admin_grant' if amount > 0 else 'admin_deduct', amount, 'Admin manual adjustment')
        flash(f"Adjusted {amount} credits.", "success")
    return redirect(url_for('admin_users'))

@app.route('/admin/skills')
@admin_required
def admin_skills():
    with get_db_cursor(mysql) as cursor:
        cursor.execute("SELECT s.*, u.full_name, c.name as category_name FROM skills s JOIN users u ON s.user_id = u.id JOIN skill_categories c ON s.category_id = c.id")
        skills = cursor.fetchall()
    return render_template('admin/skills.html', skills=skills)

@app.route('/admin/skills/<id>/delete', methods=['POST'])
@admin_required
def admin_delete_skill(id):
    with get_db_cursor(mysql) as cursor:
        cursor.execute("DELETE FROM skills WHERE id=%s", (id,))
    flash("Skill deleted.", "success")
    return redirect(url_for('admin_skills'))

@app.route('/admin/sessions')
@admin_required
def admin_sessions():
    with get_db_cursor(mysql) as cursor:
        cursor.execute("SELECT s.*, u1.full_name as teacher, u2.full_name as learner FROM sessions s JOIN users u1 ON s.teacher_id=u1.id JOIN users u2 ON s.learner_id=u2.id ORDER BY s.created_at DESC")
        sessions = cursor.fetchall()
    return render_template('admin/sessions.html', sessions=sessions)
    
@app.route('/admin/transactions')
@admin_required
def admin_transactions():
    with get_db_cursor(mysql) as cursor:
        cursor.execute("SELECT t.*, u.full_name FROM credit_transactions t JOIN users u ON t.user_id=u.id ORDER BY t.created_at DESC")
        txns = cursor.fetchall()
    return render_template('admin/transactions.html', transactions=txns)

@app.route('/admin/certificates')
@admin_required
def admin_certificates():
    with get_db_cursor(mysql) as cursor:
        cursor.execute("""
            SELECT c.*, u.full_name, s.skill_name 
            FROM certificates c
            JOIN users u ON c.user_id = u.id
            JOIN skills s ON c.skill_id = s.id
            WHERE c.status='pending'
        """)
        certs = cursor.fetchall()
    return render_template('admin/certificates.html', certificates=certs)

@app.route('/admin/certificates/<id>/<action>', methods=['POST'])
@admin_required
def admin_review_certificate(id, action):
    if action not in ['approve', 'reject']:
        return "Invalid action", 400
        
    status = 'approved' if action == 'approve' else 'rejected'
    with get_db_cursor(mysql) as cursor:
        cursor.execute("SELECT * FROM certificates WHERE id=%s", (id,))
        cert = cursor.fetchone()
        if cert:
            cursor.execute("UPDATE certificates SET status=%s, reviewed_by=%s, reviewed_at=CURRENT_TIMESTAMP WHERE id=%s", (status, session['user_id'], id))
            if status == 'approved':
                cursor.execute("UPDATE skills SET is_active=1 WHERE id=%s", (cert['skill_id'],))
                # Optionally mark user as verified globally
                cursor.execute("UPDATE users SET is_verified=1 WHERE id=%s", (cert['user_id'],))
                create_notification(cursor, cert['user_id'], 'admin_message', 'Certificate Approved', f"Your certificate for {cert['skill_id']} has been approved!")
            else:
                create_notification(cursor, cert['user_id'], 'admin_message', 'Certificate Rejected', f"Your certificate for {cert['skill_id']} was rejected. Please re-upload.")
                
    flash(f"Certificate {status}.", "success")
    return redirect(url_for('admin_certificates'))

if __name__ == '__main__':

    app.run(debug=True, port=5001)
