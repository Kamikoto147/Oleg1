import os
from werkzeug.utils import secure_filename
from flask import send_from_directory
from models import File, User, Message, SessionLocal
from datetime import datetime

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}

# Проверка расширения

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Загрузка файла

def save_file(file_storage, upload_folder, username, message_id=None):
    if not allowed_file(file_storage.filename):
        return None, 'Недопустимый тип файла'
    if file_storage.content_length and file_storage.content_length > 10 * 1024 * 1024:
        return None, 'Файл слишком большой (макс 10MB)'
    filename = secure_filename(file_storage.filename)
    path = os.path.join(upload_folder, filename)
    file_storage.save(path)
    db = SessionLocal()
    user = db.query(User).filter_by(username=username).first()
    file_obj = File(
        filename=filename,
        path=path,
        mimetype=file_storage.mimetype,
        size=os.path.getsize(path),
        user=user,
        message_id=message_id,
        uploaded_at=datetime.now()
    )
    db.add(file_obj)
    db.commit()
    db.refresh(file_obj)
    db.close()
    return file_obj, None

# Получение файла

def serve_file(filename, upload_folder):
    return send_from_directory(upload_folder, filename)
