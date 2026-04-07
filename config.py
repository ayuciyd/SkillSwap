import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'skillswap-secret-2024')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'ayushi1439')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'skillswap_db')
    MYSQL_CHARSET = 'utf8mb4'
    MYSQL_CURSORCLASS = 'DictCursor'
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'skillswap050@gmail.com')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'nrli vfdt tvky vgli')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'skillswap050@gmail.com')
