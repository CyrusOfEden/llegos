from typing import List

import ray
from pydantic import Field
from ray.util.placement_group import placement_group
from ray.util.scheduling_strategies import PlacementGroupSchedulingStrategy

from llambdao.actor import ActorMapperNode, ActorNode
from llambdao.message import Message


class SummaryActorNode(ActorNode):
    """
    ActorNodes can be run in their own process and receive messages over a network.

    This can be useful for distributing local computation across multiple hosts.
    """

    role = "assistant"
    messages: List[Message] = Field(default_factory=list)
    actor_options = dict(num_cpus=1)  # passed through to Actor.options(**actor_options)

    def inform(self, message: Message):
        self.messages.append(message)

    def query(self, message: Message):
        summary = ""  # summarize the messages using a local LLM
        yield Message(content=summary, sender_id=self, parent_id=message)


def test_summary_actor_node():
    """
    Learn more about placement groups and clusters:

    https://docs.ray.io/en/latest/ray-core/scheduling/placement-group.html#ray-placement-group-doc-ref
    """
    ray.init(namespace="my_cluster", num_cpus=2, num_gpus=1)

    # Create a placement group bundle representing 2 1x CPU resources
    pg = placement_group([{"CPU": 1}, {"CPU": 1}])

    # Wait until the placement group is created
    ray.get(pg.ready())

    # Create the nodes, each one will get a reserved CPU core
    actor_options = dict(scheduling_strategy=PlacementGroupSchedulingStrategy(pg))
    mapper = ActorMapperNode(
        SummaryActorNode(actor_options=actor_options),
        SummaryActorNode(actor_options=actor_options),
    )
    do = Message(type="do", content="Do something!")
    for summary in ray.get(mapper.receive(do)):
        print(summary)
