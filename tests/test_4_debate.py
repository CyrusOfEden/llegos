from random import random
from typing import Sequence, Union

from pydantic import Field

from llegos import research as llegos


class Proposition(llegos.Message):
    content: str


class Rebuttal(llegos.Message):
    content: str


class Agreement(llegos.Message):
    content: str


class Debater(llegos.Actor):
    def receive_proposition(self, message: Proposition):
        if random() < 0.5:
            return Rebuttal.reply_to(message, content="I disagree")
        else:
            return Agreement.reply_to(message, content="I agree")

    def receive_rebuttal(self, message: Rebuttal):
        if random() < 0.5:
            return Rebuttal.reply_to(message, content="I disagree")
        else:
            return Agreement.reply_to(message, content="I agree")

    def receive_argument(self, message: Agreement):
        if random() < 0.5:
            return Rebuttal.reply_to(message, content="I disagree")
        else:
            return Agreement.reply_to(message, content="I agree")


class Review(llegos.Message):
    points: Sequence[Union[Agreement, Rebuttal]]


class Verdict(Review):
    content: str


class Judge(llegos.Actor):
    def receive_review(self, message: Review):
        agreements = sum(1 for point in message.points if isinstance(point, Agreement))
        rebuttals = sum(1 for point in message.points if isinstance(point, Rebuttal))

        return Verdict.reply_to(
            message,
            content="I agree" if agreements >= rebuttals else "I disagree",
        )


class Debate(llegos.Scene):
    rounds: int = Field(ge=1, le=5)
    judge: Judge
    debaters: Sequence[Debater]

    def __init__(self, judge: Judge, debaters: Sequence[Debater], **kwargs):
        super().__init__(
            judge=judge,
            debaters=debaters,
            **kwargs,
            actors=[judge, *debaters],
        )

    def receive_proposition(self, message: Proposition):
        responses = []

        for _round in range(self.rounds):
            for debater in self.debaters:
                for response in llegos.message_send(message.forward_to(debater)):
                    responses.append(response)

        verdict = next(
            self.judge.send(Review(points=responses, sender=self, receiver=self.judge))
        )
        return verdict.forward_to(message.sender)


def test_debate(num_rounds=3):
    user = llegos.Actor()
    judge = Judge()
    debaters = [Debater(), Debater(), Debater()]
    debate = Debate(judge=judge, debaters=debaters, rounds=num_rounds)
    proposition = Proposition(
        sender=user,
        receiver=debate,
        content="Apple pie is the best",
    )

    verdict = next(debate.send(proposition))
    assert isinstance(verdict, Verdict)
    assert verdict.content in ("I agree", "I disagree")
    assert len(verdict.points) == num_rounds * len(debaters)
