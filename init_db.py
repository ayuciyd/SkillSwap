import MySQLdb

try:
    conn = MySQLdb.connect(host="localhost", user="root", password="ayushi1439")
    cursor = conn.cursor()
    with open('schema.sql', 'r', encoding='utf-8') as f:
        sql_script = f.read()

    # Simple split since schema.sql does not have ';' inside string literals
    statements = sql_script.split(';')
    for stmt in statements:
        if stmt.strip():
            cursor.execute(stmt)

    conn.commit()
    cursor.close()
    conn.close()
    print("Database Initialized successfully.")
except Exception as e:
    print(f"Error initializing DB: {e}")
