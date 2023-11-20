from datetime import datetime

users = set()


class User:
    def __init__(
        self,
        id: str,
        language: str = None,
        authorized: bool = None,
        last_updated: datetime = None,
    ):
        self.id = id
        self.language = language
        self.authorized = authorized
        self.last_updated = last_updated
        users.add(self)

    def check(id: str):
        for user in users:
            if user.id == id:
                diff = datetime.now() - user.last_updated
                if diff.seconds > 120:
                    user.unauthorize()
                return user
        user = User(id, None, False, None)
        return user

    def set_language(self, language: str):
        self.language = language

    def authorize(self):
        self.authorized = True

    def unauthorize(self):
        self.authorized = False
        self.language = None
