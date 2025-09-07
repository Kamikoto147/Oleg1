from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import uuid
from datetime import datetime
import os
from werkzeug.utils import secure_filename

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config['SECRET_KEY'] = 'oleg_messenger_secret_key_2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size
socketio = SocketIO(app, cors_allowed_origins="*")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}

# Хранилище данных (в реальном приложении используйте базу данных)
users = {}
rooms = {}
messages = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
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
        'password': password,  # В реальном приложении храните хеш!
        'online': True,
        'joined_at': datetime.now().isoformat()
    }
    
    session['username'] = username
    session['user_id'] = user_id
    
    return jsonify({
        'success': True,
        'user_id': user_id,
        'username': username
    })

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Имя пользователя и пароль обязательны'}), 400
    
    if username not in users:
        return jsonify({'error': 'Пользователь не найден'}), 404
    if users[username]['password'] != password:
        return jsonify({'error': 'Неверный пароль'}), 401
    
    users[username]['online'] = True
    session['username'] = username
    session['user_id'] = users[username]['id']
    
    return jsonify({
        'success': True,
        'user_id': users[username]['id'],
        'username': username
    })

@app.route('/api/users')
def get_users():
    return jsonify([{
        'username': username,
        'online': user_data['online'],
        'joined_at': user_data['joined_at']
    } for username, user_data in users.items()])

@app.route('/api/rooms')
def get_rooms():
    return jsonify(list(rooms.keys()))

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
        print(f"[UPLOAD] Сохраняю файл: {file.filename} -> {file_path}")
        file.save(file_path)
        print(f"[UPLOAD] Файл успешно сохранён: {file_path}")
        return jsonify({
            'success': True,
            'url': f'/uploads/{unique_filename}',
            'filename': filename
        })
    
    return jsonify({'error': 'Недопустимый тип файла'}), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # Абсолютный путь к папке uploads относительно корня проекта
    upload_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), 'uploads'))
    return send_from_directory(upload_folder, filename)

@socketio.on('connect')
def handle_connect():
    username = session.get('username')
    if username:
        users[username]['online'] = True
        emit('user_status', {'username': username, 'online': True}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    username = session.get('username')
    if username and username in users:
        users[username]['online'] = False
        emit('user_status', {'username': username, 'online': False}, broadcast=True)

@socketio.on('join_room')
def handle_join_room(data):
    room = data['room']
    username = session.get('username')
    
    if username:
        join_room(room)
        if room not in rooms:
            rooms[room] = {'users': [], 'created_at': datetime.now().isoformat()}
        if username not in rooms[room]['users']:
            rooms[room]['users'].append(username)
        
        emit('room_joined', {'room': room, 'username': username}, room=room)

@socketio.on('leave_room')
def handle_leave_room(data):
    room = data['room']
    username = session.get('username')
    
    if username and room in rooms:
        leave_room(room)
        if username in rooms[room]['users']:
            rooms[room]['users'].remove(username)
        
        emit('room_left', {'room': room, 'username': username}, room=room)

@socketio.on('send_message')
def handle_message(data):
    room = data['room']
    message = data['message']
    username = session.get('username')
    
    if username:
        message_id = str(uuid.uuid4())
        message_data = {
            'id': message_id,
            'username': username,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'room': room
        }
        # Если есть файл, добавляем его в сообщение
        if 'file' in data:
            file = data['file']
            message_data['file'] = {
                'name': file.get('name'),
                'url': file.get('url'),
                'type': file.get('type'),
                'size': file.get('size')
            }
        
        if room not in messages:
            messages[room] = []
        messages[room].append(message_data)
        
        emit('new_message', message_data, room=room)

@socketio.on('get_messages')
def handle_get_messages(data):
    room = data['room']
    if room in messages:
        emit('messages_history', messages[room])

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
                emit('message_edited', {
                    'message_id': message_id,
                    'new_content': new_content,
                    'edited_at': message['edited_at']
                }, room=room)
                break

@socketio.on('delete_message')
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

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)

