from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, create_engine, Table, JSON
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import uuid

Base = declarative_base()

# Таблица для друзей (many-to-many)
friendship_table = Table('friendship', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('friend_id', Integer, ForeignKey('users.id'))
)

# Таблица для связи ролей и прав (many-to-many)
role_permission_table = Table('role_permission', Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id')),
    Column('permission_id', Integer, ForeignKey('permissions.id'))
)

# Таблица для связи пользователей и ролей в гильдии (many-to-many)
user_role_table = Table('user_role', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('role_id', Integer, ForeignKey('roles.id')),
    Column('guild_id', Integer, ForeignKey('guilds.id'))
)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    avatar = Column(String)
    bio = Column(Text)
    status = Column(String)
    email = Column(String, unique=True)
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String)
    totp_secret = Column(String)  # Для 2FA (TOTP)
    created_at = Column(DateTime, default=datetime.utcnow)
    friends = relationship('User',
        secondary=friendship_table,
        primaryjoin=id==friendship_table.c.user_id,
        secondaryjoin=id==friendship_table.c.friend_id
    )

class Guild(Base):
    __tablename__ = 'guilds'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey('users.id'))
    owner = relationship('User')
    created_at = Column(DateTime, default=datetime.utcnow)
    channels = relationship('Channel', back_populates='guild')
    roles = relationship('Role', back_populates='guild')
    categories = relationship('Category', back_populates='guild')

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    guild_id = Column(Integer, ForeignKey('guilds.id'))
    guild = relationship('Guild', back_populates='categories')
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    channels = relationship('Channel', back_populates='category')

class Channel(Base):
    __tablename__ = 'channels'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    guild_id = Column(Integer, ForeignKey('guilds.id'))
    guild = relationship('Guild', back_populates='channels')
    category_id = Column(Integer, ForeignKey('categories.id'))
    category = relationship('Category', back_populates='channels')
    read_only = Column(Boolean, default=False)
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    messages = relationship('Message', back_populates='channel')

class DMChannel(Base):
    __tablename__ = 'dm_channels'
    id = Column(Integer, primary_key=True)
    user1_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user2_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    messages = relationship('Message', back_populates='dm_channel')
    
    # Relationships
    user1 = relationship('User', foreign_keys=[user1_id])
    user2 = relationship('User', foreign_keys=[user2_id])

class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    guild_id = Column(Integer, ForeignKey('guilds.id'))
    guild = relationship('Guild', back_populates='roles')
    color = Column(String, default='#99aab5')
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    permissions = relationship('Permission', secondary=role_permission_table, back_populates='roles')

class Permission(Base):
    __tablename__ = 'permissions'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    roles = relationship('Role', secondary=role_permission_table, back_populates='permissions')

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey('channels.id'))
    channel = relationship('Channel', back_populates='messages')
    dm_channel_id = Column(Integer, ForeignKey('dm_channels.id'))
    dm_channel = relationship('DMChannel', back_populates='messages')
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User')
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    pinned = Column(Boolean, default=False)
    files = relationship('File', back_populates='message')

class File(Base):
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    path = Column(String, nullable=False)
    mimetype = Column(String)
    size = Column(Integer)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship('User')
    message_id = Column(Integer, ForeignKey('messages.id'))
    message = relationship('Message', back_populates='files')
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class CustomEmoji(Base):
    __tablename__ = 'custom_emojis'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    guild_id = Column(Integer, ForeignKey('guilds.id'), nullable=False)
    file_path = Column(String, nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    animated = Column(Boolean, default=False)
    
    # Relationships
    guild = relationship("Guild")
    creator = relationship("User", foreign_keys=[created_by])

class Sticker(Base):
    __tablename__ = 'stickers'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    guild_id = Column(Integer, ForeignKey('guilds.id'), nullable=False)
    file_path = Column(String, nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(String)
    
    # Relationships
    guild = relationship("Guild")
    creator = relationship("User", foreign_keys=[created_by])

class Poll(Base):
    __tablename__ = 'polls'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(Integer, ForeignKey('messages.id'), nullable=False)
    question = Column(String, nullable=False)
    options = Column(JSON, nullable=False)  # [{"id": "1", "text": "Option 1", "votes": 0}]
    expires_at = Column(DateTime)
    allow_multiple = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message = relationship("Message")

class PollVote(Base):
    __tablename__ = 'poll_votes'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    poll_id = Column(String, ForeignKey('polls.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    option_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    poll = relationship("Poll")
    user = relationship("User", foreign_keys=[user_id])

# Настройка подключения к SQLite
engine = create_engine('sqlite:///oleg_messenger.db')
SessionLocal = sessionmaker(bind=engine)

# Для создания таблиц
if __name__ == '__main__':
    Base.metadata.create_all(engine)
