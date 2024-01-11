from pydantic import Field

from llegos import research as llegos


class MapRequest(llegos.Message):
    query: str


class MapResponse(llegos.Message):
    sources: list[str]


class Mapper(llegos.Actor):
    sources: list[str] = Field(
        description="A list of sources that this actor can query"
    )

    def can_receive(self, message):
        """
        This method is called when receiving a message to determine if the
        actor can receive the message. If this method returns False, the
        actor will raise a llegos.InvalidMessage error.

        You can use this method to implement custom logic, like checking
        if the message is of a certain type, or if the message is from
        a certain sender, or if the sender has the proper authorization, etc.

        By default, can_receive verifies that the message.recipient is the
        actor, and that the message.sender is not the actor.
        """
        return super().can_receive(message)

    def receive_map_request(self, request: MapRequest):
        """
        Method names are f"receive_{camel_case(MessageClassName)}", so the
        SourcesRequest message dispatches to this receive_sources_request method.
        """
        return MapResponse.reply_to(request, sources=self.sources)


class ReduceRequest(llegos.Message):
    sources: list[str]


class ReduceResponse(llegos.Message):
    unique_sources: list[str]


class Reducer(llegos.Actor):
    """
    This example reducer just does the set overlap of all the sources returned,
    but you can imagine a more complex reducer that does some sort of ranking,
    or synthesis/summarization, etc.
    """

    def receive_reduce_request(self, request: ReduceRequest):
        """
        Messages are immutable, so you can't just append to the sources list.
        Instead, you have to create a new message with the new sources list.

        MessageClass.reply_to(msg, **kwargs) will create a new message of type
        MessageClass by copying over the attributes of msg, and updating (or adding)
        to them with the kwargs. In this case, we're creating a new Response message
        """
        unique_sources = list(set(request.sources))
        return ReduceRequest.reply_to(request, unique_sources=unique_sources)


class MapReducer(llegos.Network):
    """
    Networks compose multiple Actors together. Networks are also Actors, so you can
    compose Networks together to create more complex Networks.
    """

    reducer: Reducer

    def __init__(self, reducer: Reducer, sources: list[Mapper]):
        """
        The constructor accepts a list of actors which are used to initialize the
        underlying graph. This is important! Do not forget to pass actors=[a1, a2, ...]
        """
        super().__init__(reducer=reducer, actors=[reducer, *sources])
        for source in sources:
            """
            Here's where the magic happens. The llegos.Network class has a private
            networkx.MultiGraph that keeps track of all the actors and their relationships.

            The intuition behind this is simple — as humans we have different relationships
            in different networks, simultaneously. For example, you might be a friend to
            someone in your family, and a sibling to someone in your friend group.

            Llegos lets you model the Family as a Network, and the Friend Group as a Network,
            and the same Actor can be in both Networks, and have different relationships
            in each Network.
            """
            self._graph.add_edge(reducer, source, metadata={"key": "value"})

    def receive_map_request(self, request: MapRequest):
        """
        Use 'with {network}:' to enter the network's context.
        Here, all relationships are scoped to that network.
        """
        with self:
            """
            First, we use .receivers(MessageClass) to get all the actors in the network that
            can receive the SourcesRequest message.
            """
            sourcers = self.receivers(MapRequest)
            sources: list[str] = []
            for s in sourcers:
                """
                Messages have email semantics, so you can use .forward_to(new_actor)
                to send a message to another actor, and the message will be of the
                same type, but with sender=receiver, and receiver=new_actor
                """
                msg = request.forward_to(s)
                for response in llegos.message_send(msg):
                    match response:
                        case MapResponse():
                            sources.extend(response.sources)

            fuse_req = ReduceRequest(
                sources=sources, sender=self, receiver=self.reducer
            )
            """
            message_send returns an iterator, because a receiver can return or yield
            multiple messages in response to a single message.

            By using llegos.message_send(message) or Actor.receive(message)
            receive_{message} methods that return a single message will be wrapped in


            Here we use next() to get the first message in the iterator, since we know
            that there will only be one.
            """
            fuse_resp = next(llegos.message_send(fuse_req))
            return MapResponse.reply_to(request, sources=fuse_resp.unique_sources)


def test_map_reducer():
    test_actor = llegos.Actor()  # a simple, dummy actor with no utility
    sources_map_reducer = MapReducer(
        Reducer(),
        [
            Mapper(sources=["The Hitchhiker's Guide to the Galaxy", "Star Wars"]),
            Mapper(sources=["Doctor Who", "Star Wars"]),
        ],
    )

    request = MapRequest(
        sender=test_actor,
        receiver=sources_map_reducer,
        query="Query?",
    )

    response = next(llegos.message_send(request))
    assert isinstance(response, MapResponse)
    assert sorted(response.sources) == sorted(
        [
            "The Hitchhiker's Guide to the Galaxy",
            "Star Wars",
            "Doctor Who",
        ]
    )


def test_nested_map_reducer():
    """
    Since Networks are Actors, you can compose Networks together to create more complex
    Networks. Here, we compose two SourcesMapReducers together in another .

    This works because the MapReducer implements the same interface as a Sources,
    so it acts as a drop-in replacement.
    """

    test_actor = llegos.Actor()  # a simple, dummy actor with no utility
    nested_map_reducer = MapReducer(
        Reducer(),
        [
            Mapper(sources=["The Hitchhiker's Guide to the Galaxy", "Star Wars"]),
            Mapper(sources=["Doctor Who", "Star Wars"]),
        ],
    )

    root_map_reducer = MapReducer(
        Reducer(),
        [
            nested_map_reducer,
            Mapper(sources=["Star Trek", "Star Wars"]),
        ],
    )

    request = MapRequest(
        sender=test_actor,
        receiver=root_map_reducer,
        query="Query?",
    )

    with root_map_reducer:
        """
        Use 'with {network}:' to enter the network's context.
        Here, all relationships are scoped to that network.
        """

        response = next(llegos.message_send(request))
        assert isinstance(response, MapResponse)
        assert sorted(response.sources) == sorted(
            [
                "The Hitchhiker's Guide to the Galaxy",
                "Star Wars",
                "Doctor Who",
                "Star Trek",
            ]
        )
