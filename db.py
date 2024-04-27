import sqlite3

MAX_HISTORY_LENGTH = 5
def init_db():
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            model_name TEXT,
            message TEXT,
            type TEXT,  -- 'USER' or 'AI'
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def append_message(model_name, message, author_type):
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO chat_messages (model_name, message, type)
        VALUES (?, ?, ?)
    ''', (model_name, message, author_type))
    conn.commit()
    conn.close()

def get_history(model_name):
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT message FROM chat_messages
        WHERE model_name = ? ORDER BY timestamp DESC LIMIT ?
    ''', (model_name, MAX_HISTORY_LENGTH))
    history = cursor.fetchall()
    conn.close()
    return [msg[0] for msg in reversed(history)]

# Ensure initialization is called at the appropriate point in your flow
init_db()