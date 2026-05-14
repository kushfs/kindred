import secrets
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from database.db import get_db

admin_bp = Blueprint('admin', __name__)

# ── decorators ────────────────────────────────────────────────────────────────

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        if not session.get('is_admin'):
            flash('Access denied.', 'error')
            return redirect(url_for('discover.discover'))
        return f(*args, **kwargs)
    return decorated

def check_csrf():
    token      = session.get('_csrf', '')
    form_token = request.form.get('_csrf_token', '')
    if not token or not secrets.compare_digest(token, form_token):
        abort(403)

# ── routes ────────────────────────────────────────────────────────────────────

@admin_bp.route('/admin')
@admin_required
def dashboard():
    db = get_db()
    stats = {
        'total_users':    db.execute("SELECT COUNT(*) FROM users WHERE is_admin=0").fetchone()[0],
        'active_users':   db.execute("SELECT COUNT(*) FROM users WHERE is_active=1 AND is_admin=0").fetchone()[0],
        'total_matches':  db.execute("SELECT COUNT(*) FROM matches").fetchone()[0],
        'total_messages': db.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
        'pending_reports':db.execute("SELECT COUNT(*) FROM reports WHERE status='pending'").fetchone()[0],
    }
    recent_users = db.execute(
        "SELECT * FROM users WHERE is_admin=0 ORDER BY created_at DESC LIMIT 10"
    ).fetchall()
    pending_reports = db.execute('''
        SELECT r.*,
               reporter.full_name AS reporter_name,
               reported.full_name AS reported_name
        FROM reports r
        JOIN users reporter ON r.reporter_id = reporter.id
        JOIN users reported  ON r.reported_id = reported.id
        WHERE r.status = 'pending'
        LIMIT 20
    ''').fetchall()
    return render_template('admin/dashboard.html',
                           stats=stats, recent_users=recent_users, reports=pending_reports)


@admin_bp.route('/admin/users')
@admin_required
def users():
    db     = get_db()
    search = request.args.get('search', '').strip()
    if search:
        like = f'%{search}%'
        all_users = db.execute(
            "SELECT * FROM users WHERE is_admin=0 AND (full_name LIKE ? OR email LIKE ? OR username LIKE ?) ORDER BY created_at DESC",
            (like, like, like)
        ).fetchall()
    else:
        all_users = db.execute(
            "SELECT * FROM users WHERE is_admin=0 ORDER BY created_at DESC"
        ).fetchall()
    return render_template('admin/users.html', users=all_users, search=search)


@admin_bp.route('/admin/user/<int:user_id>/toggle', methods=['POST'])
@admin_required
def toggle_user(user_id):
    check_csrf()
    db   = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    if user:
        new_status  = 0 if user['is_active'] else 1
        db.execute('UPDATE users SET is_active=? WHERE id=?', (new_status, user_id))
        db.commit()
        label = 'activated' if new_status else 'suspended'
        flash(f"User {user['full_name'] or user['username']} has been {label}.", 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    check_csrf()
    db   = get_db()
    user = db.execute('SELECT * FROM users WHERE id=? AND is_admin=0', (user_id,)).fetchone()
    if user:
        db.execute('DELETE FROM users WHERE id=?', (user_id,))
        db.commit()
        flash('User deleted permanently.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/admin/report/<int:report_id>/resolve', methods=['POST'])
@admin_required
def resolve_report(report_id):
    check_csrf()
    action = request.form.get('action', 'dismiss')
    if action not in ('dismiss', 'ban'):
        abort(400)

    db     = get_db()
    report = db.execute('SELECT * FROM reports WHERE id=?', (report_id,)).fetchone()
    if report:
        db.execute("UPDATE reports SET status=? WHERE id=?", (action, report_id))
        if action == 'ban':
            db.execute('UPDATE users SET is_active=0 WHERE id=? AND is_admin=0',
                       (report['reported_id'],))
        db.commit()
        flash(f'Report {"dismissed" if action=="dismiss" else "resolved — user banned"}.', 'success')
    return redirect(url_for('admin.dashboard'))
