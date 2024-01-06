import typing as t
from itertools import combinations

from faker import Faker
from pydantic import Field
from pydash import sample

from llegos.research import Actor, Message, Object, Scene, propogate_message


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
    def receive_ping(self, ping: Ping) -> "Pong":
        return Pong.reply_to(ping)


class Pong(Message):
    ...


class Ponger(Actor):
    def receive_pong(self, pong: Pong) -> "Ping":
        return Ping.reply_to(pong)


def test_ping_pong() -> None:
    pinger = Pinger()
    ponger = Ponger()

    for m, _ in zip(propogate_message(Ping(sender=ponger, receiver=pinger)), range(4)):
        match m:
            case Ping(sender=ponger, receiver=pinger):
                ...
            case Pong(sender=pinger, receiver=ponger):
                ...
            case _:
                assert False, m


class PingPonger(Pinger, Ponger):
    ...


def test_actor_inheritance() -> None:
    a = PingPonger()
    b = PingPonger()

    for m, _ in zip(propogate_message(Ping(sender=a, receiver=b)), range(4)):
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
    name: str
    passes: int = Field(default=0)

    def receive_ball_pass(self, message: BallPass) -> BallPass:
        receiver = sample(self.receivers(BallPass))
        self.passes += 1
        message.ball.passes += 1
        return message.forward_to(receiver)


class SoccerGame(Scene):
    players: list[SoccerPlayer]

    def reset(self):
        for player in self.players:
            player.passes = 0

    def play(self):
        for a, b in combinations(self.players, 2):
            self._graph.add_edge(a, b)

        return propogate_message(
            BallPass(ball=SoccerBall(), sender=self, receiver=sample(self.players))
        )


def test_soccer_scene(faker: Faker) -> None:
    total_passes = 42
    game = SoccerGame(
        players=[SoccerPlayer(name=faker.name()) for _ in range(22)],
    )

    with game:
        for index, message in zip(range(1, total_passes + 1), game.play()):
            match message:
                case BallPass():
                    assert message.ball.passes == index
                case _:
                    assert False, message

        assert total_passes == sum(p.passes for p in game.players)


class Employee(Actor):
    name: str


class OKR(Message):
    objective: str
    key_results: list[str]


class Company(Scene):
    _receivable_messages = {OKR}

    def __init__(self, actors: t.Sequence[Employee]):
        super().__init__(actors=actors)
        for a, b in combinations(actors, 2):
            self._graph.add_edge(a, b)


class Direction(Message):
    ...


class Department(Company):
    _receivable_messages = {Direction}


def test_office_scene() -> None:
    dunder_mifflin = Company(
        actors=[
            Employee(name=name)
            for name in [
                "Michael Scott",
                "Dwight Schrute",
                "Jim Halpert",
                "Pam Beesly",
                "Ryan Howard",
                "Andy Bernard",
                "Robert California",
                "Stanley Hudson",
                "Kevin Malone",
                "Meredith Palmer",
                "Angela Martin",
                "Oscar Martinez",
                "Phyllis Vance",
                "Roy Anderson",
                "Jan Levinson",
                "Kelly Kapoor",
                "Toby Flenderson",
                "Creed Bratton",
            ]
        ]
    )

    assert dunder_mifflin._receivable_messages == {OKR}

    for employee in dunder_mifflin.actors:
        assert employee in dunder_mifflin, "Could not find employee in scene"

    # Define department membership
    sales = Department(
        actors=[
            e
            for e in dunder_mifflin.actors
            if e.name
            in {"Jim Halpert", "Dwight Schrute", "Stanley Hudson", "Phyllis Vance"}
        ]
    )
    assert sales._receivable_messages == {Direction}

    accounting = Department(
        actors=[
            e
            for e in dunder_mifflin.actors
            if e.name in {"Angela Martin", "Oscar Martinez", "Kevin Malone"}
        ]
    )
    warehouse = Department(
        actors=[
            e
            for e in dunder_mifflin.actors
            if e.name in {"Darryl Philbin", "Roy Anderson"}
        ]
    )

    # Test nested contexts
    with dunder_mifflin:
        for e in dunder_mifflin.actors:
            assert e.scene == dunder_mifflin
        with sales:
            for e in sales.actors:
                assert e.scene == sales
        with accounting:
            for e in accounting.actors:
                assert e.scene == accounting
        with warehouse:
            for e in warehouse.actors:
                assert e.scene == warehouse
