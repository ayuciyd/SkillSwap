import MySQLdb
import bcrypt
import random

def fix_and_seed():
    conn = MySQLdb.connect(host="localhost", user="root", password="ayushi1439", database="skillswap_db", charset="utf8mb4")
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    # Fix the category emojis
    cats = [
        ('CAT-001', '💻'), ('CAT-002', '🎸'), ('CAT-003', '🗣️'), ('CAT-004', '📚'),
        ('CAT-005', '🎨'), ('CAT-006', '💪'), ('CAT-007', '📈')
    ]
    for cat_id, icon in cats:
        cursor.execute("UPDATE skill_categories SET icon=%s WHERE id=%s", (icon, cat_id))
        
    friends = [
        "Devika Patil", "Durva Rane", "Sowmya Govindhrajan", "Sagar Surwase", 
        "Prachi Mishra", "Tashaf Shaik", "Eklavya Singh", "Shubham Tambe", 
        "Darsh Trivedi", "Sameer Sonawane", "Shubham Yadav", "Vartika Yadav"
    ]
    cat_ids = ["CAT-001", "CAT-002", "CAT-003", "CAT-004", "CAT-005", "CAT-006", "CAT-007"]
    topics = {
        "CAT-001": ["Python Core", "Data Structures", "React Native", "Java Spring Boot"],
        "CAT-002": ["Classical Vocals", "Keyboard basics", "Music Production", "FL Studio"],
        "CAT-003": ["German A1", "Advanced English", "French Basics", "Japanese N5"],
        "CAT-004": ["Linear Algebra", "Calculus III", "Discrete Math", "GMAT Quant"],
        "CAT-005": ["UI/UX Prototyping", "Photoshop", "Illustrator", "Video Editing"],
        "CAT-006": ["Yoga", "Home Workouts", "Nutrition", "Powerlifting"],
        "CAT-007": ["Social Media", "Stock Market", "SEO Optimization", "Public Speaking"]
    }
    
    pass_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()
    
    # We will use Admin as the mock learner for their sessions
    cursor.execute("SELECT id FROM users WHERE role='admin' LIMIT 1")
    admin = cursor.fetchone()
    if not admin:
        return
    admin_id = admin['id']
    cursor.execute("SELECT id FROM skills WHERE user_id=%s LIMIT 1", (admin_id,))
    admin_skill = cursor.fetchone()
    if not admin_skill:
        admin_skill_id = "SKL-ADM-DUMMY"
        cursor.execute("INSERT IGNORE INTO skills (id, user_id, category_id, skill_name, skill_type, description) VALUES (%s, %s, 'CAT-001', 'Admin Skill', 'learn', 'Dummy') ", (admin_skill_id, admin_id))
    else:
        admin_skill_id = admin_skill['id']
    
    for i, name in enumerate(friends):
        parts = name.split()
        first = parts[0].lower()
        last = parts[-1].lower() if len(parts) > 1 else ""
        email = f"{first}.{last}@vjti.edu.in"
        uid = f"USR-FRN-2024-{300+i:03d}"
        
        cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
        if not cursor.fetchone():
            sessions_count = random.randint(15, 60)
            credits = random.randint(20, 200)
            username = f"{first}{last}{random.randint(1,99)}"
            
            cursor.execute("""
                INSERT INTO users (id, full_name, username, email, password_hash, role, credits_balance, credits_earned, university, is_active, is_verified)
                VALUES (%s, %s, %s, %s, %s, 'student', %s, %s, 'VJTI Mumbai', 1, 1)
            """, (uid, name, username, email, pass_hash, credits, credits))
            
            t_skill_ids = []
            for j in range(2):
                t_cat = random.choice(cat_ids)
                t_skill = random.choice(topics[t_cat])
                sk_id = f"SKL-T-{350+i}-{j}"
                t_skill_ids.append(sk_id)
                cursor.execute("""
                    INSERT INTO skills (id, user_id, category_id, skill_name, skill_type, level, description, preferred_mode, available_days, is_active)
                    VALUES (%s, %s, %s, %s, 'teach', 'advanced', 'Great at this!', 'both', 127, 1)
                """, (sk_id, uid, t_cat, f"{t_skill} by {first}"))
            
            l_cat = random.choice(cat_ids)
            l_skill = random.choice(topics[l_cat])
            cursor.execute("""
                INSERT INTO skills (id, user_id, category_id, skill_name, skill_type, level, description, preferred_mode, available_days, is_active)
                VALUES (%s, %s, %s, %s, 'learn', 'beginner', 'Looking to learn', 'online', 127, 1)
            """, (f"SKL-L-{350+i}", uid, l_cat, l_skill))
            
            match_id = f"MCH-FRN-{350+i}"
            cursor.execute("""
                INSERT IGNORE INTO matches (id, teacher_id, learner_id, teacher_skill_id, learner_skill_id, status)
                VALUES (%s, %s, %s, %s, %s, 'accepted')
            """, (match_id, uid, admin_id, t_skill_ids[0], admin_skill_id))
            
            for s_idx in range(sessions_count):
                ses_id = f"SES-FRN-{350+i}-{s_idx}"
                rev_id = f"REV-FRN-{350+i}-{s_idx}"
                cursor.execute("""
                    INSERT IGNORE INTO sessions (id, match_id, teacher_id, learner_id, skill_id, session_date, session_time, mode, status)
                    VALUES (%s, %s, %s, %s, %s, '2024-01-01', '10:00:00', 'online', 'completed')
                """, (ses_id, match_id, uid, admin_id, t_skill_ids[0]))
                
                rating = random.choice([4, 5, 5, 5])
                cursor.execute("""
                    INSERT IGNORE INTO reviews (id, session_id, reviewer_id, reviewee_id, rating, comment)
                    VALUES (%s, %s, %s, %s, %s, 'Awesome session!')
                """, (rev_id, ses_id, admin_id, uid, rating))
                
    conn.commit()
    print("Database encodings fixed and friends network injected successfully!")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    fix_and_seed()
