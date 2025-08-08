import uuid
from fastapi import Request

class SessionManager:
    def __init__(self):
        self.sessions = {}

    def get_session(self, request: Request):
        session_id = request.cookies.get("session_id")
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {}
        return self.sessions[session_id]

session_manager = SessionManager()
