import os
import logging
import secrets
import string
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import Flask, request, redirect, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPTokenAuth
from werkzeug.exceptions import HTTPException

# --------------------------------------------------------
# 1. Configuration & Initializations
# --------------------------------------------------------

app = Flask(__name__)

# Configure structured application logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Standardize Database URIs (Fixing Render/Heroku legacy postgres:// schema)
raw_db_url = os.environ.get('DATABASE_URL', 'sqlite:///urls.db')
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

app.config.update(
    SQLALCHEMY_DATABASE_URI=raw_db_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(32))
)

db = SQLAlchemy(app)
auth = HTTPTokenAuth(scheme='Bearer')

# --------------------------------------------------------
# 2. Database Models
# --------------------------------------------------------

class URL(db.Model):
    __tablename__ = 'urls'

    id = db.Column(db.Integer, primary_key=True)
    short_code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    long_url = db.Column(db.String(2048), nullable=False) # Increased length limit for enterprise/tracking links
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    clicks = db.Column(db.Integer, default=0, nullable=False)
    last_accessed = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "short_code": self.short_code,
            "long_url": self.long_url,
            "clicks": self.clicks,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None
        }


class APIKey(db.Model):
    __tablename__ = 'api_keys'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user = db.Column(db.String(100), unique=True, nullable=False) # Enforce single key per user identity
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# --------------------------------------------------------
# 3. Core Engine & Business Logic
# --------------------------------------------------------

def generate_short_code(length: int = 6) -> str:
    """Generates a cryptographically secure random alphanumeric string."""
    pool = string.ascii_letters + string.digits
    return ''.join(secrets.choice(pool) for _ in range(length))


def generate_api_key() -> str:
    """Generates an opaque secure bearer token."""
    return secrets.token_urlsafe(32)


