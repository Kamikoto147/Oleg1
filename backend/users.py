import uuid
from werkzeug.security import generate_password_hash
from models import User, SessionLocal
from sqlalchemy.orm import joinedload

users = {}
friendships = {}
friend_requests_in = {}
friend_requests_out = {}

# CRUD пользователя

def create_user(username, password):
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

def get_user(username):
    db = SessionLocal()
    user = db.query(User).filter_by(username=username).first()
    db.close()
    return user

def update_profile(username, avatar=None, bio=None, status=None):
    db = SessionLocal()
    user = db.query(User).filter_by(username=username).first()
    if not user:
        db.close()
        return False
    if avatar is not None:
        user.avatar = avatar
    if bio is not None:
        user.bio = bio
    if status is not None:
        user.status = status
    db.commit()
    db.close()
    return True

def set_user_note(owner, target, note):
    user = users.get(owner)
    if not user:
        return False
    user['notes'][target] = note
    return True

def search_users(query):
    db = SessionLocal()
    users = db.query(User).filter(User.username.ilike(f'%{query}%')).all()
    db.close()
    return [u.username for u in users]

# Друзья

MAX_FRIENDS = 1000

def add_friend(sender, receiver):
    db = SessionLocal()
    sender_user = db.query(User).filter_by(username=sender).first()
    receiver_user = db.query(User).filter_by(username=receiver).first()
    if sender == receiver:
        db.close()
        return False, 'Нельзя добавить себя'
    if not receiver_user:
        db.close()
        return False, 'Пользователь не найден'
    if len(sender_user.friends) >= MAX_FRIENDS:
        db.close()
        return False, f'Лимит друзей: {MAX_FRIENDS}'
    if receiver_user in sender_user.friends:
        db.close()
        return False, 'Уже в друзьях'
    sender_user.friends.append(receiver_user)
    db.commit()
    db.close()
    return True, None

def accept_friend(receiver, sender):
    friendships.setdefault(sender, set())
    friendships.setdefault(receiver, set())
    if sender in friend_requests_in[receiver]:
        friendships[sender].add(receiver)
        friendships[receiver].add(sender)
        friend_requests_in[receiver].discard(sender)
        friend_requests_out[sender].discard(receiver)
        return True
    return False

def remove_friend(user1, user2):
    friendships.setdefault(user1, set())
    friendships.setdefault(user2, set())
    friendships[user1].discard(user2)
    friendships[user2].discard(user1)
    return True

def decline_friend(receiver, sender):
    if sender in friend_requests_in.get(receiver, set()):
        friend_requests_in[receiver].discard(sender)
        friend_requests_out[sender].discard(receiver)
        return True
    return False

def get_friends(username):
    db = SessionLocal()
    user = db.query(User).options(joinedload(User.friends)).filter_by(username=username).first()
    if not user:
        db.close()
        return []
    friends = [f.username for f in user.friends]
    db.close()
    return friends

def get_friend_requests(username):
    return list(friend_requests_in.get(username, set()))
