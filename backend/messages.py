import uuid
from datetime import datetime
from models import Message, Channel, User, DMChannel, SessionLocal
from sqlalchemy.orm import joinedload

messages = {}
threads_index = {}

# Сообщения

MAX_MESSAGES_PER_CHANNEL = 10000

def create_message(channel_id, username, text, file=None):
    db = SessionLocal()
    user = db.query(User).filter_by(username=username).first()
    channel = db.query(Channel).filter_by(id=channel_id).first()
    if not user or not channel:
        db.close()
        return None
    msg_count = db.query(Message).filter_by(channel_id=channel_id).count()
    if msg_count >= MAX_MESSAGES_PER_CHANNEL:
        db.close()
        return None  # Можно вернуть ошибку "Лимит сообщений в канале"
    message = Message(channel=channel, user=user, content=text, timestamp=datetime.now(), pinned=False)
    db.add(message)
    db.commit()
    db.refresh(message)
    db.close()
    return message

def get_messages(channel_id, limit=50, offset=0):
    db = SessionLocal()
    msgs = db.query(Message).options(joinedload(Message.user)).filter_by(channel_id=channel_id).order_by(Message.timestamp.desc()).offset(offset).limit(limit).all()
    db.close()
    return msgs

def get_messages_count(channel_id):
    db = SessionLocal()
    count = db.query(Message).filter_by(channel_id=channel_id).count()
    db.close()
    return count

def edit_message(channel_id, message_id, new_text):
    db = SessionLocal()
    msg = db.query(Message).filter_by(id=message_id, channel_id=channel_id).first()
    if not msg:
        db.close()
        return False
    msg.content = new_text
    db.commit()
    db.close()
    return True

def delete_message(channel_id, message_id):
    db = SessionLocal()
    msg = db.query(Message).filter_by(id=message_id, channel_id=channel_id).first()
    if not msg:
        db.close()
        return False
    db.delete(msg)
    db.commit()
    db.close()
    return True

# Реакции (заглушка: можно реализовать отдельной таблицей message_reactions)
def add_reaction(channel_id, message_id, emoji, username):
    return False

def remove_reaction(channel_id, message_id, emoji, username):
    return False

# Пины

def pin_message(channel_id, message_id):
    db = SessionLocal()
    msg = db.query(Message).filter_by(id=message_id, channel_id=channel_id).first()
    if not msg:
        db.close()
        return False
    msg.pinned = True
    db.commit()
    db.close()
    return True

def unpin_message(channel_id, message_id):
    db = SessionLocal()
    msg = db.query(Message).filter_by(id=message_id, channel_id=channel_id).first()
    if not msg:
        db.close()
        return False
    msg.pinned = False
    db.commit()
    db.close()
    return True

# Нити (threads) — заглушка
def create_thread(gid, cid, title, creator):
    return None, None

def get_threads(gid, cid):
    return []

# DM каналы
def create_dm_channel(user1_username, user2_username):
    """Создать или найти DM канал между двумя пользователями"""
    db = SessionLocal()
    try:
        user1 = db.query(User).filter_by(username=user1_username).first()
        user2 = db.query(User).filter_by(username=user2_username).first()
        
        if not user1 or not user2:
            return None, "Пользователь не найден"
        
        # Проверяем, существует ли уже DM канал
        existing_dm = db.query(DMChannel).filter(
            ((DMChannel.user1_id == user1.id) & (DMChannel.user2_id == user2.id)) |
            ((DMChannel.user1_id == user2.id) & (DMChannel.user2_id == user1.id))
        ).first()
        
        if existing_dm:
            return existing_dm.id, existing_dm
        
        # Создаем новый DM канал
        dm_channel = DMChannel(user1_id=user1.id, user2_id=user2.id)
        db.add(dm_channel)
        db.commit()
        db.refresh(dm_channel)
        
        return dm_channel.id, dm_channel
    except Exception as e:
        db.rollback()
        return None, str(e)
    finally:
        db.close()

def create_dm_message(dm_channel_id, username, text, file=None):
    """Создать сообщение в DM канале"""
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=username).first()
        dm_channel = db.query(DMChannel).filter_by(id=dm_channel_id).first()
        
        if not user or not dm_channel:
            return None
        
        message = Message(
            dm_channel=dm_channel,
            user=user,
            content=text,
            timestamp=datetime.now(),
            pinned=False
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        
        return message
    except Exception as e:
        db.rollback()
        return None
    finally:
        db.close()

def get_dm_messages(dm_channel_id, limit=50, offset=0):
    """Получить сообщения из DM канала"""
    db = SessionLocal()
    try:
        messages = db.query(Message).options(
            joinedload(Message.user)
        ).filter_by(dm_channel_id=dm_channel_id).order_by(
            Message.timestamp.desc()
        ).offset(offset).limit(limit).all()
        
        return messages
    except Exception as e:
        return []
    finally:
        db.close()

def get_dm_channel_by_users(user1_username, user2_username):
    """Найти DM канал между двумя пользователями"""
    db = SessionLocal()
    try:
        user1 = db.query(User).filter_by(username=user1_username).first()
        user2 = db.query(User).filter_by(username=user2_username).first()
        
        if not user1 or not user2:
            return None
        
        dm_channel = db.query(DMChannel).filter(
            ((DMChannel.user1_id == user1.id) & (DMChannel.user2_id == user2.id)) |
            ((DMChannel.user1_id == user2.id) & (DMChannel.user2_id == user1.id))
        ).first()
        
        return dm_channel
    except Exception as e:
        return None
    finally:
        db.close()