def is_valid_url(url: str) -> bool:
    """Validates structural integrity and constraints of target URLs."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ('http', 'https') and bool(parsed.netloc)
    except Exception:
        return False

# --------------------------------------------------------
# 4. Authentication Layer
# --------------------------------------------------------

@auth.verify_token
def verify_token(token: str) -> bool:
    """Validates incoming API bearer tokens."""
    if not token:
        return False
    
    # Constant-time comparison or exact match query to mitigate timing profiling
    api_key_record = APIKey.query.filter_by(key=token).first()
    if api_key_record:
        logger.info(f"Authenticated API request for user: '{api_key_record.user}'")
        return True
    return False

# --------------------------------------------------------
# 5. Global Error Handling
# --------------------------------------------------------

@app.errorhandler(Exception)
def handle_exception(e):
    """Intercepts unexpected failures globally and formats JSON responses if API path."""
    if request.path.startswith('/api/'):
        code = 500
        if isinstance(e, HTTPException):
            code = e.code
        logger.error(f"API Error Handled: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": getattr(e, 'description', str(e))}), code
    raise e

# --------------------------------------------------------
# 6. Web Interface View Components
# --------------------------------------------------------

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>URL Shortener</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { box-sizing: border-box; font-family: 'Segoe UI', system-ui, sans-serif; }
        body {
            margin: 0; padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; display: flex; justify-content: center; align-items: center;
        }
        .container {
            background: white; padding: 40px; border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3); max-width: 600px; width: 100%;
        }
        h2 { color: #333; text-align: center; margin-bottom: 5px; font-size: 28px; }
        .subtitle { text-align: center; color: #666; margin-bottom: 30px; font-size: 14px; }
        .input-group { display: flex; flex-direction: column; gap: 12px; }
        input {
            padding: 14px 18px; border: 2px solid #ddd; border-radius: 10px;
            font-size: 16px; transition: border-color 0.3s; width: 100%;
        }
        input:focus { outline: none; border-color: #667eea; }
        .btn-primary {
            padding: 14px 18px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; border: none; border-radius: 10px; font-size: 16px;
            cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; width: 100%; font-weight: 600;
        }
        .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4); }
        .result { margin-top: 25px; background: #f8f9fa; padding: 20px; border-radius: 12px; border: 2px solid #e9ecef; }
        .result p { margin: 0 0 10px 0; word-break: break-all; }
        .result a { color: #667eea; text-decoration: none; font-weight: bold; }
        .result a:hover { text-decoration: underline; }
        .copy-btn {
            background: #28a745; color: white; border: none; padding: 8px 20px;
            border-radius: 6px; cursor: pointer; font-size: 14px; transition: background 0.3s;
        }
        .copy-btn:hover { background: #218838; }
        .error { color: #dc3545; margin-top: 15px; padding: 12px; background: #f8d7da; border-radius: 8px; border: 1px solid #f5c6cb; }
        .stats { display: flex; justify-content: space-around; margin: 25px 0 15px 0; padding: 15px; background: #f8f9fa; border-radius: 10px; }
        .stat-item { text-align: center; }
        .stat-number { font-size: 24px; font-weight: bold; color: #333; }
        .stat-label { font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
        .footer { text-align: center; margin-top: 20px; color: #999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🔗 URL Shortener</h2>
        <p class="subtitle">Make your links shorter and shareable</p>

        <form method="post" class="input-group">
            <input type="url" name="url" placeholder="Enter long URL (e.g., https://example.com)" required>
            <button type="submit" class="btn-primary">🚀 Shorten URL</button>
        </form>

        {% if short_url %}
        <div class="result">
            <p><strong>Short URL:</strong></p>
            <p><a href="{{ short_url }}" target="_blank" rel="noopener">{{ short_url }}</a></p>
            <button class="copy-btn" onclick="copyToClipboard('{{ short_url }}')">📋 Copy Link</button>
        </div>
        {% endif %}

        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}

        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">4</div>
                <div class="stat-label">Active Deployments</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{{ total_clicks }}</div>
                <div class="stat-label">Total Redirections</div>
            </div>
        </div>

        <div class="footer">
            Made with ❤️ by Md Jishan
        </div>
    </div>

    <script>
        function copyToClipboard(text) {
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text).then(() => alert('✅ Copied to clipboard!'));
            } else {
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed'; // Avoid scrolling view down
                document.body.appendChild(textarea);
                textarea.select();
                try {
                    document.execCommand('copy');
                    alert('✅ Copied to clipboard!');
                } catch (err) {
                    alert('❌ Failed to copy link');
                }
                document.body.removeChild(textarea);
            }
        }
    </script>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def home():
    error = None
    short_url = None
    
    # Calculate sum aggregation safely
    total_clicks = db.session.query(db.func.sum(URL.clicks)).scalar() or 0

    if request.method == 'POST':
        long_url = request.form.get('url', '').strip()

        if not long_url:
            error = "⚠️ URL payload missing or empty."
        elif not is_valid_url(long_url):
            error = "⚠️ Invalid link format. Make sure it contains 'http://' or 'https://'."
        else:
            # Check if this exact URL was already indexed
            existing_record = URL.query.filter_by(long_url=long_url).first()
            
            if existing_record:
                short_code = existing_record.short_code
                logger.info(f"Resolved existing entry for: {long_url}")
            else:
                # Collision prevention loop
                while True:
                    code = generate_short_code()
                    if not URL.query.filter_by(short_code=code).first():
                        break
                
                new_entry = URL(short_code=code, long_url=long_url)
                db.session.add(new_entry)
                db.session.commit()
                short_code = code
                logger.info(f"Shortened raw mapping created: {long_url} -> {code}")

            short_url = request.host_url + short_code

    return render_template_string(HTML_TEMPLATE, short_url=short_url, error=error, total_clicks=total_clicks)


@app.route('/<short_code>')
def redirect_to_url(short_code):
    """Performs HTTP 302 redirects to indexed locations while collecting telemetry."""
    url_entry = URL.query.filter_by(short_code=short_code).first()
    
    if url_entry:
        url_entry.clicks += 1
        url_entry.last_accessed = datetime.now(timezone.utc)
        db.session.commit()
        logger.info(f"Redirection Event: {short_code} (Total tracking counter: {url_entry.clicks})")
        return redirect(url_entry.long_url)
        
    return render_template_string('''
        <div style="font-family: sans-serif; text-align:center; margin-top: 100px;">
            <h2>🔗 URL Resource Missing</h2>
            <p>The routing signature <strong>{{ code }}</strong> could not be matching a mapping entry.</p>
            <a href="/" style="color: #667eea; font-weight:bold;">Return Home</a>
        </div>
    ''', code=short_code), 404

# --------------------------------------------------------
# 7. Restful API Resource Routing
# --------------------------------------------------------

@app.route('/api/shorten', methods=['POST'])
@auth.login_required
def api_shorten():
    data = request.get_json(silent=True)
    if not data or 'url' not in data:
        return jsonify({"success": false, "error": "Request body must contain valid JSON specifying 'url'."}), 400

    long_url = data['url'].strip()
    if not is_valid_url(long_url):
        return jsonify({"success": false, "error": "URL target invalid. Prefix schemes must utilize HTTP or HTTPS protocols."}), 400

    existing_record = URL.query.filter_by(long_url=long_url).first()
    if existing_record:
        code = existing_record.short_code
    else:
        while True:
            code = generate_short_code()
            if not URL.query.filter_by(short_code=code).first():
                break
        new_entry = URL(short_code=code, long_url=long_url)
        db.session.add(new_entry)
        db.session.commit()
        logger.info(f"API Engine Ingestion: {long_url} mapped to {code}")

    return jsonify({
        "success": True,
        "short_code": code,
        "short_url": request.host_url + code,
        "long_url": long_url
    }), 201


@app.route('/api/expand/<short_code>', methods=['GET'])
@auth.login_required
def api_expand(short_code):
    url_entry = URL.query.filter_by(short_code=short_code).first()
    if url_entry:
        return jsonify({
            "success": True,
            "data": url_entry.to_dict()
        })
    return jsonify({"success": False, "error": f"Short target definition '{short_code}' not found."}), 404


@app.route('/api/stats', methods=['GET'])
@auth.login_required
def api_stats():
    total_urls = URL.query.count()
    total_clicks = db.session.query(db.func.sum(URL.clicks)).scalar() or 0
    recent_records = URL.query.order_by(URL.created_at.desc()).limit(5).all()

    return jsonify({
        "success": True,
        "stats": {
            "total_urls": total_urls,
            "total_clicks": total_clicks,
            "recent": [item.to_dict() for item in recent_records]
        }
    })


@app.route('/api/keys', methods=['POST'])
def create_api_key():
    data = request.get_json(silent=True) or {}
    user_identity = data.get('user', '').strip() or 'default_user'

    existing_key = APIKey.query.filter_by(user=user_identity).first()
    if existing_key:
        return jsonify({"success": False, "error": f"An active key allocation already exists for identity '{user_identity}'"}), 400

    raw_token = generate_api_key()
    new_api_key = APIKey(key=raw_token, user=user_identity)
    
    db.session.add(new_api_key)
    db.session.commit()
    logger.info(f"Provisioned token authority for identity context: '{user_identity}'")

    return jsonify({
        "success": True,
        "api_key": raw_token,
        "user": user_identity,
        "message": "Store this credential securely. It cannot be recovered later."
    }), 201

# --------------------------------------------------------
# 8. Execution Context & Schema Setup
# --------------------------------------------------------

with app.app_context():
    db.create_all()
    # Check-and-provision default sandbox keys
    if not APIKey.query.first():
        fallback_token = generate_api_key()
        sandbox_user = APIKey(key=fallback_token, user="default_user")
        db.session.add(sandbox_user)
        db.session.commit()
        
        print("\n" + "="*70)
        print(f"🔑 PROVISIONED INITIAL ACCESS KEY: {fallback_token}")
        print(f"📌 Postman Header Authorization Setup:")
        print(f"   Authorization: Bearer {fallback_token}")
        print("="*70 + "\n")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
