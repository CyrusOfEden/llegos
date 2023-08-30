import os

from dotenv import load_dotenv

from llegos.functional import use_gen_message, use_model, use_reply_to
from llegos.research import Actor, Context, Message, SceneObject, send_and_propogate


def model(*args, **kwargs):
    return openai.ChatCompletion.create(
        model="anthropic/claude-instant-v1", *args, **kwargs
    )


jeremy_howard_system = """\
You are an autoregressive language model that has been fine-tuned with
instruction-tuning and RLHF. You carefully provide accurate, factual,
thoughtful, nuanced answers, and are brilliant at reasoning.
If you think there might not be a correct answer, you say so.

Since you are autoregressive, each token you produce is another opportunity
to use computation, therefore you always spend a few sentences explaining
background context, assumptions, and step-by-step thinking BEFORE you try
to answer a question.
"""


class CafeScene(Context):
    customer: "Customer"
    cashier: "Cashier"
    barista: "Barista"


class Item(SceneObject):
    name: str
    price: float


class Order(Message):
    items_and_counts: dict[Item, int]


class Customer(Actor):
    name: str
    temperament: str

    def enter_cafe(self):
        model_kwargs = use_model(
            system="""\
            """,
            prompt="""\
            """,
        )
        function_kwargs, parse_order = use_gen_message(
            {Order}, sender=self, receiver=self.context.cashier
        )

        order = parse_order(model(**model_kwargs, **function_kwargs))
        yield order

    def on_message(self, message: Message):
        ...

    def on_order(self, order: Order):
        ...


class Cashier(Actor):
    def on_order(self, order: Order):
        # Pass the order off to the Barista
        yield Order.forward(order, to=self.context.barista)

        # Respond to the Customer
        model_kwargs = use_model(
            system="""\
            """,
            prompt="""\
            """,
            context=order,
        )
        function_kwargs, parse_message = use_reply_to(order, {Message})
        message = parse_message(model(**model_kwargs, **function_kwargs))

        yield message


class Barista(Actor):
    def on_order(self, order: Order):
        yield Order.forward(order, to=self.context.customer)


if __name__ == "__main__":
    import openai

    load_dotenv()

    openai.api_base = "https://openrouter.ai/api/v1"
    openai.api_key = os.getenv("OPENAI_API_KEY")

    scene = CafeScene(customer=Customer(), cashier=Cashier(), barista=Barista())
    with scene.context():
        for message in send_and_propogate(scene.customer.enter_cafe()):
            print(str(message))
