# Kindred — Personality-First Dating Platform

A modern, premium dating web app built with Flask + SQLite.
Focus: meaningful connections, not hookup culture.

---

## Quick Start (Development)

```bash
pip install flask werkzeug
python app.py
# Visit http://localhost:5000
```

**Default admin login:**
- Email: `admin@kindred.com`
- Password: `KindredAdmin2024!`
⚠️ Change this immediately after first login.

---

## Production Deployment

### 1. Set environment variables

```bash
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(64))')"
export HTTPS=true          # enables Secure cookie flag
export FLASK_DEBUG=false
```

### 2. Run with Gunicorn behind Nginx

```bash
pip install gunicorn
gunicorn -w 4 -b 127.0.0.1:5000 app:app
```

Nginx config (`/etc/nginx/sites-available/kindred`):
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    client_max_body_size 16M;

    location /static/ {
        alias /path/to/kindred/static/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. SSL (free with Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

---

## Security Features Included

| Feature | Implementation |
|---|---|
| Password hashing | werkzeug scrypt (stronger than bcrypt) |
| CSRF protection | Signed per-session token on all POST forms + AJAX |
| Session hardening | HttpOnly, SameSite=Lax, Secure (prod) |
| Session fixation | `session.clear()` on login |
| Rate limiting | In-process: 15 login attempts / 60 seconds per IP |
| Security headers | CSP, X-Frame-Options, X-Content-Type-Options, etc. |
| SQL injection | Parameterised queries throughout |
| XSS | Jinja2 auto-escaping + escapeHtml() in JS |
| Input validation | Email regex, username allowlist, length limits |
| Timing attack | Dummy hash checked even on unknown email |
| File upload | Extension allowlist, 16 MB cap |
| Foreign keys | SQLite FK enforcement ON |

---

## Folder Structure

```
kindred/
├── app.py                  # App factory, security middleware
├── requirements.txt
├── README.md
├── database/
│   └── db.py               # Schema, init, WAL mode
├── routes/
│   ├── auth.py             # Login / register / logout
│   ├── profile.py          # Profile wizard + view
│   ├── discover.py         # Browse + like
│   ├── matches.py          # Match listing
│   ├── chat.py             # Messaging
│   └── admin.py            # Admin panel
├── templates/
│   ├── base.html
│   ├── landing.html
│   ├── login.html / register.html
│   ├── profile_build.html / profile_view.html / profile_edit.html
│   ├── discover.html
│   ├── matches.html
│   ├── chat.html
│   ├── error.html
│   └── admin/
│       ├── dashboard.html
│       └── users.html
└── static/
    ├── css/
    │   ├── main.css        # Full design system
    │   └── landing.css     # Landing page styles
    ├── js/
    │   ├── main.js         # Secure apiFetch, toast, CSRF
    │   └── landing.js      # Parallax, tilt, counter animations
    └── uploads/            # User-uploaded images (gitignore this)
```

---

## Before Commercial Launch Checklist

- [ ] Change admin password
- [ ] Set `SECRET_KEY` env var (never use the default)
- [ ] Enable HTTPS + set `HTTPS=true`
- [ ] Add Privacy Policy page (required by law)
- [ ] Add Terms of Service page
- [ ] Add age verification (18+ requirement)
- [ ] GDPR: data deletion / export endpoint
- [ ] India DPDP Act compliance if serving Indian users
- [ ] Move uploads to S3/R2 for scalability
- [ ] Switch SQLite → PostgreSQL for multi-user load
- [ ] Set up daily database backups
- [ ] Add email verification on signup (Flask-Mail)
- [ ] Add password reset via email

---

## License

MIT — free to use commercially. See dependency licenses in requirements.txt.
