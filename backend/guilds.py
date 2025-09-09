import uuid
from models import Guild, Channel, User, Role, Permission, Category, SessionLocal
from sqlalchemy.orm import joinedload

guilds = {}
member_of_guild = {}
invites = {}

# Гильдии

MAX_GUILDS = 100
MAX_CHANNELS = 100

def create_guild(owner_username, name):
    db = SessionLocal()
    owner = db.query(User).filter_by(username=owner_username).first()
    user_guilds = db.query(Guild).filter_by(owner_id=owner.id).count()
    if user_guilds >= MAX_GUILDS:
        db.close()
        return None, f'Лимит гильдий: {MAX_GUILDS}'
    if not owner:
        db.close()
        return None, 'Владелец не найден'
    guild = Guild(name=name, owner=owner)
    db.add(guild)
    db.commit()
    db.refresh(guild)
    db.close()
    return guild.id, guild

def get_guild(gid):
    db = SessionLocal()
    guild = db.query(Guild).options(joinedload(Guild.channels)).filter_by(id=gid).first()
    db.close()
    return guild

def delete_guild(gid):
    db = SessionLocal()
    guild = db.query(Guild).filter_by(id=gid).first()
    if not guild:
        db.close()
        return False
    db.delete(guild)
    db.commit()
    db.close()
    return True

def list_guilds():
    db = SessionLocal()
    guilds = db.query(Guild).all()
    db.close()
    return guilds

# Каналы

def create_channel(gid, name, read_only=False):
    db = SessionLocal()
    guild = db.query(Guild).filter_by(id=gid).first()
    if not guild:
        db.close()
        return None, 'Гильдия не найдена'
    if len(guild.channels) >= MAX_CHANNELS:
        db.close()
        return None, f'Лимит каналов в гильдии: {MAX_CHANNELS}'
    channel = Channel(name=name, guild=guild, read_only=read_only)
    db.add(channel)
    db.commit()
    db.refresh(channel)
    db.close()
    return channel.id, channel

def get_channel(gid, cid):
    db = SessionLocal()
    channel = db.query(Channel).filter_by(id=cid, guild_id=gid).first()
    db.close()
    return channel

def list_channels(gid):
    db = SessionLocal()
    channels = db.query(Channel).filter_by(guild_id=gid).all()
    db.close()
    return channels

# Членство (упрощённо: просто список пользователей-гильдий)
def add_member(gid, username):
    db = SessionLocal()
    guild = db.query(Guild).filter_by(id=gid).first()
    user = db.query(User).filter_by(username=username).first()
    if not guild or not user:
        db.close()
        return False
    # В реальной Discord — отдельная таблица membership, здесь можно реализовать позже
    db.close()
    return True

def remove_member(gid, username):
    # Аналогично add_member — реализовать через отдельную таблицу membership
    return True

def get_members(gid):
    # Аналогично — реализовать через отдельную таблицу membership
    return []

# Роли и права

def create_role(gid, name, color='#99aab5'):
    db = SessionLocal()
    guild = db.query(Guild).filter_by(id=gid).first()
    if not guild:
        db.close()
        return None, 'Гильдия не найдена'
    role = Role(name=name, guild=guild, color=color)
    db.add(role)
    db.commit()
    db.refresh(role)
    db.close()
    return role.id, role

def get_roles(gid):
    db = SessionLocal()
    roles = db.query(Role).filter_by(guild_id=gid).order_by(Role.position).all()
    db.close()
    return roles

def assign_permission_to_role(role_id, permission_name):
    db = SessionLocal()
    role = db.query(Role).filter_by(id=role_id).first()
    permission = db.query(Permission).filter_by(name=permission_name).first()
    if not role or not permission:
        db.close()
        return False
    if permission not in role.permissions:
        role.permissions.append(permission)
        db.commit()
    db.close()
    return True

def check_user_permission(gid, username, permission_name):
    db = SessionLocal()
    user = db.query(User).filter_by(username=username).first()
    guild = db.query(Guild).filter_by(id=gid).first()
    if not user or not guild:
        db.close()
        return False
    # Владелец гильдии имеет все права
    if guild.owner_id == user.id:
        db.close()
        return True
    # Проверяем права через роли пользователя
    # TODO: реализовать через user_role_table
    db.close()
    return False

# Категории

def create_category(gid, name):
    db = SessionLocal()
    guild = db.query(Guild).filter_by(id=gid).first()
    if not guild:
        db.close()
        return None, 'Гильдия не найдена'
    category = Category(name=name, guild=guild)
    db.add(category)
    db.commit()
    db.refresh(category)
    db.close()
    return category.id, category

def get_categories(gid):
    db = SessionLocal()
    categories = db.query(Category).filter_by(guild_id=gid).order_by(Category.position).all()
    db.close()
    return categories

# Инвайты

def create_invite(gid, creator):
    code = str(uuid.uuid4())[:8]
    invites.setdefault(gid, set()).add(code)
    return code

def use_invite(gid, code, username):
    if code in invites.get(gid, set()):
        add_member(gid, username)
        invites[gid].discard(code)
        return True
    return False
