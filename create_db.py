import sqlite3
def initialize_database():
    conn = sqlite3.connect('monitor.db')
    cursor = conn.cursor()
    
    # Create matched_data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matched_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT NOT NULL,
            message TEXT NOT NULL,
            date TEXT NOT NULL
        )
    ''')
    
    # Create keywords table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL
        )
    ''')
    
    # Create channels table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == '__main__':
    initialize_database()
