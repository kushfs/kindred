from flask import Blueprint, render_template, redirect, url_for, session
from database.db import get_db

matches_bp = Blueprint('matches', __name__)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

@matches_bp.route('/matches')
@login_required
def matches():
    db = get_db()
    
    rows = db.execute('''
        SELECT m.id as match_id, m.created_at as matched_at,
               u.id, u.full_name, u.age, u.profile_image, u.bio, u.music_taste, u.movie_taste,
               (SELECT content FROM messages WHERE match_id = m.id ORDER BY created_at DESC LIMIT 1) as last_message,
               (SELECT COUNT(*) FROM messages WHERE match_id = m.id AND sender_id != ? AND is_read = 0) as unread_count
        FROM matches m
        JOIN users u ON (
            CASE WHEN m.user1_id = ? THEN m.user2_id ELSE m.user1_id END = u.id
        )
        WHERE (m.user1_id = ? OR m.user2_id = ?)
        AND u.is_active = 1
        ORDER BY m.created_at DESC
    ''', (session['user_id'], session['user_id'], session['user_id'], session['user_id'])).fetchall()
    
    matches_data = []
    for row in rows:
        hobbies = db.execute('SELECT hobby_name FROM hobbies WHERE user_id = ? LIMIT 3', (row['id'],)).fetchall()
        matches_data.append({
            'match': row,
            'hobbies': [h['hobby_name'] for h in hobbies]
        })
    
    return render_template('matches.html', matches=matches_data)
