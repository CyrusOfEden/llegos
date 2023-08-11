from llegos.contexts import Context
from llegos.ephemeral import EphemeralRole


class User(EphemeralRole):
    def read(self, post: Read):
        ...


class SocialNetwork(Context):
    def post(self, post: Post):
        ...
