import MySQLdb
import random

def update_unis():
    conn = MySQLdb.connect(host="localhost", user="root", password="ayushi1439", database="skillswap_db", charset="utf8mb4")
    cursor = conn.cursor()
    
    colleges = [
        "IIT Bombay", "IIT Delhi", "BITS Pilani", "NIT Trichy", 
        "Delhi University", "VIT Vellore", "SRM Chennai", 
        "Jadavpur University", "Anna University", "Manipal Institute of Technology",
        "COEP Pune", "VJTI Mumbai", "NIT Surathkal", "IIT Madras", "IIT Kanpur"
    ]
    
    cursor.execute("SELECT id FROM users WHERE role='student' AND id LIKE 'USR-FRN-%'")
    users = cursor.fetchall()
    
    for (uid,) in users:
        uni = random.choice(colleges)
        cursor.execute("UPDATE users SET university=%s WHERE id=%s", (uni, uid))
        
    conn.commit()
    print("Universities updated explicitly")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    update_unis()
