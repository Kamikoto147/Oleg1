from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import uuid
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Response
import time
from functools import wraps
from flask import make_response
from auth import rate_limited_socketio
from emojis_stickers_polls import create_custom_emoji, get_guild_emojis, create_sticker, get_guild_stickers, create_poll, vote_poll, get_poll, get_poll_by_message, get_user_poll_votes, delete_custom_emoji, delete_sticker
from cache import cache_channel_messages, get_cached_channel_messages, invalidate_channel_cache, start_cache_cleanup

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config['SECRET_KEY'] = 'oleg_messenger_secret_key_2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size
socketio = SocketIO(app, cors_allowed_origins="*")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')

users = {}
rooms = {}
messages = {}
friendships = {}
friend_requests_in = {}
friend_requests_out = {}

guilds = {}
member_of_guild = {}
invites = {}
threads_index = {}

# Admins set (usernames)
admins = set()


def _ensure_user_sets(username):
    if username not in friendships:
        friendships[username] = set()
    if username not in friend_requests_in:
        friend_requests_in[username] = set()
    if username not in friend_requests_out:
        friend_requests_out[username] = set()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _create_default_guild_for(username: str) -> str:
    gid = str(uuid.uuid4())
    guilds[gid] = {
        'id': gid,
        'name': f"{username}'s Server",
        'owner': username,
        'created_at': datetime.now().isoformat(),
        'channels': {}
    }
    cid = str(uuid.uuid4())
    guilds[gid]['channels'][cid] = {'id': cid, 'name': 'general', 'created_at': datetime.now().isoformat(), 'read_only': False}
    member_of_guild[gid] = set([username])
    save_data()
    return gid


def serialize_data():
    return {
        'users': users,
        'rooms': rooms,
        'messages': messages,
        'friendships': {k: list(v) for k, v in friendships.items()},
        'friend_requests_in': {k: list(v) for k, v in friend_requests_in.items()},
        'friend_requests_out': {k: list(v) for k, v in friend_requests_out.items()},
        'guilds': guilds,
        'member_of_guild': {gid: list(members) for gid, members in member_of_guild.items()},
        'invites': invites,
        'threads_index': {f"{gid}:{cid}": val for (gid, cid), val in threads_index.items()}
    }


def save_data():
    try:
        data = serialize_data()
        data['admins'] = list(admins)
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        print('[PERSIST] save failed:', e)


def load_data():
    global users, rooms, messages, friendships, friend_requests_in, friend_requests_out, guilds, member_of_guild, invites, threads_index, admins
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        users = data.get('users', {})
        rooms = data.get('rooms', {})
        messages = data.get('messages', {})
        friendships = {k: set(v) for k, v in data.get('friendships', {}).items()}
        friend_requests_in = {k: set(v) for k, v in data.get('friend_requests_in', {}).items()}
        friend_requests_out = {k: set(v) for k, v in data.get('friend_requests_out', {}).items()}
        guilds = data.get('guilds', {})
        member_of_guild = {gid: set(members) for gid, members in data.get('member_of_guild', {}).items()}
        invites = data.get('invites', {})
        threads_index = {}
        for key, val in data.get('threads_index', {}).items():
            try:
                gid, cid = key.split(':', 1)
                threads_index[(gid, cid)] = val
            except Exception:
                continue
        admins = set(data.get('admins', []))
    except Exception as e:
        print('[PERSIST] load failed:', e)


# Remove unsupported before_first_request and load data at startup
# @app.before_first_request
# def _init_load():
#     load_data()
load_data()


@app.route('/')
def index():
    return render_template('index.html')


# CSRF simple token
def get_csrf_token():
    token = session.get('_csrf')
    if not token:
        token = uuid.uuid4().hex
        session['_csrf'] = token
    return token

@app.after_request
def attach_csrf_cookie(resp):
    # Set CSRF token as cookie for frontend to read and echo in header
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

# Simple rate limiting per-IP+endpoint
RATE_LIMIT = {}
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 120

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

# Apply protections
@app.route('/api/register', methods=['POST'])
@rate_limited('auth')
@require_csrf
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Имя пользователя и пароль обязательны'}), 400
    if username in users:
        return jsonify({'error': 'Пользователь уже существует'}), 400
    user_id = str(uuid.uuid4())
    users[username] = {
        'id': user_id,
        'username': username,
        'password': generate_password_hash(password),
        'online': True,
        'joined_at': datetime.now().isoformat(),
        'avatar_url': None,
        'bio': '',
        'status_text': ''
    }
    
    # Создаем пользователя в базе данных
    try:
        from auth import register_user
        success, user = register_user(username, password)
        if success:
            users[username]['db_id'] = user.id
    except Exception as e:
        print(f"Ошибка создания пользователя в БД: {e}")
    
    _ensure_user_sets(username)
    # Promote first user to admin if none exists
    if not admins:
        admins.add(username)
    gid = _create_default_guild_for(username)
    socketio.emit('guilds_updated', {'guild_id': gid})
    session['username'] = username
    session['user_id'] = user_id
    save_data()
    return jsonify({'success': True, 'user_id': user_id, 'username': username})
    

