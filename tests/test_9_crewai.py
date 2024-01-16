import typing as t

from beartype.typing import Iterator, Optional
from matchref import ref
from pydantic import Field, computed_field
from sorcery import maybe

from llegos import research as llegos


class Task(llegos.Message):
    description: str
    context: Optional[str] = None

    @computed_field
    @property
    def content(self) -> str:
        if self.context:
            return f"{self.context}\n\n{self.description}"
        return self.description


class Result(llegos.Message):
    content: str


class Agent(llegos.Actor):
    name: str
    role: str
    goal: str
    backstory: str
    executor: t.Any = Field(description="AgentExecutor")
    counter: int = Field(default=0)

    def receive_task(self, task: Task) -> str:
        self.counter += 1
        return Result.reply_to(task, content="42" + ("!" * self.counter))


class Crew(llegos.Network):
    tasks: list[Task]

    def perform(self) -> Iterator[Result]:
        result = None
        for task in self.tasks:
            agent = next(a for a in self.actors if a.can_receive(task))
            result = next(
                agent.receive(
                    task.forward_to(
                        agent,
                        sender=self,
                        context=maybe(result).content,
                    )
                )
            )
            yield result

    def receive_task(self, task: Task) -> Iterator[Result]:
        # Plan some tasks
        self.tasks = [task]
        for result in self.perform():
            yield result.forward_to(task.sender)


def test_crewai():
    crew = Crew(
        actors=[
            Crew(
                actors=[
                    Agent(
                        name="Copywriter",
                        role="copywriter",
                        goal="",
                        backstory="",
                        executor=None,
                    ),
                ],
                tasks=[],
            ),
            Agent(
                name="Copywriter",
                role="copywriter",
                goal="",
                backstory="",
                executor=None,
            ),
            Agent(
                name="Brand Strategist",
                role="brand-strategist",
                goal="",
                backstory="",
                executor=None,
            ),
        ],
        tasks=[
            Task(
                description="Task 1",
            ),
            Task(
                description="Task 2",
            ),
            Task(
                description="Task 3",
            ),
        ],
    )

    nested_crew = crew.actors[0]
    assert isinstance(nested_crew, Crew)
    assert nested_crew.tasks == []

    # We can use the generator to keep running tasks until they are all done
    for result in crew.perform():
        assert result.parent, "Result should have a parent"

        match result:
            case Result(sender=ref.nested_crew, content="42!"):
                assert result.parent.description == crew.tasks[0].description
            case Result(sender=ref.nested_crew, content="42!!"):
                assert result.parent.description == crew.tasks[1].description
            case Result(sender=ref.nested_crew, content="42!!!"):
                assert result.parent.description == crew.tasks[2].description
