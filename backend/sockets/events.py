from flask_socketio import emit, join_room, leave_room
from ..extensions import socketio


@socketio.on("connect", namespace="/chat")
def handle_connect():
    emit("system", {"message": "Connected to chat"})


@socketio.on("join", namespace="/chat")
def handle_join(data):
    room = data.get("room")
    join_room(room)
    emit("system", {"message": f"Joined room {room}"}, to=room)


@socketio.on("message", namespace="/chat")
def handle_message(data):
    room = data.get("room")
    msg = data.get("message")
    emit("message", {"room": room, "message": msg}, to=room)
