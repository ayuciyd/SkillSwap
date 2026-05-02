import datetime
from contextlib import contextmanager
import re

@contextmanager
def get_db_cursor(mysql):
    """Yields a database cursor, commits on success, rollbacks on error."""
    conn = mysql.connection
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()

def generate_id(mysql, prefix, type_code=None, cursor=None):
    """
    Generate a custom ID format: PREFIX-TYPECODE-YEAR-SEQUENCE or PREFIX-YEAR-SEQUENCE
    Takes the MySQL extension instance to query for the max ID.
    Examples: USR-STU-2024-00001 or MCH-2024-00001
    """
    year = datetime.datetime.now().year
    
    # Determine the table from the prefix
    table_map = {
        'USR': 'users',
        'SKL': 'skills',
        'CAT': 'skill_categories',
        'SES': 'sessions',
        'MCH': 'matches',
        'TXN': 'credit_transactions',
        'REV': 'reviews',
        'NTF': 'notifications',
        'CRT': 'certificates'
    }
    
    table = table_map.get(prefix)
    if not table:
        raise ValueError(f"Unknown prefix: {prefix}")
        
    if type_code:
        pattern = f"{prefix}-{type_code}-{year}-%"
        base_str = f"{prefix}-{type_code}-{year}-"
    else:
        pattern = f"{prefix}-{year}-%"
        base_str = f"{prefix}-{year}-"
        
    query = f"SELECT MAX(id) AS max_id FROM {table} WHERE id LIKE %s"
    if cursor:
        cursor.execute(query, (pattern,))
        result = cursor.fetchone()
    else:
        with get_db_cursor(mysql) as c:
            c.execute(query, (pattern,))
            result = c.fetchone()
        
    next_seq = 1
    if result and result['max_id']:
        max_id = result['max_id']
        # Try extracting the sequence number at the end
        match = re.search(r'-(\d+)$', max_id)
        if match:
            next_seq = int(match.group(1)) + 1
            
    return f"{base_str}{next_seq:05d}"
