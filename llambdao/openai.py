import json
from textwrap import dedent

from llambdao import Message


class OpenAIMessage(Message):
    def json(self):
        return {
            "role": self.sender.role,
            "content": dedent(
                f"""\
                Message ID: {self.id}
                In Reply To: {self.reply_to and self.reply_to.id}
                Metadata: {json.dump(self.metadata)}
                Content: {self.content}
                """
            ),
        }