@app.route('/api/login', methods=['POST'])
@rate_limited('auth')
@require_csrf
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Имя пользователя и пароль обязательны'}), 400
    # Проверяем пользователя в памяти
    if username not in users:
        # Проверяем пользователя в базе данных
        try:
            from auth import login_user
            success, user = login_user(username, password)
            if success:
                # Создаем пользователя в памяти на основе данных из БД
                users[username] = {
                    'id': str(user.id),
                    'username': username,
                    'password': user.password,
                    'online': True,
                    'joined_at': user.created_at.isoformat() if user.created_at else datetime.now().isoformat(),
                    'avatar_url': None,
                    'bio': user.bio or '',
                    'status_text': user.status or '',
                    'db_id': user.id
                }
                _ensure_user_sets(username)
            else:
                return jsonify({'error': user}), 401
        except Exception as e:
            print(f"Ошибка проверки пользователя в БД: {e}")
            return jsonify({'error': 'Пользователь не найден'}), 404
    else:
        # Проверяем пароль для пользователя из памяти
        if not check_password_hash(users[username]['password'], password):
            return jsonify({'error': 'Неверный пароль'}), 401
    
    users[username]['online'] = True
    session['username'] = username
    session['user_id'] = users[username]['id']
    _ensure_user_sets(username)
    owns_any = any(g.get('owner') == username for g in guilds.values())
    is_member_any = any(username in (member_of_guild.get(gid) or set()) for gid in guilds.keys())
    if not owns_any and not is_member_any:
        gid = _create_default_guild_for(username)
        socketio.emit('guilds_updated', {'guild_id': gid})
    save_data()
    return jsonify({'success': True, 'user_id': users[username]['id'], 'username': username})


# In all mutation endpoints, call save_data() after updates
# Upload avatar
@app.route('/api/upload_avatar', methods=['POST'])
@require_csrf
@rate_limited('upload')
def upload_avatar():
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    if 'avatar' not in request.files:
        return jsonify({'error': 'Файл не выбран'}), 400
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}):
        return jsonify({'error': 'Допустимы только изображения'}), 400
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    upload_folder = app.config['UPLOAD_FOLDER']
    abs_upload_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), upload_folder))
    if not os.path.exists(abs_upload_folder):
        os.makedirs(abs_upload_folder)
    file_path = os.path.join(abs_upload_folder, unique_filename)
    file.save(file_path)
    username = session['username']
    users[username]['avatar_url'] = f'/uploads/{unique_filename}'
    save_data()
    socketio.emit('user_profile_updated', {'username': username, 'avatar_url': users[username]['avatar_url']})
    return jsonify({'success': True, 'avatar_url': users[username]['avatar_url']})


@app.route('/api/profile', methods=['GET', 'POST'])
@rate_limited('profile')
@require_csrf
def profile():
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    username = session['username']
    if request.method == 'GET':
        user = users.get(username)
        return jsonify({'username': user['username'], 'avatar_url': user.get('avatar_url'), 'bio': user.get('bio', ''), 'status_text': user.get('status_text', '')})
    else:
        data = request.get_json(force=True, silent=True) or {}
        bio = data.get('bio')
        status_text = data.get('status_text')
        changed = {}
        if bio is not None:
            users[username]['bio'] = str(bio)[:200]
            changed['bio'] = users[username]['bio']
        if status_text is not None:
            users[username]['status_text'] = str(status_text)[:80]
            changed['status_text'] = users[username]['status_text']
        if changed:
            changed['username'] = username
            save_data()
            socketio.emit('user_profile_updated', changed)
        return jsonify({'success': True})


# Friends endpoints: add save_data() where state mutates
@app.route('/api/friends/request', methods=['POST'])
@require_csrf
@rate_limited('friends')
def friends_request():
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    me = session['username']
    data = request.get_json(force=True)
    print(f"[DEBUG] Friend request from {me} to {data}")
    to_user = (data.get('to') or '').strip()
    if not to_user or to_user == me:
        print(f"[DEBUG] Invalid user: {to_user} (me: {me})")
        return jsonify({'error': 'Неверный пользователь'}), 400
    if to_user not in users:
        print(f"[DEBUG] User not found: {to_user}")
        return jsonify({'error': 'Пользователь не найден'}), 404
    _ensure_user_sets(me)
    _ensure_user_sets(to_user)
    if to_user in friendships[me]:
        return jsonify({'error': 'Пользователь уже в друзьях'}), 400
    if to_user in friend_requests_out[me]:
        return jsonify({'error': 'Заявка уже отправлена'}), 400
    if me in friend_requests_out[to_user] or me in friend_requests_in[me]:
        friendships[me].add(to_user)
        friendships[to_user].add(me)
        friend_requests_in[to_user].discard(me)
        friend_requests_out[me].discard(to_user)
        friend_requests_in[me].discard(to_user)
        friend_requests_out[to_user].discard(me)
        save_data()
        socketio.emit('friends_update', {'username': me})
        socketio.emit('friends_update', {'username': to_user})
        return jsonify({'success': True, 'auto_accepted': True})
    friend_requests_out[me].add(to_user)
    friend_requests_in[to_user].add(me)
    save_data()
    socketio.emit('friends_update', {'username': to_user})
    return jsonify({'success': True})


@app.route('/api/friends/cancel', methods=['POST'])
@require_csrf
@rate_limited('friends')
def friends_cancel():
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    me = session['username']
    data = request.get_json(force=True)
    to_user = (data.get('to') or '').strip()
    if not to_user:
        return jsonify({'error': 'Неверный пользователь'}), 400
    _ensure_user_sets(me)
    _ensure_user_sets(to_user)
    friend_requests_out[me].discard(to_user)
    friend_requests_in[to_user].discard(me)
    save_data()
    socketio.emit('friends_update', {'username': to_user})
    return jsonify({'success': True})


@app.route('/api/friends/accept', methods=['POST'])
@require_csrf
@rate_limited('friends')
def friends_accept():
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    me = session['username']
    data = request.get_json(force=True)
    from_user = (data.get('from') or '').strip()
    if not from_user:
        return jsonify({'error': 'Неверный пользователь'}), 400
    if from_user not in users:
        return jsonify({'error': 'Пользователь не найден'}), 404
    _ensure_user_sets(me)
    _ensure_user_sets(from_user)
    if from_user not in friend_requests_in[me]:
        return jsonify({'error': 'Нет входящей заявки'}), 400
    friend_requests_in[me].discard(from_user)
    friend_requests_out[from_user].discard(me)
    friendships[me].add(from_user)
    friendships[from_user].add(me)
    save_data()
    socketio.emit('friends_update', {'username': me})
    socketio.emit('friends_update', {'username': from_user})
    return jsonify({'success': True})


