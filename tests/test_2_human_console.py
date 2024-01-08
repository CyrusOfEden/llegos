"""
This test/example shows how to use Llegos to implement a human-in-the-loop pattern.
"""

from pprint import pprint

import pytest

from llegos import research as llegos
from llegos.research import Message


class ShellMessage(llegos.Message):
    content: str


class ShellHuman(llegos.Actor):
    """
    The receive_missing method is a catch-all method that gets called
    if no matching receive_{message} method is found.

    By default, it raises an error, but here we override it so that we can
    respond in the shell to the system.
    """

    def receive_missing(self, message: Message):
        print(self.id, "received new message", message.__class__.__name__)
        pprint(message.model_dump())

        """
        Get human input and respond
        """
        response = input("\nEnter your response: ")
        return ShellMessage.reply_to(message, content=response)


class ShellBot(llegos.Actor):
    def receive_shell_message(self, message: ShellMessage):
        return message.reply(content=f"Bot received: {message.content}")


@pytest.mark.skipif("not config.getoption('shell')")
def test_shell_input():
    user = ShellHuman()
    bot = ShellBot()

    initial_content = input("Enter the initial message: ")

    for _ in zip(
        llegos.message_propogate(
            ShellMessage(sender=user, receiver=bot, content=initial_content)
        ),
        range(2),
    ):
        """
        Run this test with pytest -sv --shell
        You can respond twice and the bot should reply with 'Bot received: {your response}'
        """
