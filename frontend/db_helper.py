import sqlite3
import os

DB_FILE = 'comments.db'

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Create comments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manga_id TEXT NOT NULL,
            manga_title TEXT NOT NULL,
            chapter_id TEXT,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Create notifications table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            manga_id TEXT NOT NULL,
            manga_title TEXT NOT NULL,
            chapter_id TEXT,
            username TEXT NOT NULL,
            content TEXT NOT NULL,
            target_user TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_comment(manga_id, manga_title, chapter_id, username, email, content):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Insert comment
    cursor.execute('''
        INSERT INTO comments (manga_id, manga_title, chapter_id, username, email, content)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (manga_id, manga_title, chapter_id, username, email, content))
    
    comment_id = cursor.lastrowid
    snippet = content[:60] + "..." if len(content) > 60 else content
    
    # 2. Notify Admin
    cursor.execute('''
        INSERT INTO notifications (type, manga_id, manga_title, chapter_id, username, content, target_user)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('new_comment', manga_id, manga_title, chapter_id, username, snippet, 'admin'))
    
    # 3. Notify all other users who commented on this manga
    cursor.execute('''
        SELECT DISTINCT email FROM comments 
        WHERE manga_id = ? AND email != ?
    ''', (manga_id, email))
    
    other_users = [row['email'] for row in cursor.fetchall()]
    for u_email in other_users:
        cursor.execute('''
            INSERT INTO notifications (type, manga_id, manga_title, chapter_id, username, content, target_user)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('thread_reply', manga_id, manga_title, chapter_id, username, snippet, u_email))
        
    conn.commit()
    conn.close()
    return comment_id

def get_comments(manga_id, chapter_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if chapter_id:
        cursor.execute('''
            SELECT * FROM comments 
            WHERE manga_id = ? AND chapter_id = ?
            ORDER BY created_at DESC
        ''', (manga_id, chapter_id))
    else:
        cursor.execute('''
            SELECT * FROM comments 
            WHERE manga_id = ?
            ORDER BY created_at DESC
        ''', (manga_id,))
    
    comments = []
    for row in cursor.fetchall():
        comments.append({
            "id": row["id"],
            "manga_id": row["manga_id"],
            "manga_title": row["manga_title"],
            "chapter_id": row["chapter_id"],
            "username": row["username"],
            "email": row["email"],
            "content": row["content"],
            "created_at": row["created_at"]
        })
    conn.close()
    return comments

def get_notifications(target_user):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM notifications 
        WHERE target_user = ?
        ORDER BY created_at DESC
        LIMIT 50
    ''', (target_user,))
    
    notifications = []
    for row in cursor.fetchall():
        notifications.append({
            "id": row["id"],
            "type": row["type"],
            "manga_id": row["manga_id"],
            "manga_title": row["manga_title"],
            "chapter_id": row["chapter_id"],
            "username": row["username"],
            "content": row["content"],
            "is_read": row["is_read"],
            "created_at": row["created_at"]
        })
    conn.close()
    return notifications

def mark_notification_as_read(notification_id, target_user=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if notification_id == "all":
        cursor.execute('''
            UPDATE notifications 
            SET is_read = 1 
            WHERE target_user = ?
        ''', (target_user,))
    else:
        try:
            nid = int(notification_id)
            cursor.execute('''
                UPDATE notifications 
                SET is_read = 1 
                WHERE id = ?
            ''', (nid,))
        except ValueError:
            pass
    conn.commit()
    conn.close()
