import pydash
from pydantic import Field

from llegos import research as llegos


class Ack(llegos.Message):
    content: str


class Teaching(llegos.Message):
    content: str


class Question(llegos.Message):
    content: str


class StudentState(llegos.Object):
    learnings: list[str] = Field(default_factory=list)


class Student(llegos.Actor):
    reflect_every: int
    state: StudentState = Field(default_factory=StudentState)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        """
        We can use the before:receive and after:receive events to implement
        a simple reflection mechanism.
        """

        def before_receive(msg: llegos.Message):
            if (
                any(self.state.learnings)
                and len(self.state.learnings) % self.reflect_every == 0
            ):
                self.reflect()

        self.on("before:receive", before_receive)

    def reflect(self):
        self.state.learnings.pop(0)

    def receive_teaching(self, msg: Teaching):
        self.state.learnings.append(msg.content)

        learnings_count = len(self.state.learnings)
        return Ack.reply_to(
            msg,
            content=f"I have learned {learnings_count} things!",
        )


class TeacherState(llegos.Object):
    teachings: list[str] = Field(min_length=1)


class Teacher(llegos.Actor):
    state: TeacherState

    def receive_question(self, msg: Question):
        return Teaching.reply_to(
            msg,
            content=pydash.sample(self.state.teachings),
        )

    def receive_ack(self, msg: Ack):
        ...


def test_student_question() -> None:
    student = Student(reflect_every=2)
    teacher = Teacher(
        state=TeacherState(teachings=["math", "science", "history"]),
    )
    msg = Question(sender=student, receiver=teacher, content="What should I learn?")

    messages = list(llegos.message_propagate(msg))
    assert len(messages) == 2, "Did not terminate after Ack"
    assert messages[0].content in {"math", "science", "history"}
    assert messages[0].sender == teacher
    assert messages[0].receiver == student
    assert messages[1].content == "I have learned 1 things!"
    assert messages[1].sender == student
    assert messages[1].receiver == teacher


def test_student_reflection() -> None:
    teachings = ["zen", "art", "motorcycle maintenace"]
    teacher = Teacher(
        state=TeacherState(teachings=teachings),
    )
    student = Student(reflect_every=2)

    def teach(content: str):
        return Teaching(sender=teacher, receiver=student, content=content)

    list(student.receive(teach(teachings[0])))
    list(student.receive(teach(teachings[1])))
    assert len(student.state.learnings) == 2
    assert student.state.learnings == teachings[:-1]

    list(student.receive(teach(teachings[2])))
    assert len(student.state.learnings) == 2, "should have trimmed learnings"


class LearningTeacher(llegos.Actor):
    student: Student
    teacher: Teacher

    def receive_question(self, msg: Question):
        return self.teacher.receive_question(msg)

    def receive_teaching(self, msg: Teaching):
        return self.student.receive_teaching(msg)

    def receive_ack(self, msg: Ack):
        return self.teacher.receive_ack(msg)


def test_learning_teacher() -> None:
    science_teacher = LearningTeacher(
        student=Student(reflect_every=2),
        teacher=Teacher(
            state=TeacherState(teachings=["biology", "chemistry", "physics"]),
        ),
    )
    maths_teacher = LearningTeacher(
        student=Student(reflect_every=2),
        teacher=Teacher(
            state=TeacherState(teachings=["algebra", "geometry", "calculus"]),
        ),
    )

    msg = Question(
        sender=maths_teacher,
        receiver=science_teacher,
        content="What should I learn?",
    )

    messages = list(llegos.message_propagate(msg))
    assert len(messages) == 2
    assert isinstance(messages[0], Teaching)
    assert messages[0].sender == science_teacher
    assert messages[0].content in {
        "biology",
        "chemistry",
        "physics",
    }
    assert isinstance(messages[1], Ack)
    assert messages[1].sender == maths_teacher
    assert messages[1].content == "I have learned 1 things!", "Ack content incorrect"

    msg = Question(
        sender=science_teacher,
        receiver=maths_teacher,
        content="What should I learn?",
    )

    messages = list(llegos.message_propagate(msg))
    assert len(messages) == 2
    assert isinstance(messages[0], Teaching)
    assert messages[0].sender == maths_teacher
    assert messages[0].content in {
        "algebra",
        "geometry",
        "calculus",
    }
    assert isinstance(messages[1], Ack)
    assert messages[1].sender == science_teacher
    assert messages[1].content == "I have learned 1 things!"
