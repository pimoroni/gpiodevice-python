import pytest


def test_find_chip_by_pins_int(gpiod):
    import gpiodevice

    with pytest.raises(SystemExit):
        gpiodevice.find_chip_by_pins(1)


def test_find_chip_by_pins_quiet(gpiod):
    import gpiodevice

    assert gpiodevice.find_chip_by_pins(1, fatal=False) is None
    assert gpiodevice.find_chip_by_pins("GPIO1", fatal=False) is None


def test_find_chip_by_pins_str(gpiod):
    import gpiodevice

    with pytest.raises(SystemExit):
        gpiodevice.find_chip_by_pins("GPIO1")
