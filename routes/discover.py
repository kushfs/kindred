import secrets
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, abort
from database.db import get_db
from datetime import date

discover_bp = Blueprint('discover', __name__)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def _check_csrf_json():
    """CSRF check for AJAX POST — reads from FormData field."""
    token      = session.get('_csrf', '')
    form_token = request.form.get('_csrf_token', '')
    if not token or not secrets.compare_digest(token, form_token):
        return False
    return True


@discover_bp.route('/discover')
@login_required
def discover():
    db           = get_db()
    current_user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()

    if not current_user['is_profile_complete']:
        return redirect(url_for('profile.build_profile'))

    # Reset daily likes if needed
    today = str(date.today())
    if current_user['likes_reset_date'] != today:
        db.execute('UPDATE users SET likes_given_today=0, likes_reset_date=? WHERE id=?',
                   (today, session['user_id']))
        db.commit()
        current_user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()

    remaining_likes  = max(0, 20 - (current_user['likes_given_today'] or 0))
    interested_in    = current_user['interested_in']

    query  = '''
        SELECT u.* FROM users u
        WHERE u.id != ?
          AND u.is_active = 1
          AND u.is_profile_complete = 1
          AND u.is_admin = 0
          AND u.id NOT IN (SELECT liked_id FROM likes WHERE liker_id = ?)
    '''
    params = [session['user_id'], session['user_id']]

    if interested_in and interested_in != 'Everyone':
        # Map "Men"/"Women" to gender column values
        gender_map = {'Men': 'Man', 'Women': 'Woman', 'Non-binary people': 'Non-binary'}
        gender_val = gender_map.get(interested_in)
        if gender_val:
            query  += ' AND u.gender = ?'
            params.append(gender_val)

    query += ' ORDER BY u.created_at DESC LIMIT 20'
    profiles = db.execute(query, params).fetchall()

    enriched = []
    for p in profiles:
        hobbies = db.execute('SELECT hobby_name FROM hobbies WHERE user_id=?', (p['id'],)).fetchall()
        img     = db.execute('SELECT image_path FROM hobby_images WHERE user_id=? LIMIT 1', (p['id'],)).fetchone()
        enriched.append({
            'user':          p,
            'hobbies':       [h['hobby_name'] for h in hobbies],
            'preview_image': img['image_path'] if img else None,
        })

    return render_template('discover.html',
                           profiles=enriched,
                           remaining_likes=remaining_likes,
                           current_user=current_user)


@discover_bp.route('/like/<int:liked_id>', methods=['POST'])
@login_required
def like_profile(liked_id):
    # CSRF check
    if not _check_csrf_json():
        return jsonify({'success': False, 'message': 'Security check failed.'}), 403

    if liked_id == session['user_id']:
        return jsonify({'success': False, 'message': "You can't like yourself."})

    db           = get_db()
    current_user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()

    today      = str(date.today())
    likes_today = current_user['likes_given_today'] if current_user['likes_reset_date'] == today else 0

    if likes_today >= 20:
        return jsonify({'success': False, 'message': 'Daily like limit reached. Come back tomorrow!'})

    # Idempotent — ignore duplicate likes
    existing = db.execute('SELECT id FROM likes WHERE liker_id=? AND liked_id=?',
                          (session['user_id'], liked_id)).fetchone()
    if existing:
        return jsonify({'success': False, 'message': 'Already liked!'})

    # Verify target user exists and is active
    target = db.execute('SELECT id FROM users WHERE id=? AND is_active=1', (liked_id,)).fetchone()
    if not target:
        return jsonify({'success': False, 'message': 'User not found.'})

    db.execute('INSERT INTO likes (liker_id, liked_id) VALUES (?, ?)', (session['user_id'], liked_id))
    new_count = likes_today + 1
    db.execute('UPDATE users SET likes_given_today=?, likes_reset_date=? WHERE id=?',
               (new_count, today, session['user_id']))

    # Check for mutual like → create match
    mutual = db.execute('SELECT id FROM likes WHERE liker_id=? AND liked_id=?',
                        (liked_id, session['user_id'])).fetchone()
    is_match = False
    match_id = None
    if mutual:
        u1, u2 = min(session['user_id'], liked_id), max(session['user_id'], liked_id)
        existing_match = db.execute('SELECT id FROM matches WHERE user1_id=? AND user2_id=?',
                                    (u1, u2)).fetchone()
        if not existing_match:
            db.execute('INSERT INTO matches (user1_id, user2_id) VALUES (?, ?)', (u1, u2))
        match_row = db.execute('SELECT id FROM matches WHERE user1_id=? AND user2_id=?',
                               (u1, u2)).fetchone()
        match_id = match_row['id'] if match_row else None
        is_match = True

    db.commit()

    remaining = max(0, 20 - new_count)
    return jsonify({
        'success':         True,
        'is_match':        is_match,
        'match_id':        match_id,
        'remaining_likes': remaining,
        'message':         "It's a match! 💫" if is_match else 'Liked!',
    })
