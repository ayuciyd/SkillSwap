import MySQLdb

def update_bio():
    conn = MySQLdb.connect(host="localhost", user="root", password="ayushi1439", database="skillswap_db", charset="utf8mb4")
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE skills 
        SET description = 'I am eager to dive deep and learn everything I can about this subject!' 
        WHERE description LIKE '%Auto-generated%' AND skill_type='learn'
    """)
    
    cursor.execute("""
        UPDATE skills 
        SET description = 'I have great practical experience and I am excited to help you master this skill!' 
        WHERE description LIKE '%Auto-generated%' AND skill_type='teach'
    """)
        
    conn.commit()
    print("Bios updated explicitly")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    update_bio()
