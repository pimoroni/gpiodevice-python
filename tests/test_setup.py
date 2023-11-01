def test_version(gpiod):
    import gpiodevice

    assert gpiodevice.find_chip_by_label("test") is None
