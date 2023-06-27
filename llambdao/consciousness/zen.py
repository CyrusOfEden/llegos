from abc import ABC
from typing import Iterator

from llambdao.message import Message, Node


class Zen(Node, ABC):
    def receive(self, message: Message) -> Iterator[Message]:
        for shonen in self.shonen(message):
            yield shonen

            for junen in self.junen(shonen):
                yield junen

                for honen in self.honen(junen):
                    yield honen

    def shonen(self, message: Message) -> Iterator[Message]:
        """
        Shonen corresponds to the first unit of thought,
        the immediate perception of an object or event.

        This function would contain the logic corresponding to the agent's
        immediate reaction to the incoming message.

        Args:
            message (Message): Incoming message that the node immediately perceives.

        Yields:
            Iterator[Message]: Yields messages representing direct responses
        """
        pass

    def junen(self, message: Message) -> Iterator[Message]:
        """
        Junen corresponds to the second unit of thought,
        reflection or consideration of the object or event perceived in the shonen.

        In this function, the 'message' initially perceived in shonen
        is further contemplated, analyzed, and interpreted.

        Args:
            message (Message): Incoming message that the node perceives and contemplates.

        Yields:
            Iterator[Message]: Yields messages representing thoughtful responses
        """
        pass

    def honen(self, message: Message) -> Iterator[Message]:
        """
        Honen corresponds to the third unit of thought,
        involving the further development of thoughts arising from the junen.

        In this function, thoughts and interpretations from the junen stage are further expanded,
        potentially involving planning a response, creating a narrative around the event,
        or exploring deeper emotional reactions.

        Args:
            message (Message): Incoming message that the node perceives, interprets, and reacts to.

        Yields:
            Iterator[Message]: Yields messages representing thoughtful responses
        """
        pass
