import secrets
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database.db import get_db

chat_bp = Blueprint('chat', __name__)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def _check_csrf():
    token      = session.get('_csrf', '')
    form_token = request.form.get('_csrf_token', '')
    return bool(token and secrets.compare_digest(token, form_token))


@chat_bp.route('/chat/<int:match_id>')
@login_required
def chat(match_id):
    db = get_db()
    match = db.execute(
        'SELECT * FROM matches WHERE id=? AND (user1_id=? OR user2_id=?)',
        (match_id, session['user_id'], session['user_id'])
    ).fetchone()

    if not match:
        flash('Match not found.', 'error')
        return redirect(url_for('matches.matches'))

    other_id   = match['user2_id'] if match['user1_id'] == session['user_id'] else match['user1_id']
    other_user = db.execute('SELECT * FROM users WHERE id=?', (other_id,)).fetchone()

    messages = db.execute('''
        SELECT m.*, u.full_name, u.profile_image
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.match_id = ?
        ORDER BY m.created_at ASC
    ''', (match_id,)).fetchall()

    # Mark incoming messages as read
    db.execute('UPDATE messages SET is_read=1 WHERE match_id=? AND sender_id!=?',
               (match_id, session['user_id']))
    db.commit()

    current_user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    return render_template('chat.html',
                           match=match, other_user=other_user,
                           messages=messages, current_user=current_user,
                           match_id=match_id)


@chat_bp.route('/chat/<int:match_id>/send', methods=['POST'])
@login_required
def send_message(match_id):
    if not _check_csrf():
        return jsonify({'success': False, 'message': 'Security check failed.'}), 403

    db    = get_db()
    match = db.execute(
        'SELECT * FROM matches WHERE id=? AND (user1_id=? OR user2_id=?)',
        (match_id, session['user_id'], session['user_id'])
    ).fetchone()

    if not match:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    content = request.form.get('content', '').strip()
    if not content:
        return jsonify({'success': False, 'message': 'Empty message'})
    if len(content) > 1000:
        return jsonify({'success': False, 'message': 'Message too long (max 1000 characters)'})

    db.execute('INSERT INTO messages (match_id, sender_id, content) VALUES (?, ?, ?)',
               (match_id, session['user_id'], content))
    db.commit()

    current_user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    return jsonify({
        'success':     True,
        'message': {
            'content':     content,
            'sender_name': current_user['full_name'],
            'is_own':      True,
        }
    })
