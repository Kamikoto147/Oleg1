from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from models import CustomEmoji, Sticker, Poll, PollVote, Guild, User, Message
from files import allowed_file, save_file
import os
import uuid
from datetime import datetime, timedelta

def create_custom_emoji(db: Session, guild_id: int, name: str, file, created_by: int):
    """Создать кастомный эмодзи"""
    if not allowed_file(file.filename, ['png', 'jpg', 'jpeg', 'gif', 'webp']):
        return None, "Неподдерживаемый формат файла"
    
    # Проверяем права на создание эмодзи
    guild = db.query(Guild).filter(Guild.id == guild_id).first()
    if not guild:
        return None, "Гильдия не найдена"
    
    if guild.owner_id != created_by:
        return None, "Недостаточно прав"
    
    # Сохраняем файл
    file_path = save_file(file, 'emojis')
    if not file_path:
        return None, "Ошибка сохранения файла"
    
    # Определяем анимированный ли эмодзи
    animated = file.filename.lower().endswith('.gif')
    
    emoji = CustomEmoji(
        name=name,
        guild_id=guild_id,
        file_path=file_path,
        created_by=created_by,
        animated=animated
    )
    
    db.add(emoji)
    db.commit()
    db.refresh(emoji)
    
    return emoji, None

def get_guild_emojis(db: Session, guild_id: int):
    """Получить все эмодзи гильдии"""
    return db.query(CustomEmoji).filter(CustomEmoji.guild_id == guild_id).all()

def create_sticker(db: Session, guild_id: int, name: str, file, created_by: int, description: str = None):
    """Создать стикер"""
    if not allowed_file(file.filename, ['png', 'jpg', 'jpeg', 'webp']):
        return None, "Неподдерживаемый формат файла"
    
    # Проверяем права на создание стикера
    guild = db.query(Guild).filter(Guild.id == guild_id).first()
    if not guild:
        return None, "Гильдия не найдена"
    
    if guild.owner_id != created_by:
        return None, "Недостаточно прав"
    
    # Сохраняем файл
    file_path = save_file(file, 'stickers')
    if not file_path:
        return None, "Ошибка сохранения файла"
    
    sticker = Sticker(
        name=name,
        guild_id=guild_id,
        file_path=file_path,
        created_by=created_by,
        description=description
    )
    
    db.add(sticker)
    db.commit()
    db.refresh(sticker)
    
    return sticker, None

def get_guild_stickers(db: Session, guild_id: int):
    """Получить все стикеры гильдии"""
    return db.query(Sticker).filter(Sticker.guild_id == guild_id).all()

def create_poll(db: Session, message_id: int, question: str, options: list, expires_hours: int = None, allow_multiple: bool = False):
    """Создать опрос"""
    if len(options) < 2:
        return None, "Минимум 2 варианта ответа"
    
    if len(options) > 10:
        return None, "Максимум 10 вариантов ответа"
    
    # Форматируем опции
    formatted_options = []
    for i, option_text in enumerate(options):
        formatted_options.append({
            "id": str(i + 1),
            "text": option_text,
            "votes": 0
        })
    
    expires_at = None
    if expires_hours:
        expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
    
    poll = Poll(
        message_id=message_id,
        question=question,
        options=formatted_options,
        expires_at=expires_at,
        allow_multiple=allow_multiple
    )
    
    db.add(poll)
    db.commit()
    db.refresh(poll)
    
    return poll, None

def vote_poll(db: Session, poll_id: str, user_id: int, option_id: str):
    """Голосовать в опросе"""
    poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if not poll:
        return None, "Опрос не найден"
    
    # Проверяем, не истек ли опрос
    if poll.expires_at and poll.expires_at < datetime.utcnow():
        return None, "Опрос истек"
    
    # Проверяем, голосовал ли уже пользователь
    existing_vote = db.query(PollVote).filter(
        and_(PollVote.poll_id == poll_id, PollVote.user_id == user_id)
    ).first()
    
    if existing_vote and not poll.allow_multiple:
        return None, "Вы уже голосовали в этом опросе"
    
    # Проверяем, существует ли вариант ответа
    option_exists = any(opt["id"] == option_id for opt in poll.options)
    if not option_exists:
        return None, "Неверный вариант ответа"
    
    # Если не разрешено множественное голосование, удаляем предыдущие голоса
    if existing_vote and not poll.allow_multiple:
        db.delete(existing_vote)
        # Уменьшаем счетчик голосов для предыдущего варианта
        for opt in poll.options:
            if opt["id"] == existing_vote.option_id:
                opt["votes"] -= 1
                break
    
    # Создаем новый голос
    vote = PollVote(
        poll_id=poll_id,
        user_id=user_id,
        option_id=option_id
    )
    
    db.add(vote)
    
    # Увеличиваем счетчик голосов
    for opt in poll.options:
        if opt["id"] == option_id:
            opt["votes"] += 1
            break
    
    db.commit()
    db.refresh(poll)
    
    return poll, None

def get_poll(db: Session, poll_id: str):
    """Получить опрос"""
    return db.query(Poll).filter(Poll.id == poll_id).first()

def get_poll_by_message(db: Session, message_id: int):
    """Получить опрос по сообщению"""
    return db.query(Poll).filter(Poll.message_id == message_id).first()

def get_user_poll_votes(db: Session, poll_id: str, user_id: int):
    """Получить голоса пользователя в опросе"""
    return db.query(PollVote).filter(
        and_(PollVote.poll_id == poll_id, PollVote.user_id == user_id)
    ).all()

def delete_custom_emoji(db: Session, emoji_id: str, user_id: int):
    """Удалить кастомный эмодзи"""
    emoji = db.query(CustomEmoji).filter(CustomEmoji.id == emoji_id).first()
    if not emoji:
        return False, "Эмодзи не найден"
    
    # Проверяем права
    guild = db.query(Guild).filter(Guild.id == emoji.guild_id).first()
    if not guild or (guild.owner_id != user_id and emoji.created_by != user_id):
        return False, "Недостаточно прав"
    
    # Удаляем файл
    try:
        if os.path.exists(emoji.file_path):
            os.remove(emoji.file_path)
    except:
        pass
    
    db.delete(emoji)
    db.commit()
    
    return True, None

def delete_sticker(db: Session, sticker_id: str, user_id: int):
    """Удалить стикер"""
    sticker = db.query(Sticker).filter(Sticker.id == sticker_id).first()
    if not sticker:
        return False, "Стикер не найден"
    
    # Проверяем права
    guild = db.query(Guild).filter(Guild.id == sticker.guild_id).first()
    if not guild or (guild.owner_id != user_id and sticker.created_by != user_id):
        return False, "Недостаточно прав"
    
    # Удаляем файл
    try:
        if os.path.exists(sticker.file_path):
            os.remove(sticker.file_path)
    except:
        pass
    
    db.delete(sticker)
    db.commit()
    
    return True, None


