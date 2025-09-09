# minimal seed script to create demo users and a server with a channel
from app import create_app
from extensions import db
from models.user import User
from models.server import Server
from models.channel import Channel
from models.member import Member

app = create_app()

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='alice').first():
        u1 = User(email='alice@example.com', username='alice')
        u1.set_password('password')
        u2 = User(email='bob@example.com', username='bob')
        u2.set_password('password')
        db.session.add_all([u1, u2])
        db.session.commit()
        s = Server(name='Demo Server', owner_id=u1.id)
        db.session.add(s)
        db.session.commit()
        c = Channel(server_id=s.id, name='general')
        db.session.add(c)
        db.session.commit()
        m1 = Member(user_id=u1.id, server_id=s.id, role='owner')
        m2 = Member(user_id=u2.id, server_id=s.id, role='member')
        db.session.add_all([m1, m2])
        db.session.commit()
        print('Seeded demo users and server.')
    else:
        print('Already seeded.')