@app.route('/api/friends/decline', methods=['POST'])
@require_csrf
@rate_limited('friends')
def friends_decline():
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    me = session['username']
    data = request.get_json(force=True)
    from_user = (data.get('from') or '').strip()
    if not from_user:
        return jsonify({'error': 'Неверный пользователь'}), 400
    _ensure_user_sets(me)
    _ensure_user_sets(from_user)
    friend_requests_in[me].discard(from_user)
    friend_requests_out[from_user].discard(me)
    save_data()
    socketio.emit('friends_update', {'username': me})
    return jsonify({'success': True})


@app.route('/api/friends/remove', methods=['POST'])
@require_csrf
@rate_limited('friends')
def friends_remove():
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    me = session['username']
    data = request.get_json(force=True)
    other = (data.get('user') or '').strip()
    if not other:
        return jsonify({'error': 'Неверный пользователь'}), 400
    _ensure_user_sets(me)
    _ensure_user_sets(other)
    friendships[me].discard(other)
    friendships[other].discard(me)
    save_data()
    socketio.emit('friends_update', {'username': me})
    socketio.emit('friends_update', {'username': other})
    return jsonify({'success': True})


# --- Уведомление о создании гильдии ---
@app.route('/api/guilds', methods=['GET', 'POST'])
@rate_limited('guilds')
@require_csrf
def api_guilds():
    if 'username' not in session:
        return jsonify({'error': 'not_logged_in'}), 401
    if request.method == 'POST':
        name = request.json.get('name')
        if not name:
            return jsonify({'error': 'no_name'}), 400
        gid = str(uuid.uuid4())
        guilds[gid] = {'id': gid, 'name': name, 'owner': session['username'], 'created_at': datetime.now().isoformat(), 'channels': {}}
        try:
            from guilds import create_guild
            guild_id, guild = create_guild(name, session['username'])
            if guild_id:
                guilds[gid]['db_id'] = guild_id
                from guilds import create_channel
                channel_id, channel = create_channel(guild_id, 'general')
                if channel_id:
                    cid = str(uuid.uuid4())
                    guilds[gid]['channels'][cid] = {'id': cid, 'name': 'general', 'created_at': datetime.now().isoformat(), 'read_only': False, 'db_id': channel_id}
                else:
                    cid = str(uuid.uuid4())
                    guilds[gid]['channels'][cid] = {'id': cid, 'name': 'general', 'created_at': datetime.now().isoformat(), 'read_only': False}
            else:
                cid = str(uuid.uuid4())
                guilds[gid]['channels'][cid] = {'id': cid, 'name': 'general', 'created_at': datetime.now().isoformat(), 'read_only': False}
        except Exception as e:
            print(f"Ошибка создания гильдии в БД: {e}")
            cid = str(uuid.uuid4())
            guilds[gid]['channels'][cid] = {'id': cid, 'name': 'general', 'created_at': datetime.now().isoformat(), 'read_only': False}
        member_of_guild[gid] = set([session['username']])
        save_data()
        socketio.emit('guilds_updated', {'guild_id': gid})
        # --- уведомление ---
        socketio.emit('notification', {'message': f'Создана новая гильдия: {name}'})
        return jsonify({'success': True, 'id': gid})
    else:
        me = session['username']
        result = []
        for gid, g in guilds.items():
            members = member_of_guild.get(gid) or set()
            if me == g['owner'] or me in members:
                result.append({'id': g['id'], 'name': g['name'], 'owner': g['owner'], 'created_at': g['created_at']})
        return jsonify(result)


# --- Уведомление о создании канала ---
@app.route('/api/guilds/<gid>/channels', methods=['GET', 'POST'])
@rate_limited('channels')
@require_csrf
def api_guild_channels(gid):
    if 'username' not in session:
        return jsonify({'error': 'not_logged_in'}), 401
    if gid not in guilds:
        return jsonify({'error': 'guild_not_found'}), 404
    me = session['username']
    members = member_of_guild.get(gid) or set()
    if me != guilds[gid]['owner'] and me not in members:
        return jsonify({'error': 'Нет доступа'}), 403
    if request.method == 'GET':
        channels = [{'id': c['id'], 'name': c['name'], 'read_only': c.get('read_only', False)} for c in guilds[gid]['channels'].values()]
        return jsonify(channels)
    else:
        if guilds[gid]['owner'] != me:
            return jsonify({'error': 'Недостаточно прав'}), 403
        data = request.get_json(force=True)
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'Имя канала обязательно'}), 400
        cid = str(uuid.uuid4())
        guilds[gid]['channels'][cid] = {'id': cid, 'name': name, 'created_at': datetime.now().isoformat(), 'read_only': False}
        
        # Создаем канал в базе данных
        try:
            from guilds import create_channel
            channel_id, channel = create_channel(int(gid), name)
            if channel_id:
                # Обновляем ID канала в памяти на ID из БД
                guilds[gid]['channels'][cid]['db_id'] = channel_id
        except Exception as e:
            print(f"Ошибка создания канала в БД: {e}")
        
        save_data()
        socketio.emit('channels_updated', {'guild_id': gid, 'channel_id': cid})
        # --- уведомление ---
        socketio.emit('notification', {'message': f'В гильдии "{guilds[gid]["name"]}" создан новый канал: {name}'})
        return jsonify({'success': True, 'id': cid})


@app.route('/api/guilds/<gid>/channels/<cid>/settings', methods=['POST'])
@rate_limited('channels')
@require_csrf
def api_channel_settings(gid, cid):
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    if gid not in guilds or cid not in guilds[gid]['channels']:
        return jsonify({'error': 'Не найдено'}), 404
    if guilds[gid]['owner'] != session['username']:
        return jsonify({'error': 'Недостаточно прав'}), 403
    data = request.get_json(force=True)
    if 'read_only' in data:
        guilds[gid]['channels'][cid]['read_only'] = bool(data['read_only'])
        save_data()
        socketio.emit('channel_settings_updated', {'guild_id': gid, 'channel_id': cid})
    return jsonify({'success': True})

