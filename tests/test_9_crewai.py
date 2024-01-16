import typing as t

from beartype.typing import Optional
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
    llm: t.Any
    counter: int = Field(default=0)

    def receive_task(self, task: Task) -> str:
        self.counter += 1
        return Result.reply_to(task, content="42" + ("!" * self.counter))


class Crew(llegos.Network):
    tasks: list[Task]

    def perform(self):
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


def test_crewai():
    crew = Crew(
        actors=[
            Agent(
                name="Copywriter",
                role="copywriter",
                goal="",
                backstory="",
                llm="",
            ),
            Agent(
                name="Brand Strategist",
                role="brand-strategist",
                goal="",
                backstory="",
                llm="",
            ),
            Agent(
                name="Social Media Marketer",
                role="social-media-marketer",
                goal="",
                backstory="",
                llm="",
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

    # We can use the generator to keep running tasks until they are all done
    generator = crew.perform()

    res_1 = t.cast(Result, next(generator))  # for type checking
    assert res_1.content == "42!"
    assert res_1.sender == crew.actors[0]
    assert res_1.parent
    assert res_1.parent.description == crew.tasks[0].description
    assert res_1.parent.content == "Task 1"

    res_2 = t.cast(Result, next(generator))  # for type checking
    assert res_2.content == "42!!"
    assert res_2.sender == crew.actors[0]
    assert res_2.parent
    assert res_2.parent.description == crew.tasks[1].description
    assert res_2.parent.content == "42!\n\nTask 2"

    res_3 = t.cast(Result, next(generator))  # for type checking
    assert res_3.content == "42!!!"
    assert res_3.sender == crew.actors[0]
    assert res_3.parent
    assert res_3.parent.description == crew.tasks[2].description
    assert res_3.parent.content == "42!!\n\nTask 3"

    try:
        "Now we're done processing the tasks"
        next(generator)
        assert False
    except StopIteration:
        assert True
