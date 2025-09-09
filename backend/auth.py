import uuid
import time
from functools import wraps
from flask import request, session, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, SessionLocal
import secrets

def get_csrf_token():
    token = session.get('_csrf')
    if not token:
        token = uuid.uuid4().hex
        session['_csrf'] = token
    return token

# Flask after_request hook

def attach_csrf_cookie(resp):
    try:
        token = get_csrf_token()
        resp.set_cookie('X-CSRF-Token', token, httponly=False, samesite='Lax')
    except Exception:
        pass
    return resp

def require_csrf(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method in ('POST','PUT','PATCH','DELETE'):
            sent = request.headers.get('X-CSRF-Token') or request.headers.get('X-Csrf-Token')
            expected = session.get('_csrf')
            if not expected or sent != expected:
                return jsonify({'error': 'CSRF validation failed'}), 403
        return f(*args, **kwargs)
    return wrapper

RATE_LIMIT = {}
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 120

# Для REST

def rate_limited(key_suffix=''):
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            ip = request.headers.get('X-Forwarded-For', request.remote_addr) or 'ip'
            key = f"{ip}:{request.path}:{key_suffix}"
            now = int(time.time())
            bucket = RATE_LIMIT.get(key, {'start': now, 'count': 0})
            if now - bucket['start'] > RATE_LIMIT_WINDOW:
                bucket = {'start': now, 'count': 0}
            bucket['count'] += 1
            RATE_LIMIT[key] = bucket
            if bucket['count'] > RATE_LIMIT_MAX:
                return jsonify({'error': 'Too many requests'}), 429
            return f(*args, **kwargs)
        return wrapper
    return deco

# Для Socket.IO

def rate_limited_socketio(event_name='', max_per_min=60):
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            ip = request.headers.get('X-Forwarded-For', request.remote_addr) or 'ip'
            username = session.get('username', 'anon')
            key = f"SOCKET:{event_name}:{ip}:{username}"
            now = int(time.time())
            bucket = RATE_LIMIT.get(key, {'start': now, 'count': 0})
            if now - bucket['start'] > 60:
                bucket = {'start': now, 'count': 0}
            bucket['count'] += 1
            RATE_LIMIT[key] = bucket
            if bucket['count'] > max_per_min:
                return False  # Socket.IO: просто игнорировать событие
            return f(*args, **kwargs)
        return wrapper
    return deco

# Заглушки для users, session и т.д. для интеграции с app.py
users = {}

def register_user(username, password):
    db = SessionLocal()
    if db.query(User).filter_by(username=username).first():
        db.close()
        return False, 'Пользователь уже существует'
    user = User(username=username, password=generate_password_hash(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return True, user

def login_user(username, password):
    db = SessionLocal()
    user = db.query(User).filter_by(username=username).first()
    if not user:
        db.close()
        return False, 'Пользователь не найден'
    if not check_password_hash(user.password, password):
        db.close()
        return False, 'Неверный пароль'
    session['username'] = username
    session['user_id'] = user.id
    db.close()
    return True, user

def send_verification_email(user, email):
    # Здесь должна быть отправка email с токеном user.email_verification_token
    print(f"[DEBUG] Отправить письмо на {email} с токеном: {user.email_verification_token}")
    return True

def generate_email_token():
    return secrets.token_urlsafe(32)

def verify_email_token(user, token):
    return user.email_verification_token == token

def enable_2fa(user):
    # Здесь должна быть генерация TOTP-секрета и отображение QR-кода
    # user.totp_secret = ...
    pass

def verify_2fa_code(user, code):
    # Здесь должна быть проверка TOTP-кода (например, через pyotp)
    return True  # Заглушка
