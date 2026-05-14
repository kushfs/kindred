from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db
import re, secrets

auth_bp = Blueprint('auth', __name__)

# ── helpers ──────────────────────────────────────────────────────────────────

def _is_valid_email(email):
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))

def _is_safe_username(username):
    return bool(re.match(r'^[a-zA-Z0-9_.\-]{3,32}$', username))

def _get_csrf():
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_hex(32)
    return session['_csrf']

def _check_csrf():
    from flask import abort
    token = session.get('_csrf', '')
    form_token = request.form.get('_csrf_token', '')
    if not token or not secrets.compare_digest(token, form_token):
        abort(403)

@auth_bp.app_context_processor
def inject_csrf():
    return dict(csrf_token=_get_csrf)

# ── routes ───────────────────────────────────────────────────────────────────

@auth_bp.route('/')
def index():
    return render_template('landing.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('discover.discover'))

    if request.method == 'POST':
        _check_csrf()

        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please fill in all fields.', 'error')
            return render_template('login.html')

        db   = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE LOWER(email) = ? AND is_active = 1', (email,)
        ).fetchone()

        # Always run hash check to prevent timing oracle attacks
        dummy   = generate_password_hash('dummy_prevent_timing_attack')
        pw_ok   = check_password_hash(user['password_hash'] if user else dummy, password)

        if user and pw_ok:
            session.clear()  # session-fixation protection
            session['user_id']  = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])

            if not user['is_profile_complete']:
                return redirect(url_for('profile.build_profile'))
            return redirect(url_for('discover.discover'))

        flash('Invalid email or password.', 'error')

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('discover.discover'))

    if request.method == 'POST':
        _check_csrf()

        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        errors = []
        if not _is_safe_username(username):
            errors.append('Username must be 3–32 characters: letters, numbers, _ . - only.')
        if not _is_valid_email(email):
            errors.append('Please enter a valid email address.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')

        for e in errors:
            flash(e, 'error')
        if errors:
            return render_template('register.html')

        db = get_db()
        existing = db.execute(
            'SELECT id FROM users WHERE LOWER(email) = ? OR LOWER(username) = ?',
            (email, username.lower())
        ).fetchone()
        if existing:
            flash('Email or username already taken.', 'error')
            return render_template('register.html')

        pw_hash = generate_password_hash(password)   # scrypt — strong
        db.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username, email, pw_hash)
        )
        db.commit()

        user = db.execute('SELECT * FROM users WHERE LOWER(email) = ?', (email,)).fetchone()
        session.clear()
        session['user_id']  = user['id']
        session['username'] = user['username']
        session['is_admin'] = False

        flash("Welcome to Kindred! Let's build your profile.", 'success')
        return redirect(url_for('profile.build_profile'))

    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.index'))
