from llm_net.base import AbstractObject, Field, GenNetwork, Iterable, Message


class RGN(GenNetwork):
    """RGN: Recurrent Generative Network"""

    hidden_state: AbstractObject = Field()

    def receive(self, message: Message) -> Iterable[Message]:
        for response in super().receive(message):
            [*responses, self.hidden_state] = list(self.forward(response))
            yield from responses

    def forward(self, message: Message) -> Iterable[Message]:
        ...


class TGN(GenNetwork):
    """TGN: Transformer Generative Network"""

    def receive(self, message: Message) -> Iterable[Message]:
        yield from self.forward(super().receive(message))

    def forward(self, messages: Iterable[Message]) -> Iterable[Message]:
        ...
