import pytest
from app import create_app
from extensions import db
from config import Config
import os
import tempfile
import json

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_register_and_login(client):
    r = client.post('/api/auth/register', json={'email':'a@a.com','username':'user1','password':'pass'})
    assert r.status_code == 200
    data = r.get_json()
    assert 'access' in data
    r2 = client.post('/api/auth/login', json={'username':'user1','password':'pass'})
    assert r2.status_code == 200
    data2 = r2.get_json()
    assert 'access' in data2
