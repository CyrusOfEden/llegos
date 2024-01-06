from pytest import Parser


def pytest_addoption(parser: Parser):
    parser.addoption(
        "--shell",
        action="store_true",
        dest="shell",
        default=False,
        help="Run tests requiring shell input",
    )
