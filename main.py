from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List
from pydantic import BaseModel

app = FastAPI()

rooms = {}

class Message(BaseModel):
    type: str  # The type of the message (e.g., "chat", "notification")
    content: str  # The actual message content
    sender: str  # The sender of the message
    active_users: int = 0  # The number of active users, optional
    room: str = 'friends-forever'  # The room name

async def broadcast_message(room: str, message: Message):
    if room in rooms:
        for client in rooms[room]:
            await client.send_text(message.json())

async def broadcast_active_users(room: str):
    if room in rooms:
        active_users_count = len(rooms[room])
        for client in rooms[room]:
            message = Message(
                type="active_users",
                content="",
                sender="",
                active_users=active_users_count,
                room=room
            )
            await client.send_text(message.json())

@app.websocket("/ws/chat/{room_name}")
async def websocket_endpoint(websocket: WebSocket, room_name: str):
    await websocket.accept()
    if room_name not in rooms:
        rooms[room_name] = []
    rooms[room_name].append(websocket)
    await broadcast_active_users(room_name)  # Notify all clients of the new user

    try:
        while True:
            data = await websocket.receive_text()
            message = Message.parse_raw(data)
            if message.room == room_name:
                await broadcast_message(room_name, message)
    except WebSocketDisconnect:
        rooms[room_name].remove(websocket)
        if not rooms[room_name]:
            del rooms[room_name]
        await broadcast_active_users(room_name)  # Notify all clients of the updated user count
        message = Message(
            type="notification",
            content="A user has left the chat.",
            sender="",
            room=room_name
        )
        await broadcast_message(room_name, message)
