import os
import time
import secrets
from collections import defaultdict
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, g
from database.db import init_db, get_db
from routes.auth import auth_bp
from routes.profile import profile_bp
from routes.discover import discover_bp
from routes.matches import matches_bp
from routes.chat import chat_bp
from routes.admin import admin_bp

# ── Simple in-process rate limiter (no external deps) ────────────────────────
_rate_store = defaultdict(list)   # ip -> [timestamps]

def _is_rate_limited(ip: str, max_hits: int = 10, window: int = 60) -> bool:
    """Return True if ip exceeded max_hits in the last `window` seconds."""
    now = time.time()
    hits = [t for t in _rate_store[ip] if now - t < window]
    hits.append(now)
    _rate_store[ip] = hits
    return len(hits) > max_hits


def create_app():
    app = Flask(__name__)

    # ── Core config ──────────────────────────────────────────────────────────
    app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    app.config['UPLOAD_FOLDER']      = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024   # 16 MB

    # ── Session cookie hardening ─────────────────────────────────────────────
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    # Set SECURE to True when running behind HTTPS in production:
    app.config['SESSION_COOKIE_SECURE']   = os.environ.get('HTTPS', 'false').lower() == 'true'
    app.config['PERMANENT_SESSION_LIFETIME'] = 60 * 60 * 24 * 7  # 7 days

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # ── Database ─────────────────────────────────────────────────────────────
    with app.app_context():
        init_db()

    # ── Blueprints ───────────────────────────────────────────────────────────
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(discover_bp)
    app.register_blueprint(matches_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(admin_bp)

    # ── Security headers (added to every response) ───────────────────────────
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options']  = 'nosniff'
        response.headers['X-Frame-Options']         = 'SAMEORIGIN'
        response.headers['X-XSS-Protection']        = '1; mode=block'
        response.headers['Referrer-Policy']         = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy']      = 'geolocation=(), microphone=(), camera=()'
        # Relaxed CSP — allows Bootstrap CDN, Google Fonts, AOS
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net unpkg.com; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net unpkg.com fonts.googleapis.com; "
            "font-src 'self' fonts.gstatic.com cdn.jsdelivr.net; "
            "img-src 'self' data: blob:; "
            "connect-src 'self';"
        )
        return response

    # ── Rate limiting on auth endpoints ──────────────────────────────────────
    @app.before_request
    def rate_limit_auth():
        if request.method == 'POST' and request.endpoint in ('auth.login', 'auth.register'):
            ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
            if _is_rate_limited(ip, max_hits=15, window=60):
                flash('Too many attempts. Please wait a minute and try again.', 'error')
                return redirect(request.url)

    # ── CSRF 403 handler ─────────────────────────────────────────────────────
    @app.errorhandler(403)
    def forbidden(e):
        flash('Security check failed. Please try again.', 'error')
        return redirect(request.referrer or url_for('auth.index'))

    # ── Report route ─────────────────────────────────────────────────────────
    @app.route('/report/<int:reported_id>', methods=['POST'])
    def report_user(reported_id):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))

        import secrets as _s
        token      = session.get('_csrf', '')
        form_token = request.form.get('_csrf_token', '')
        if not token or not _s.compare_digest(token, form_token):
            abort(403)

        if reported_id == session['user_id']:
            flash('You cannot report yourself.', 'error')
            return redirect(url_for('discover.discover'))

        db     = get_db()
        reason = request.form.get('reason', '').strip()
        details = request.form.get('details', '').strip()[:1000]

        if not reason:
            flash('Please select a reason.', 'error')
            return redirect(url_for('profile.view_profile', user_id=reported_id))

        existing = db.execute(
            'SELECT id FROM reports WHERE reporter_id = ? AND reported_id = ?',
            (session['user_id'], reported_id)
        ).fetchone()
        if existing:
            flash('You have already reported this profile.', 'info')
            return redirect(url_for('profile.view_profile', user_id=reported_id))

        db.execute(
            'INSERT INTO reports (reporter_id, reported_id, reason, details) VALUES (?, ?, ?, ?)',
            (session['user_id'], reported_id, reason, details)
        )
        db.commit()
        flash('Report submitted. Our team will review it promptly.', 'success')
        return redirect(url_for('discover.discover'))

    # ── Error handlers ───────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return render_template('error.html', code=404, message='Page not found'), 404

    @app.errorhandler(413)
    def too_large(e):
        flash('File too large. Maximum size is 16 MB.', 'error')
        return redirect(request.referrer or url_for('auth.index'))

    @app.errorhandler(500)
    def server_error(e):
        return render_template('error.html', code=500, message='Something went wrong'), 500

    return app


app = create_app()

if __name__ == '__main__':
    # Never run debug=True in production
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, port=int(os.environ.get('PORT', 5000)))
