from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from models import db, User, Chat, Message
import os

# Flask app init
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///oleg_messenger.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "supersecretkey"

# Extensions
db.init_app(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
CORS(app)

# ---------------------------
# ROUTES
# ---------------------------

@app.route("/")
def home():
    return {"message": "Hello from Oleg Messenger!"}

# ---------------------------
# AUTH
# ---------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    if not data.get("username") or not data.get("password"):
        return jsonify({"error": "Missing fields"}), 400
    
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "User already exists"}), 400
    
    hashed_pw = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    new_user = User(username=data["username"], password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"message": "User registered successfully"})

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get("username")).first()
    if not user or not bcrypt.check_password_hash(user.password, data.get("password")):
        return jsonify({"error": "Invalid credentials"}), 401
    
    session["user_id"] = user.id
    return jsonify({"message": "Login successful", "user_id": user.id})

@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"message": "Logged out"})

# ---------------------------
# CHATS
# ---------------------------
@app.route("/api/chats", methods=["GET"])
def get_chats():
    chats = Chat.query.all()
    return jsonify([{"id": c.id, "name": c.name} for c in chats])

@app.route("/api/chats", methods=["POST"])
def create_chat():
    data = request.json
    if not data.get("name"):
        return jsonify({"error": "Chat name required"}), 400
    
    new_chat = Chat(name=data["name"])
    db.session.add(new_chat)
    db.session.commit()
    
    return jsonify({"message": "Chat created", "id": new_chat.id})

# ---------------------------
# MESSAGES
# ---------------------------
@app.route("/api/messages/<int:chat_id>", methods=["GET"])
def get_messages(chat_id):
    messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.timestamp).all()
    return jsonify([
        {"id": m.id, "user": m.user.username, "content": m.content, "timestamp": m.timestamp.isoformat()}
        for m in messages
    ])

@app.route("/api/messages/<int:chat_id>", methods=["POST"])
def send_message(chat_id):
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    new_msg = Message(content=data.get("content"), user_id=session["user_id"], chat_id=chat_id)
    db.session.add(new_msg)
    db.session.commit()
    
    return jsonify({"message": "Message sent", "id": new_msg.id})

@app.route("/api/messages/<int:msg_id>", methods=["PUT"])
def edit_message(msg_id):
    msg = Message.query.get_or_404(msg_id)
    if msg.user_id != session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json
    msg.content = data.get("content", msg.content)
    db.session.commit()
    return jsonify({"message": "Message updated"})

@app.route("/api/messages/<int:msg_id>", methods=["DELETE"])
def delete_message(msg_id):
    msg = Message.query.get_or_404(msg_id)
    if msg.user_id != session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 403
    
    db.session.delete(msg)
    db.session.commit()
    return jsonify({"message": "Message deleted"})

# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
