import sqlite3
import os
from flask import g, current_app

DATABASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'kindred.db')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')   # better concurrency
        g.db.execute('PRAGMA foreign_keys=ON')    # enforce FK constraints
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')

    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            age INTEGER,
            gender TEXT,
            interested_in TEXT,
            bio TEXT,
            profile_image TEXT,
            music_taste TEXT,
            movie_taste TEXT,
            favorite_artists TEXT,
            favorite_movies TEXT,
            is_admin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            is_profile_complete INTEGER DEFAULT 0,
            likes_given_today INTEGER DEFAULT 0,
            likes_reset_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS hobbies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            hobby_name TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS hobby_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            hobby_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            caption TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (hobby_id) REFERENCES hobbies(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            liker_id INTEGER NOT NULL,
            liked_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(liker_id, liked_id),
            FOREIGN KEY (liker_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (liked_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user1_id, user2_id),
            FOREIGN KEY (user1_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (user2_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER NOT NULL,
            reported_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            details TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (reported_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL,
            attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_likes_liker ON likes(liker_id);
        CREATE INDEX IF NOT EXISTS idx_likes_liked ON likes(liked_id);
        CREATE INDEX IF NOT EXISTS idx_matches_users ON matches(user1_id, user2_id);
        CREATE INDEX IF NOT EXISTS idx_messages_match ON messages(match_id);
    ''')
    conn.commit()

    # Create default admin using werkzeug secure hash
    from werkzeug.security import generate_password_hash
    admin_hash = generate_password_hash('KindredAdmin2024!')
    try:
        conn.execute('''INSERT OR IGNORE INTO users
            (username, email, password_hash, full_name, is_admin, is_active, is_profile_complete)
            VALUES (?, ?, ?, ?, 1, 1, 1)''',
            ('admin', 'admin@kindred.com', admin_hash, 'Admin'))
        conn.commit()
    except Exception:
        pass

    conn.close()
    current_app.teardown_appcontext(close_db)