# Роли и права

@app.route('/api/guilds/<gid>/roles', methods=['GET', 'POST'])
@require_csrf
@rate_limited('guilds')
def api_guild_roles(gid):
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    me = session['username']
    if gid not in guilds:
        return jsonify({'error': 'Гильдия не найдена'}), 404
    if me != guilds[gid]['owner']:
        return jsonify({'error': 'Нет доступа'}), 403
    
    if request.method == 'GET':
        from guilds import get_roles
        roles = get_roles(gid)
        return jsonify([{'id': r.id, 'name': r.name, 'color': r.color, 'position': r.position} for r in roles])
    
    elif request.method == 'POST':
        data = request.get_json(force=True)
        name = data.get('name', '').strip()
        color = data.get('color', '#99aab5')
        if not name:
            return jsonify({'error': 'Название роли обязательно'}), 400
        from guilds import create_role
        role_id, role = create_role(gid, name, color)
        if not role_id:
            return jsonify({'error': role}), 400
        return jsonify({'success': True, 'role_id': role_id})

@app.route('/api/guilds/<gid>/categories', methods=['GET', 'POST'])
@require_csrf
@rate_limited('guilds')
def api_guild_categories(gid):
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    me = session['username']
    if gid not in guilds:
        return jsonify({'error': 'Гильдия не найдена'}), 404
    if me != guilds[gid]['owner']:
        return jsonify({'error': 'Нет доступа'}), 403
    
    if request.method == 'GET':
        from guilds import get_categories
        categories = get_categories(gid)
        return jsonify([{'id': c.id, 'name': c.name, 'position': c.position} for c in categories])
    
    elif request.method == 'POST':
        data = request.get_json(force=True)
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'error': 'Название категории обязательно'}), 400
        from guilds import create_category
        cat_id, category = create_category(gid, name)
        if not cat_id:
            return jsonify({'error': category}), 400
        return jsonify({'success': True, 'category_id': cat_id})


@app.route('/api/guilds/<gid>/invites', methods=['POST'])
@rate_limited('invites')
@require_csrf
def api_create_invite(gid):
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    if gid not in guilds:
        return jsonify({'error': 'Сервер не найден'}), 404
    if guilds[gid]['owner'] != session['username']:
        return jsonify({'error': 'Недостаточно прав'}), 403
    code = uuid.uuid4().hex[:8]
    invites[code] = gid
    save_data()
    return jsonify({'success': True, 'code': code})


@app.route('/api/invites/join', methods=['POST'])
@rate_limited('invites')
@require_csrf
def api_join_invite():
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    data = request.get_json(force=True)
    code = (data.get('code') or '').strip()
    gid = invites.get(code)
    if not gid or gid not in guilds:
        return jsonify({'error': 'Неверный инвайт'}), 400
    members = member_of_guild.get(gid) or set()
    if session['username'] not in members:
        members.add(session['username'])
        member_of_guild[gid] = members
        save_data()
        socketio.emit('guilds_updated', {'guild_id': gid})
    return jsonify({'success': True, 'guild_id': gid})


# Rooms (legacy)
@app.route('/api/rooms')
def get_rooms():
    public_rooms = [r for r in rooms.keys() if not str(r).startswith('dm:')]
    return jsonify(public_rooms)


# Upload файлов для сообщений
@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не выбран'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        upload_folder = app.config['UPLOAD_FOLDER']
        abs_upload_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), upload_folder))
        if not os.path.exists(abs_upload_folder):
            os.makedirs(abs_upload_folder)
        file_path = os.path.join(abs_upload_folder, unique_filename)
        file.save(file_path)
        return jsonify({'success': True, 'url': f'/uploads/{unique_filename}', 'filename': filename})
    
    return jsonify({'error': 'Недопустимый тип файла'}), 400


# Serve uploaded files
@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    upload_folder = app.config['UPLOAD_FOLDER']
    abs_upload_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), upload_folder))
    return send_from_directory(abs_upload_folder, filename)


# Socket.IO события
# Fix connect handler signature and safe status updates
@socketio.on('connect')
def handle_connect(auth=None):
    username = session.get('username')
    if username and username in users:
        users[username]['online'] = True
        _ensure_user_sets(username)
        socketio.emit('user_status', {'username': username, 'online': True})


@socketio.on('disconnect')
def handle_disconnect():
    username = session.get('username')
    if username and username in users:
        users[username]['online'] = False
        socketio.emit('user_status', {'username': username, 'online': False})


@socketio.on('join_room')
def handle_join_room(data):
    room = data['room']
    username = session.get('username')
    
    if username:
        print(f"[DEBUG] join_room: user={username} room={room}")
        is_new = room not in messages
        join_room(room)
        if room not in messages:
            messages[room] = []
        emit('room_joined', {'room': room, 'username': username}, room=room)
        if is_new and not str(room).startswith('dm:') and not str(room).startswith('g:'):
            socketio.emit('rooms_updated', {'room': room})


@socketio.on('leave_room')
def handle_leave_room(data):
    room = data['room']
    username = session.get('username')
    
    if username:
        leave_room(room)
        emit('room_left', {'room': room, 'username': username}, room=room)


