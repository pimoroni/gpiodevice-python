import sys

import mock
import pytest


@pytest.fixture(scope="function", autouse=False)
def gpiod():
    gpiopd = mock.Mock()
    sys.modules["gpiod"] = gpiopd
    yield gpiod
    del sys.modules["gpiod"]


@pytest.fixture(scope="function", autouse=True)
def cleanup():
    yield
    try:
        del sys.modules["gpiodevice"]
    except KeyError:
        pass
