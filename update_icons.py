from app import app, mysql

with app.app_context():
    cursor = mysql.connection.cursor()
    updates = {
        'CAT-001': 'laptop',
        'CAT-002': 'music',
        'CAT-003': 'globe',
        'CAT-004': 'ruler',
        'CAT-005': 'palette',
        'CAT-006': 'microscope',
        'CAT-007': 'pie-chart',
        'CAT-008': 'pencil'
    }
    
    for cat_id, icon in updates.items():
        cursor.execute("UPDATE skill_categories SET icon=%s WHERE id=%s", (icon, cat_id))
        
    mysql.connection.commit()
    print("Database icons updated successfully!")
    cursor.close()
