from itertools import combinations

from pydantic import Field
from pydash import sample

from .research import Actor, Message, Object, Scene, send_and_propogate


def test_message_hydration() -> None:
    a1 = Actor()
    a2 = Actor()
    m1 = Message(sender=a1, receiver=a2)
    m1_ = Message.model_validate(m1.model_dump())

    assert isinstance(m1_, Message)
    assert isinstance(m1_.sender, Actor)
    assert isinstance(m1_.receiver, Actor)
    assert m1.model_dump() == m1_.model_dump()


def test_message_reply_to() -> None:
    a1 = Actor()
    a2 = Actor()
    m1 = Message(sender=a1, receiver=a2)
    m2 = m1.reply()
    assert m2.parent == m1
    assert Message.model_validate(m2.model_dump()).parent_id == m1.id


def test_message_forward() -> None:
    a1 = Actor()
    a2 = Actor()
    a3 = Actor()
    m1 = Message(sender=a1, receiver=a2)
    m2 = m1.forward_to(a3)
    assert m2.parent == m1
    assert m2.receiver == a3


class Ping(Message):
    ...


class Pinger(Actor):
    _receivable_messages = {Ping}

    def receive_ping(self, ping: Ping) -> "Pong":
        return Pong.reply_to(ping)


class Pong(Message):
    ...


class Ponger(Actor):
    _receivable_messages = {Pong}

    def receive_pong(self, pong: Pong) -> "Ping":
        return Ping.reply_to(pong)


def test_ping_pong() -> None:
    assert Pinger._receivable_messages == {Ping}
    assert Ponger._receivable_messages == {Pong}

    pinger = Pinger()
    ponger = Ponger()

    for m, _ in zip(send_and_propogate(Ping(sender=ponger, receiver=pinger)), range(4)):
        match m:
            case Ping(sender=ponger, receiver=pinger):
                ...
            case Pong(sender=pinger, receiver=ponger):
                ...
            case _:
                assert False, m


class PingPonger(Pinger, Ponger):
    ...


def test_ping_ponger() -> None:
    assert PingPonger._receivable_messages == {Ping, Pong}

    a = PingPonger()
    b = PingPonger()

    for m, _ in zip(send_and_propogate(Ping(sender=a, receiver=b)), range(4)):
        match m:
            case Ping():
                ...
            case Pong():
                ...
            case _:
                assert False, m


class SoccerBall(Object):
    passes: int = Field(default=0)


class BallPass(Message):
    ball: SoccerBall


class SoccerPlayer(Actor):
    _receivable_messages = {BallPass}
    passes: int = Field(default=0)

    def receive_ball_pass(self, message: BallPass) -> BallPass:
        receiver = sample(self.receivers(BallPass))
        self.passes += 1  # why doesn't this work?
        return message.forward_to(
            receiver,
            # TODO: Why can't we just mutate message.ball?
            ball=SoccerBall(passes=message.ball.passes + 1),
        )


class SoccerGame(Scene):
    def __init__(self):
        super().__init__()
        self.ball = SoccerBall()
        self.players = [SoccerPlayer() for _ in range(22)]
        for a, b in combinations(self.players, 2):
            self._graph.add_edge(a, b)


def test_soccer_game() -> None:
    total_passes = 12

    with SoccerGame() as game:
        referee = Actor()
        for message, index in zip(
            send_and_propogate(
                BallPass(
                    ball=SoccerBall(), sender=referee, receiver=sample(game.players)
                )
            ),
            range(1, total_passes + 1),
        ):
            assert isinstance(message, BallPass)
            assert message.ball.passes == index

        # TODO: Get these to work
        assert game.ball.passes == total_passes
        assert sum(p.passes for p in game.players) == total_passes
