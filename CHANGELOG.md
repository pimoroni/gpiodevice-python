# Changelog

0.1.0
-----

* Enhancement: Repackage to the uv/hatchling method, with PyPI trusted publishing
* Enhancement: Version is derived from the git tag, __version__ from package metadata
* New: Nvidia Jetson platform support
* Python 3.9 or later, 3.7 and 3.8 support dropped

0.0.5
-----

* Add support for int type in get_pin

0.0.4
-----

* Gracefully handle a tuple being passed to get_pin
* Match all pinctrl- gpiodevices for RPi in get_gpiochip_labels

0.0.3
-----

* Deprecate the `friendly_errors` flag in favour of a new `fatal` flag on methods
* Catch use of `int` pin numbers from unported code and raise a friendly error

0.0.2
-----

* Add platform detection
* ROCK 5B support
* Bug fixes

0.0.1
-----

* Initial Release
