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


def test_find_chip_by_pins_closes_rejected_chips(gpiod, monkeypatch):
    """A chip we don't return must be closed inside the loop.

    Leaving one bound to the generator's frame means gpiod's close() runs while
    StopIteration is propagating out of it, which raises SystemError instead of
    returning None.
    """
    import gpiodevice

    monkeypatch.setattr(gpiodevice.glob, "glob", lambda pattern: ["/dev/gpiochip0", "/dev/gpiochip1"])
    gpiod.is_gpiochip_device.return_value = True

    chip = gpiod.Chip.return_value
    chip.get_info.return_value.label = "fake-gpiochip"
    chip.line_offset_from_id.side_effect = OSError

    assert gpiodevice.find_chip_by_pins("GPIO1", fatal=False) is None
    assert chip.close.call_count == 2


def test_find_chip_by_pins_does_not_close_the_chip_it_returns(gpiod, monkeypatch):
    import gpiodevice

    monkeypatch.setattr(gpiodevice.glob, "glob", lambda pattern: ["/dev/gpiochip0"])
    gpiod.is_gpiochip_device.return_value = True

    chip = gpiod.Chip.return_value
    chip.get_info.return_value.label = "fake-gpiochip"
    chip.line_offset_from_id.return_value = 1
    chip.get_line_info.return_value.used = False

    assert gpiodevice.find_chip_by_pins("GPIO1") is chip
    chip.close.assert_not_called()
