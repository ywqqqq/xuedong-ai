import sqlite3
from contextlib import contextmanager
import os

@contextmanager
def get_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()

def init_database(db_path='your_database.db'):
    """Initialize the database and create all necessary tables"""
    
    # Check if database file exists
    db_exists = os.path.exists(db_path)
    
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # Create session table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS session (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            start_time DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
            end_time DATETIME,
            session_title TEXT,
            status TEXT DEFAULT 'active',
            created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
            updated_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
            last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create message table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS message (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            sender_type TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
            intent TEXT,
            created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
            updated_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
            FOREIGN KEY (session_id) REFERENCES session(session_id)
        )
        ''')

        # Create knowledge table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge (
            knowledge_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
            updated_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime'))
        )
        ''')

        # Create session_knowledge table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_knowledge (
            session_id INTEGER NOT NULL,
            knowledge_id INTEGER NOT NULL,
            unfamiliar_count INTEGER DEFAULT 0,
            first_encountered_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
            last_encountered_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
            created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
            updated_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
            PRIMARY KEY (session_id, knowledge_id),
            FOREIGN KEY (session_id) REFERENCES session(session_id),
            FOREIGN KEY (knowledge_id) REFERENCES knowledge(knowledge_id)
        )
        ''')

        # Create user_knowledge table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_knowledge (
            user_id TEXT NOT NULL,
            knowledge_id INTEGER NOT NULL,
            total_unfamiliar_count INTEGER DEFAULT 0,
            first_encountered_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
            last_encountered_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
            created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
            updated_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
            PRIMARY KEY (user_id, knowledge_id),
            FOREIGN KEY (knowledge_id) REFERENCES knowledge(knowledge_id)
        )
        ''')

        # Create indexes for better query performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_session ON message(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_knowledge_session ON session_knowledge(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_knowledge_knowledge ON session_knowledge(knowledge_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_knowledge_user ON user_knowledge(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_knowledge_knowledge ON user_knowledge(knowledge_id)')

        # Insert some initial knowledge points (optional)
        initial_knowledge = [
            ('三角函数', '包括正弦、余弦、正切等三角函数的概念和应用'),
            ('函数', '函数的定义、性质、图像等基础知识'),
            ('导数', '导数的定义、求导法则、应用等'),
            ('积分', '积分的概念、计算方法和应用'),
            ('概率', '概率的基本概念、计算方法和应用')
        ]
        
        cursor.executemany('''
        INSERT OR IGNORE INTO knowledge (name, description)
        VALUES (?, ?)
        ''', initial_knowledge)

        conn.commit()

def main():
    """Main function to initialize the database"""
    db_path = 'tty.db'
    try:
        init_database(db_path)
        print(f"Successfully initialized database at {db_path}")
        
        # Print table schemas for verification
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            print("\nCreated tables:")
            for table in tables:
                print(f"\n{table[0]}:")
                cursor.execute(f"PRAGMA table_info({table[0]})")
                columns = cursor.fetchall()
                for column in columns:
                    print(f"  {column[1]}: {column[2]}")
                    
    except Exception as e:
        print(f"Error initializing database: {e}")

if __name__ == "__main__":
    main()