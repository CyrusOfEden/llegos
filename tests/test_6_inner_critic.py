from more_itertools import take

from llegos import research as llegos


class Thought(llegos.Message):
    content: str


class Criticism(llegos.Message):
    content: str


class CriticState(llegos.Object):
    """
    The CriticState is a simple counter that keeps track of how many criticisms it has made.
    """

    counter: int = 0


class Critic(llegos.Actor):
    state: CriticState = CriticState()

    def receive_thought(self, msg: Thought):
        """
        Process the proposal and return a Criticism
        """
        self.state.counter += 1
        return Criticism.reply_to(msg, content=f"Here's criticism {self.state.counter}")


class ThinkerState(llegos.Object):
    """
    The ThinkerState is a simple counter that keeps track of how many thoughts it has made.
    """

    counter: int = 0


class Thinker(llegos.Actor):
    critic: Critic = Critic()
    state: ThinkerState = ThinkerState()

    def receive_thought(self, msg: Thought):
        """
        Process the thought and return a Proposal
        """
        return msg.forward_to(self.critic)

    def receive_criticism(self, msg: Criticism):
        """
        Process the criticism and return an improved Proposal
        """
        self.state.counter += 1
        return Thought.reply_to(
            msg,
            content=f"You cannot defeat me! {self.state.counter}",
        )


def test_inner_critic():
    user = llegos.Actor()
    thinker = Thinker()

    train_of_thought = llegos.message_propagate(
        Thought(
            sender=user,
            receiver=thinker,
            content="Here's an idea I want to do!",
        )
    )

    # let's take the first 5 messages
    messages = take(5, train_of_thought)
    assert sorted([msg.content for msg in messages]) == sorted(
        [
            "Here's an idea I want to do!",
            "Here's criticism 1",
            "You cannot defeat me! 1",
            "Here's criticism 2",
            "You cannot defeat me! 2",
        ]
    )
