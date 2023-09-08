from llegos.research import Actor, Scene


class User(Actor):
    def read(self, post: Read):
        ...


class SocialNetwork(Scene):
    def post(self, post: Post):
        ...