@socketio.on('send_message')
@rate_limited_socketio('send_message', max_per_min=30)
def handle_message(data):
    room = data['room']
    message = data['message']
    username = session.get('username')
    
    if not username:
        return
    
    print(f"[DEBUG] send_message: user={username} room={room} message={message}")
    # Проверка прав на канал (read_only) для каналов гильдии (учитывая нити)
    if str(room).startswith('g:'):
        try:
            parts = room.split(':')
            if len(parts) >= 4 and parts[0] == 'g' and parts[2] == 'c':
                gid = parts[1]
                cid = parts[3]
                ch = guilds.get(gid, {}).get('channels', {}).get(cid)
                if ch is None:
                    emit('permission_error', {'reason': 'channel_not_found'})
                    return
                is_owner = guilds[gid]['owner'] == username
                if ch.get('read_only') and not is_owner:
                    emit('permission_error', {'reason': 'read_only'})
                    return
        except Exception:
            pass
    
    # Создание сообщения (для всех типов комнат: DM, каналы, нити)
    message_id = str(uuid.uuid4())
    message_data = {
        'id': message_id,
        'username': username,
        'message': message,
        'timestamp': datetime.now().isoformat(),
        'room': room,
        'reactions': {},
        'pinned': False
    }
    if 'file' in data:
        f = data['file']
        message_data['file'] = {
            'name': f.get('name'),
            'url': f.get('url'),
            'type': f.get('type'),
            'size': f.get('size')
        }
    
    if room not in messages:
        messages[room] = []
    messages[room].append(message_data)
    
    # Сохраняем сообщение в базе данных
    try:
        from messages import create_message, create_dm_message, create_dm_channel, get_dm_channel_by_users
        if room.startswith('dm:'):
            # Для DM создаем или находим DM канал и сохраняем сообщение
            parts = room.split(':')
            if len(parts) >= 3:
                user1, user2 = parts[1], parts[2]
                dm_channel_id, dm_channel = create_dm_channel(user1, user2)
                if dm_channel_id:
                    create_dm_message(dm_channel_id, username, message, data.get('file'))
        elif room.startswith('g:'):
            # Для каналов гильдии сохраняем в БД
            parts = room.split(':')
            if len(parts) >= 4:
                channel_id = parts[3]
                create_message(channel_id, username, message, data.get('file'))
    except Exception as e:
        print(f"Ошибка сохранения сообщения в БД: {e}")
    
    emit('new_message', message_data, room=room)
    
    # Инвалидируем кэш сообщений канала
    if str(room).startswith('g:'):
        try:
            guild_id, channel_id = room.split(':')[1], room.split(':')[3]
            invalidate_channel_cache(channel_id)
        except:
            pass


@socketio.on('get_messages')
def handle_get_messages(data):
    room = data['room']
    username = session.get('username')
    
    # Загружаем сообщения из памяти
    memory_messages = messages.get(room, [])
    
    # Загружаем сообщения из базы данных
    if room.startswith('g:'):
        try:
            from messages import get_messages
            parts = room.split(':')
            if len(parts) >= 4:
                channel_id = parts[3]
                db_messages = get_messages(channel_id, limit=50)
                # Конвертируем сообщения из БД в формат для фронтенда
                db_formatted = []
                for msg in db_messages:
                    db_formatted.append({
                        'id': str(msg.id),
                        'username': msg.user.username,
                        'message': msg.content,
                        'timestamp': msg.timestamp.isoformat(),
                        'room': room,
                        'reactions': {},
                        'pinned': msg.pinned
                    })
                # Объединяем сообщения из БД и памяти, убираем дубликаты
                all_messages = db_formatted + memory_messages
                # Убираем дубликаты по ID
                seen_ids = set()
                unique_messages = []
                for msg in all_messages:
                    if msg['id'] not in seen_ids:
                        seen_ids.add(msg['id'])
                        unique_messages.append(msg)
                emit('messages_history', unique_messages)
                return
        except Exception as e:
            print(f"Ошибка загрузки сообщений из БД: {e}")
    elif room.startswith('dm:'):
        try:
            from messages import get_dm_messages, get_dm_channel_by_users
            parts = room.split(':')
            if len(parts) >= 3:
                user1, user2 = parts[1], parts[2]
                dm_channel = get_dm_channel_by_users(user1, user2)
                if dm_channel:
                    db_messages = get_dm_messages(dm_channel.id, limit=50)
                    # Конвертируем сообщения из БД в формат для фронтенда
                    db_formatted = []
                    for msg in db_messages:
                        db_formatted.append({
                            'id': str(msg.id),
                            'username': msg.user.username,
                            'message': msg.content,
                            'timestamp': msg.timestamp.isoformat(),
                            'room': room,
                            'reactions': {},
                            'pinned': msg.pinned
                        })
                    # Объединяем сообщения из БД и памяти, убираем дубликаты
                    all_messages = db_formatted + memory_messages
                    # Убираем дубликаты по ID
                    seen_ids = set()
                    unique_messages = []
                    for msg in all_messages:
                        if msg['id'] not in seen_ids:
                            seen_ids.add(msg['id'])
                            unique_messages.append(msg)
                    emit('messages_history', unique_messages)
                    return
        except Exception as e:
            print(f"Ошибка загрузки DM сообщений из БД: {e}")
    
    print(f"[DEBUG] get_messages: user={username} room={room} messages_count={len(memory_messages)}")
    if room in messages:
        emit('messages_history', messages[room])

# Pin/unpin with simple permissions: owner can pin in guild channels; in DMs любой участник
@socketio.on('pin_message')
@rate_limited_socketio('pin_message', max_per_min=10)
def handle_pin_message(data):
    room = data['room']
    message_id = data['message_id']
    username = session.get('username')
    if not username or room not in messages:
        return
    allowed = False
    if str(room).startswith('g:'):
        try:
            parts = room.split(':')
            gid = parts[1]
            if guilds.get(gid, {}).get('owner') == username:
                allowed = True
        except Exception:
            allowed = False
    else:
        # DM/legacy — разрешаем
        allowed = True
    if not allowed:
        emit('permission_error', {'reason': 'pin_forbidden'})
        return
    for m in messages[room]:
        if m['id'] == message_id:
            m['pinned'] = True
            save_data()
            emit('message_pinned', {'room': room, 'message_id': message_id, 'pinned': True}, room=room)
            break


