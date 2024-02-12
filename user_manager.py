from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


class Manager:
    users: Dict[str, "User"]

    def __init__(self):
        self.users = {}

    def add_user(self, chat: str) -> "User":
        user: User = User()
        self.users[chat] = user
        return user
    
    def check_user(self, chat: str):
        if self.users.get(chat):
            diff = (datetime.now()-self.users.get(chat).ts).total_seconds()
            if diff > 300:
                self.users.get(chat).set_language(None)
                return None
            self.users[chat].update_ts()
            return self.users[chat]
        return self.add_user(chat)


@dataclass
class User:
    language: Optional[str] = None
    ts: Optional[datetime] = None
    
    def __init__(self):
        self.ts = datetime.now()

    def set_language(self, language: str):
        self.language = language

    def update_ts(self):
        self.ts = datetime.now()