import MySQLdb
import os
from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'ayushi1439')
MYSQL_DB = os.environ.get('MYSQL_DB', 'skillswap_db')

def update_schema():
    print("Connecting to database...")
    db = MySQLdb.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        passwd=MYSQL_PASSWORD,
        db=MYSQL_DB,
        charset='utf8mb4'
    )
    cursor = db.cursor()

    try:
        # Add columns for email verification
        print("Checking users table for OTP columns...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT FALSE")
            print("Added email_verified column.")
        except MySQLdb.OperationalError as e:
            print("email_verified column might already exist:", e)

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN otp_code VARCHAR(6) NULL")
            print("Added otp_code column.")
        except MySQLdb.OperationalError as e:
            print("otp_code column might already exist:", e)

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN otp_expires_at TIMESTAMP NULL")
            print("Added otp_expires_at column.")
        except MySQLdb.OperationalError as e:
            print("otp_expires_at column might already exist:", e)

        # We must make sure existing users like 'admin' are verified, so they aren't locked out immediately.
        cursor.execute("UPDATE users SET email_verified = TRUE WHERE role = 'admin'")
        cursor.execute("UPDATE users SET email_verified = TRUE WHERE id = 'USR-ADM-2024-00001'")
        db.commit()

        # Create certificates table for teacher verification
        print("Creating certificates table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS certificates (
                id VARCHAR(25) PRIMARY KEY,
                user_id VARCHAR(25) NOT NULL,
                skill_id VARCHAR(25) NOT NULL,
                file_path VARCHAR(255) NOT NULL,
                status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending',
                reviewed_by VARCHAR(25) NULL,
                rejection_reason VARCHAR(255) NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE,
                INDEX idx_cert_status (status)
            ) ENGINE=InnoDB;
        """)
        db.commit()
        print("Certificates table ready.")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()
        print("Database connection closed.")

if __name__ == '__main__':
    update_schema()