@socketio.on('unpin_message')
@rate_limited_socketio('unpin_message', max_per_min=10)
def handle_unpin_message(data):
    room = data['room']
    message_id = data['message_id']
    username = session.get('username')
    if not username or room not in messages:
        return
    allowed = False
    if str(room).startswith('g:'):
        try:
            parts = room.split(':')
            gid = parts[1]
            if guilds.get(gid, {}).get('owner') == username:
                allowed = True
        except Exception:
            allowed = False
    else:
        allowed = True
    if not allowed:
        emit('permission_error', {'reason': 'pin_forbidden'})
        return
    for m in messages[room]:
        if m['id'] == message_id:
            m['pinned'] = False
            save_data()
            emit('message_pinned', {'room': room, 'message_id': message_id, 'pinned': False}, room=room)
            break


@socketio.on('typing_start')
def handle_typing_start(data):
    room = data['room']
    username = session.get('username')
    if username:
        emit('user_typing', {'username': username, 'typing': True}, room=room, include_self=False)


@socketio.on('typing_stop')
def handle_typing_stop(data):
    room = data['room']
    username = session.get('username')
    if username:
        emit('user_typing', {'username': username, 'typing': False}, room=room, include_self=False)


@socketio.on('edit_message')
@rate_limited_socketio('edit_message', max_per_min=15)
def handle_edit_message(data):
    room = data['room']
    message_id = data['message_id']
    new_content = data['new_content']
    username = session.get('username')
    
    if username and room in messages:
        for message in messages[room]:
            if message['id'] == message_id and message['username'] == username:
                message['message'] = new_content
                message['edited'] = True
                message['edited_at'] = datetime.now().isoformat()
                emit('message_edited', {'message_id': message_id, 'new_content': new_content, 'edited_at': message['edited_at']}, room=room)
                break


@socketio.on('delete_message')
@rate_limited_socketio('delete_message', max_per_min=15)
def handle_delete_message(data):
    room = data['room']
    message_id = data['message_id']
    username = session.get('username')
    
    if username and room in messages:
        for i, message in enumerate(messages[room]):
            if message['id'] == message_id and message['username'] == username:
                del messages[room][i]
                emit('message_deleted', {'message_id': message_id}, room=room)
                break


@socketio.on('add_reaction')
def handle_add_reaction(data):
    room = data['room']
    message_id = data['message_id']
    emoji = data['emoji']
    username = session.get('username')
    if not username or room not in messages:
        return
    for message in messages[room]:
        if message['id'] == message_id:
            if 'reactions' not in message:
                message['reactions'] = {}
            users_set = set(message['reactions'].get(emoji, []))
            users_set.add(username)
            message['reactions'][emoji] = list(users_set)
            emit('reaction_updated', {'message_id': message_id, 'reactions': message['reactions']}, room=room)
            break


@socketio.on('remove_reaction')
def handle_remove_reaction(data):
    room = data['room']
    message_id = data['message_id']
    emoji = data['emoji']
    username = session.get('username')
    if not username or room not in messages:
        return
    for message in messages[room]:
        if message['id'] == message_id and 'reactions' in message and emoji in message['reactions']:
            users_list = list(message['reactions'][emoji])
            if username in users_list:
                users_list.remove(username)
            if users_list:
                message['reactions'][emoji] = users_list
            else:
                del message['reactions'][emoji]
            emit('reaction_updated', {'message_id': message_id, 'reactions': message['reactions']}, room=room)
            break


@app.route('/api/guilds/<gid>/channels/<cid>/threads')
def api_list_threads(gid, cid):
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    if gid not in guilds or cid not in guilds[gid]['channels']:
        return jsonify({'error': 'Не найдено'}), 404
    me = session['username']
    members = member_of_guild.get(gid) or set()
    if me != guilds[gid]['owner'] and me not in members:
        return jsonify({'error': 'Нет доступа'}), 403
    key = (gid, cid)
    channel_threads = threads_index.get(key, {})
    result = [{ 'id': t['id'], 'title': t['title'], 'creator': t['creator'], 'created_at': t['created_at'], 'parent_message_id': t.get('parent_message_id') } for t in channel_threads.values()]
    return jsonify(result)


# --- Уведомление о создании нити ---
@socketio.on('create_thread')
@rate_limited_socketio('create_thread', max_per_min=5)
def handle_create_thread(data):
    username = session.get('username')
    if not username:
        return
    gid = data.get('guild_id')
    cid = data.get('channel_id')
    title = (data.get('title') or '').strip() or 'New thread'
    parent_message_id = data.get('parent_message_id')
    if gid not in guilds or cid not in guilds[gid]['channels']:
        return
    members = member_of_guild.get(gid) or set()
    if username != guilds[gid]['owner'] and username not in members:
        return
    thread_id = str(uuid.uuid4())
    key = (gid, cid)
    if key not in threads_index:
        threads_index[key] = {}
    threads_index[key][thread_id] = {
        'id': thread_id,
        'title': title,
        'creator': username,
        'created_at': datetime.now().isoformat(),
        'parent_message_id': parent_message_id
    }
    room = f'g:{gid}:c:{cid}'
    if parent_message_id and room in messages:
        for m in messages[room]:
            if m['id'] == parent_message_id:
                m['thread_id'] = thread_id
                break
    thread_room = f'{room}:t:{thread_id}'
    if thread_room not in messages:
        messages[thread_room] = []
    save_data()
    emit('thread_created', {'guild_id': gid, 'channel_id': cid, 'thread': threads_index[key][thread_id]})
    # --- уведомление ---
    socketio.emit('notification', {'message': f'Создана новая нить: {title}'})


