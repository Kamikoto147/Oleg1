#!/usr/bin/env python3
"""
Скрипт для инициализации базовых прав (permissions) в базе данных.
Запускать один раз после создания таблиц.
"""

from models import Permission, SessionLocal

# Базовые права Discord-подобного мессенджера
BASIC_PERMISSIONS = [
    ('send_messages', 'Отправка сообщений'),
    ('read_messages', 'Чтение сообщений'),
    ('manage_messages', 'Управление сообщениями'),
    ('manage_channels', 'Управление каналами'),
    ('manage_roles', 'Управление ролями'),
    ('manage_guild', 'Управление сервером'),
    ('kick_members', 'Исключение участников'),
    ('ban_members', 'Блокировка участников'),
    ('administrator', 'Администратор (все права)'),
    ('view_audit_log', 'Просмотр журнала аудита'),
    ('manage_webhooks', 'Управление веб-хуками'),
    ('manage_emojis', 'Управление эмодзи'),
    ('change_nickname', 'Изменение никнейма'),
    ('manage_nicknames', 'Управление никнеймами'),
    ('create_instant_invite', 'Создание приглашений'),
    ('manage_invites', 'Управление приглашениями'),
    ('add_reactions', 'Добавление реакций'),
    ('use_external_emojis', 'Использование внешних эмодзи'),
    ('mention_everyone', 'Упоминание @everyone'),
    ('connect', 'Подключение к голосовым каналам'),
    ('speak', 'Говорение в голосовых каналах'),
    ('mute_members', 'Отключение микрофона участников'),
    ('deafen_members', 'Отключение звука участников'),
    ('move_members', 'Перемещение участников'),
    ('use_voice_activation', 'Использование активации по голосу'),
    ('priority_speaker', 'Приоритетный режим'),
    ('stream', 'Стриминг'),
    ('read_message_history', 'Чтение истории сообщений'),
    ('send_tts_messages', 'Отправка TTS сообщений'),
    ('embed_links', 'Встраивание ссылок'),
    ('attach_files', 'Прикрепление файлов'),
    ('use_slash_commands', 'Использование слеш-команд'),
    ('manage_threads', 'Управление ветками'),
    ('create_public_threads', 'Создание публичных веток'),
    ('create_private_threads', 'Создание приватных веток'),
    ('send_messages_in_threads', 'Отправка сообщений в ветках'),
    ('use_external_stickers', 'Использование внешних стикеров'),
    ('send_voice_messages', 'Отправка голосовых сообщений'),
]

def init_permissions():
    """Инициализирует базовые права в базе данных."""
    db = SessionLocal()
    
    try:
        # Проверяем, есть ли уже права
        existing_count = db.query(Permission).count()
        if existing_count > 0:
            print(f"Права уже инициализированы ({existing_count} записей)")
            return
        
        # Создаем права
        for perm_name, perm_desc in BASIC_PERMISSIONS:
            permission = Permission(name=perm_name, description=perm_desc)
            db.add(permission)
        
        db.commit()
        print(f"Успешно создано {len(BASIC_PERMISSIONS)} базовых прав")
        
    except Exception as e:
        print(f"Ошибка при инициализации прав: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    init_permissions()


