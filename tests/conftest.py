import contextlib
import sys
from unittest import mock

import pytest


@pytest.fixture(scope="function", autouse=False)
def gpiod():
    gpiopd = mock.Mock()
    sys.modules["gpiod"] = gpiopd
    sys.modules["gpiod.line"] = mock.Mock()
    yield gpiopd
    del sys.modules["gpiod"]
    del sys.modules["gpiod.line"]


@pytest.fixture(scope="function", autouse=True)
def cleanup():
    yield
    with contextlib.suppress(KeyError):
        del sys.modules["gpiodevice"]