@app.route('/api/account/delete', methods=['POST'])
def delete_account():
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    data = request.get_json(force=True)
    password = data.get('password')
    username = session['username']
    user = users.get(username)
    if not user or not password or not check_password_hash(user['password'], password):
        return jsonify({'error': 'Неверный пароль'}), 403

    # 1) Удалить/анонимизировать данные сообщений
    try:
        for room_key, msgs in messages.items():
            for m in msgs:
                if m.get('username') == username:
                    m['username'] = 'deleted_user'
    except Exception:
        pass

    # 2) Друзья/заявки
    if username in friendships:
        for friend in list(friendships[username]):
            friendships[friend].discard(username)
        friendships.pop(username, None)
    friend_requests_in.pop(username, None)
    if username in friend_requests_out:
        # убрать из входящих у других
        for to_user in list(friend_requests_out[username]):
            if to_user in friend_requests_in:
                friend_requests_in[to_user].discard(username)
        friend_requests_out.pop(username, None)

    # 3) Членство в гильдиях
    for gid, members in list(member_of_guild.items()):
        if username in members:
            members.discard(username)
            member_of_guild[gid] = members

    # 4) Удалить гильдии, которыми владел пользователь
    def _purge_guild(gid):
        # удалить комнаты сообщений этой гильдии (каналы и нити)
        prefix = f'g:{gid}:'
        for room_key in list(messages.keys()):
            if str(room_key).startswith(prefix):
                messages.pop(room_key, None)
        # удалить нити индекса
        for key in list(threads_index.keys()):
            g, c = key
            if g == gid:
                threads_index.pop(key, None)
        # удалить инвайты на гильдию
        for code, igid in list(invites.items()):
            if igid == gid:
                invites.pop(code, None)
        # удалить членство
        member_of_guild.pop(gid, None)
        # удалить саму гильдию
        guilds.pop(gid, None)

    for gid, g in list(guilds.items()):
        if g.get('owner') == username:
            _purge_guild(gid)

    # 5) Удалить пользователя
    users.pop(username, None)

    save_data()

    # 6) Завершить сессию
    session.clear()

    return jsonify({'success': True})


@app.route('/api/admin/export')
def admin_export():
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    if session['username'] not in admins:
        return jsonify({'error': 'Недостаточно прав'}), 403
    data = serialize_data()
    data['admins'] = list(admins)
    return Response(json.dumps(data, ensure_ascii=False), mimetype='application/json')

@app.route('/api/admin/import', methods=['POST'])
@rate_limited('admin')
@require_csrf
def admin_import():
    global users, rooms, messages, friendships, friend_requests_in, friend_requests_out, guilds, member_of_guild, invites, threads_index, admins
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    # guard: ensure admins initialized
    if session['username'] not in admins:
        return jsonify({'error': 'Недостаточно прав'}), 403
    try:
        payload = request.get_json(force=True)
        if not isinstance(payload, dict):
            return jsonify({'error': 'Неверный формат'}), 400
        users = payload.get('users', {})
        rooms = payload.get('rooms', {})
        messages = payload.get('messages', {})
        friendships = {k: set(v) for k, v in (payload.get('friendships', {}) or {}).items()}
        friend_requests_in = {k: set(v) for k, v in (payload.get('friend_requests_in', {}) or {}).items()}
        friend_requests_out = {k: set(v) for k, v in (payload.get('friend_requests_out', {}) or {}).items()}
        guilds = payload.get('guilds', {})
        member_of_guild = {gid: set(v) for gid, v in (payload.get('member_of_guild', {}) or {}).items()}
        invites = payload.get('invites', {})
        threads_index = {}
        for key, val in (payload.get('threads_index', {}) or {}).items():
            try:
                gid, cid = key.split(':', 1)
                threads_index[(gid, cid)] = val
            except Exception:
                continue
        incoming_admins = payload.get('admins')
        if isinstance(incoming_admins, list):
            admins = set(incoming_admins)
        save_data()
        socketio.emit('guilds_updated', {'import': True})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Поиск

@app.route('/api/search/messages', methods=['GET'])
@rate_limited('search')
def api_search_messages():
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'error': 'Запрос должен содержать минимум 2 символа'}), 400
    
    results = []
    query_lower = query.lower()
    
    # Поиск по сообщениям в доступных комнатах
    for room, msgs in messages.items():
        for msg in msgs:
            if query_lower in msg.get('message', '').lower():
                results.append({
                    'id': msg['id'],
                    'username': msg['username'],
                    'message': msg['message'],
                    'timestamp': msg['timestamp'],
                    'room': room
                })
    
    # Ограничиваем количество результатов
    results = results[:50]
    return jsonify({'results': results, 'count': len(results)})

@app.route('/api/search/users', methods=['GET'])
@rate_limited('search')
def api_search_users():
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'error': 'Запрос должен содержать минимум 2 символа'}), 400
    
    from users import search_users
    usernames = search_users(query)
    results = [{'username': u} for u in usernames[:20]]  # Ограничиваем 20 результатами
    return jsonify({'results': results, 'count': len(results)})

# Эмодзи API
@app.route('/api/guilds/<int:guild_id>/emojis', methods=['GET'])
def api_get_guild_emojis(guild_id):
    try:
        emojis = get_guild_emojis(guild_id)
        return jsonify([{
            'id': emoji.id,
            'name': emoji.name,
            'file_path': emoji.file_path,
            'animated': emoji.animated,
            'created_at': emoji.created_at.isoformat()
        } for emoji in emojis])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/guilds/<int:guild_id>/emojis', methods=['POST'])
def api_create_emoji(guild_id):
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не найден'}), 400
    
    file = request.files['file']
    name = request.form.get('name', '').strip()
    
    if not name:
        return jsonify({'error': 'Имя эмодзи обязательно'}), 400
    
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Не авторизован'}), 401
        
        emoji, error = create_custom_emoji(guild_id, name, file, user_id)
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'id': emoji.id,
            'name': emoji.name,
            'file_path': emoji.file_path,
            'animated': emoji.animated
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/emojis/<emoji_id>', methods=['DELETE'])
def api_delete_emoji(emoji_id):
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Не авторизован'}), 401
        
        success, error = delete_custom_emoji(emoji_id, user_id)
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Стикеры API
@app.route('/api/guilds/<int:guild_id>/stickers', methods=['GET'])
def api_get_guild_stickers(guild_id):
    try:
        stickers = get_guild_stickers(guild_id)
        return jsonify([{
            'id': sticker.id,
            'name': sticker.name,
            'file_path': sticker.file_path,
            'description': sticker.description,
            'created_at': sticker.created_at.isoformat()
        } for sticker in stickers])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/guilds/<int:guild_id>/stickers', methods=['POST'])
