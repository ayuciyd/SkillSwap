import MySQLdb
import bcrypt
from datetime import datetime
import random
from utils import generate_id

def seed_data():
    conn = MySQLdb.connect(host="localhost", user="root", password="ayushi1439", database="skillswap_db")
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        # 1. Create Users
        users_data = [
            ("USR-STU-2024-00101", "Alex Chen", "alexc", "alex@university.edu", "Computer Science", 15),
            ("USR-STU-2024-00102", "Sarah Jenkins", "sarahj", "sarah@university.edu", "Business", 20),
            ("USR-STU-2024-00103", "Micah Torres", "micaht", "micah@university.edu", "Music", 12),
            ("USR-STU-2024-00104", "Emma Watson", "emmaw", "emma@university.edu", "Design", 25),
            ("USR-STU-2024-00105", "David Kim", "davidk", "david@university.edu", "Mathematics", 8)
        ]
        
        pass_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()
        
        for u in users_data:
            cursor.execute("SELECT id FROM users WHERE email=%s", (u[3],))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO users (id, full_name, username, email, password_hash, role, credits_balance, university, is_active, is_verified)
                    VALUES (%s, %s, %s, %s, %s, 'student', %s, %s, 1, 1)
                """, (u[0], u[1], u[2], u[3], pass_hash, u[5], u[4]))
        
        # 2. Create Skills
        skills_data = [
            ("SKL-PRG-2024-00001", "USR-STU-2024-00101", "CAT-001", "Python & Machine Learning", "teach", "advanced", "I can teach you how to build ML models using PyTorch and scikit-learn.", "both"),
            ("SKL-DES-2024-00002", "USR-STU-2024-00101", "CAT-005", "UI/UX Design basics", "learn", "beginner", "Looking to learn Figma and general design principles for my apps.", "online"),
            
            ("SKL-DES-2024-00003", "USR-STU-2024-00104", "CAT-005", "Mastering Figma & UI Design", "teach", "advanced", "I have 3 years of experience mapping out beautiful SaaS applications.", "both"),
            ("SKL-BIZ-2024-00004", "USR-STU-2024-00104", "CAT-007", "Marketing & SEO", "learn", "beginner", "I need to learn how to market my design agency.", "offline"),
            
            ("SKL-BIZ-2024-00005", "USR-STU-2024-00102", "CAT-007", "Digital Marketing", "teach", "intermediate", "I run a successful e-commerce store and can teach Facebook Ads.", "online"),
            ("SKL-MUS-2024-00006", "USR-STU-2024-00102", "CAT-002", "Acoustic Guitar", "learn", "beginner", "Always wanted to play guitar, have my own instrument.", "both"),
            
            ("SKL-MUS-2024-00007", "USR-STU-2024-00103", "CAT-002", "Guitar & Music Theory", "teach", "advanced", "I can teach you how to play acoustic guitar from scratch.", "offline"),
            ("SKL-PRG-2024-00008", "USR-STU-2024-00103", "CAT-001", "Basic Web Development", "learn", "beginner", "I want to build a website for my band.", "online"),
            
            ("SKL-MTH-2024-00009", "USR-STU-2024-00105", "CAT-004", "Advanced Calculus", "teach", "advanced", "College-level calculus and statistics tutoring.", "online"),
            ("SKL-LNG-2024-00010", "USR-STU-2024-00105", "CAT-003", "Spanish", "learn", "intermediate", "Looking to practice conversational Spanish.", "online")
        ]
        
        for s in skills_data:
            cursor.execute("SELECT id FROM skills WHERE id=%s", (s[0],))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO skills (id, user_id, category_id, skill_name, skill_type, level, description, preferred_mode, available_days, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 127, 1)
                """, s)
                
        # 3. Create a Match
        cursor.execute("SELECT id FROM matches WHERE id='MCH-2024-00101'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO matches (id, teacher_id, learner_id, teacher_skill_id, learner_skill_id, is_mutual, status, initiated_by)
                VALUES ('MCH-2024-00101', 'USR-STU-2024-00101', 'USR-STU-2024-00103', 'SKL-PRG-2024-00001', 'SKL-PRG-2024-00008', 1, 'accepted', 'USR-STU-2024-00103')
            """)
            
        print("Seed data successfully injected!")
        conn.commit()
    except Exception as e:
        print("Error seeding data:", e)
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    seed_data()