def api_create_sticker(guild_id):
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не найден'}), 400
    
    file = request.files['file']
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name:
        return jsonify({'error': 'Имя стикера обязательно'}), 400
    
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400
    
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Не авторизован'}), 401
        
        sticker, error = create_sticker(guild_id, name, file, user_id, description)
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'id': sticker.id,
            'name': sticker.name,
            'file_path': sticker.file_path,
            'description': sticker.description
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stickers/<sticker_id>', methods=['DELETE'])
def api_delete_sticker(sticker_id):
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Не авторизован'}), 401
        
        success, error = delete_sticker(sticker_id, user_id)
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Опросы API
@app.route('/api/messages/<int:message_id>/poll', methods=['POST'])
def api_create_poll(message_id):
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        options = data.get('options', [])
        expires_hours = data.get('expires_hours')
        allow_multiple = data.get('allow_multiple', False)
        
        if not question:
            return jsonify({'error': 'Вопрос обязателен'}), 400
        
        if not options or len(options) < 2:
            return jsonify({'error': 'Минимум 2 варианта ответа'}), 400
        
        from models import SessionLocal
        db = SessionLocal()
        try:
            poll, error = create_poll(db, message_id, question, options, expires_hours, allow_multiple)
        finally:
            db.close()
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'id': poll.id,
            'question': poll.question,
            'options': poll.options,
            'expires_at': poll.expires_at.isoformat() if poll.expires_at else None,
            'allow_multiple': poll.allow_multiple
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/polls/<poll_id>/vote', methods=['POST'])
def api_vote_poll(poll_id):
    try:
        data = request.get_json()
        option_id = data.get('option_id', '').strip()
        
        if not option_id:
            return jsonify({'error': 'Вариант ответа обязателен'}), 400
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Не авторизован'}), 401
        
        from models import SessionLocal
        db = SessionLocal()
        try:
            poll, error = vote_poll(db, poll_id, user_id, option_id)
        finally:
            db.close()
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify({
            'id': poll.id,
            'question': poll.question,
            'options': poll.options,
            'expires_at': poll.expires_at.isoformat() if poll.expires_at else None,
            'allow_multiple': poll.allow_multiple
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/messages/<int:message_id>/poll', methods=['GET'])
def api_get_poll(message_id):
    try:
        from models import SessionLocal
        db = SessionLocal()
        try:
            poll = get_poll_by_message(db, message_id)
            if not poll:
                return jsonify({'error': 'Опрос не найден'}), 404
            
            user_id = session.get('user_id')
            user_votes = []
            if user_id:
                user_votes = get_user_poll_votes(db, poll.id, user_id)
        finally:
            db.close()
        
        return jsonify({
            'id': poll.id,
            'question': poll.question,
            'options': poll.options,
            'expires_at': poll.expires_at.isoformat() if poll.expires_at else None,
            'allow_multiple': poll.allow_multiple,
            'user_votes': [vote.option_id for vote in user_votes]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API для сообщений с пагинацией и кэшированием
@app.route('/api/channels/<int:channel_id>/messages')
def api_get_messages(channel_id):
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        
        # Проверяем кэш
        cached_data = get_cached_channel_messages(channel_id, page)
        if cached_data:
            return jsonify(cached_data)
        
        offset = (page - 1) * limit
        
        from messages import get_messages, get_messages_count
        
        messages = get_messages(channel_id, limit, offset)
        total_count = get_messages_count(channel_id)
        
        result = {
            'messages': [{
                'id': msg.id,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat(),
                'username': msg.user.username,
                'pinned': msg.pinned,
                'files': [{'filename': f.filename, 'path': f.path} for f in msg.files]
            } for msg in messages],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        }
        
        # Кэшируем результат
        cache_channel_messages(channel_id, page, result)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Restore /api/users endpoint
@app.route('/api/users')
@rate_limited('users')
def get_users_api():
    return jsonify([{
        'username': username,
        'online': user_data.get('online', False),
        'joined_at': user_data.get('joined_at'),
        'avatar_url': user_data.get('avatar_url') or None,
        'bio': user_data.get('bio', ''),
        'status_text': user_data.get('status_text', '')
    } for username, user_data in users.items()])

# Restore /api/friends/status endpoint
@app.route('/api/friends/status')
@rate_limited('friends')
def friends_status():
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    me = session['username']
    _ensure_user_sets(me)
    return jsonify({
        'friends': sorted(list(friendships.get(me, set()))),
        'incoming': sorted(list(friend_requests_in.get(me, set()))),
        'outgoing': sorted(list(friend_requests_out.get(me, set())))
    })


# User search endpoint by partial nickname
@app.route('/api/user_search')
@rate_limited('users')
def api_user_search():
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401
    q = (request.args.get('q') or '').strip().lower()
    if not q:
        return jsonify([])
    results = []
    for username, u in users.items():
        if q in username.lower():
            results.append({
                'username': username,
                'avatar_url': u.get('avatar_url') or None
            })
            if len(results) >= 20:
                break
    return jsonify(results)


# Пример: отправка уведомления всем клиентам
@app.route('/send_notification')
def send_notification():
    socketio.emit('notification', {'message': 'Новое сообщение!'})
    return 'Уведомление отправлено!'


if __name__ == '__main__':
    import eventlet
    import eventlet.wsgi
    start_cache_cleanup()  # Запускаем очистку кэша
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)

