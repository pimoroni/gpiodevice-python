# gpiodevice

[![Build Status](https://img.shields.io/github/actions/workflow/status/pimoroni/gpiodevice-python/test.yml?branch=main)](https://github.com/pimoroni/gpiodevice-python/actions/workflows/test.yml)
[![Coverage Status](https://coveralls.io/repos/github/pimoroni/gpiodevice-python/badge.svg?branch=main)](https://coveralls.io/github/pimoroni/gpiodevice-python?branch=main)
[![PyPi Package](https://img.shields.io/pypi/v/gpiodevice.svg)](https://pypi.python.org/pypi/gpiodevice)
[![Python Versions](https://img.shields.io/pypi/pyversions/gpiodevice.svg)](https://pypi.python.org/pypi/gpiodevice)

A GPIO counterpart to [i2cdevice](https://github.com/pimoroni/i2cdevice-python), generated from [the Pimoroni Python Boilerplate](https://github.com/pimoroni/boilerplate-python).

## What is gpiodevice?

gpiodevice is a middleware library intended to make some user-facing aspects of interfacing with Linux's GPIO character device ABI (via gpiod) simpler and friendlier.

gpiodevice is not intended to replace gpiod, but collects some common patterns into a reusable library for GPIO-based Python projects.

# Installing

We'd recommend using this library with Raspberry Pi OS Bookworm or later. It requires Python >=3.9.

gpiodevice is usually installed as a dependency of another library. To install gpiodevice:

* Set up a virtual environment: `python3 -m venv --system-site-packages $HOME/.virtualenvs/pimoroni`
* Switch to the virtual environment: `source ~/.virtualenvs/pimoroni/bin/activate`
* Install the library: `pip install gpiodevice`

## Development:

```bash
git clone https://github.com/pimoroni/gpiodevice-python
cd gpiodevice-python
./install.sh --unstable
```

# Finding A gpiochip

A pin's `/dev/gpiochip*` varies between boards and kernel versions. These functions return a `gpiod.Chip`.

## By Pin Name

```python
import gpiodevice

chip = gpiodevice.find_chip_by_pins("GPIO4")
chip = gpiodevice.find_chip_by_pins(("GPIO4", "GPIO17"))
chip = gpiodevice.find_chip_by_pins("GPIO4,GPIO17")
```

Returns the first gpiochip carrying all of the named pins. Pin names are those reported by the kernel.

A pin claimed by another consumer counts as a failure. Pass `ignore_claimed=True` to match on the name alone.

## By Chip Label

```python
import gpiodevice

chip = gpiodevice.find_chip_by_label("pinctrl-rp1")
chip = gpiodevice.find_chip_by_label(("pinctrl-rp1", "pinctrl-bcm2711"))
```

Returns the first gpiochip whose label matches. Labels are matched as regular expressions.

```python
import gpiodevice

chip = gpiodevice.find_chip_by_label("pinctrl-rp1", pins={"my sensor": "GPIO4"})
```

Supply `pins` to also require that those pins are free.

## By Platform

```python
import gpiodevice

chip = gpiodevice.find_chip_by_platform()
```

Reads the board model and matches the chip labels known for it. Raspberry Pi, Radxa, NVIDIA Jetson and the Alienware m15 are supported.

```python
import gpiodevice

name = gpiodevice.platform.get_name()
labels = gpiodevice.platform.get_gpiochip_labels()
```

`get_name` returns the detected board name. `get_gpiochip_labels` returns the labels tried for it. Both raise `RuntimeError` on an unrecognised board.

# Requesting Pins

```python
import gpiod
import gpiodevice
from gpiod.line import Direction, Value

settings = gpiod.LineSettings(direction=Direction.OUTPUT)
request, offset = gpiodevice.get_pin("GPIO4", "my led", settings)

request.set_value(offset, Value.ACTIVE)
```

`get_pin` requests one pin by name. It finds the chip and resolves the name to a line offset. It returns the `gpiod.LineRequest` and that offset.

The second argument labels the pin. It forms part of the consumer name reported by `gpioinfo`.

`pin` also accepts:

* An int line offset. The platform's chip is used.
* A `(request, offset)` tuple. This is returned unchanged.

```python
import gpiod
import gpiodevice
from gpiod.line import Direction

settings = gpiod.LineSettings(direction=Direction.OUTPUT)

pins = gpiodevice.get_pins_for_platform({
    "Raspberry Pi 5": {"my led": ("GPIO4", settings)},
    "Raspberry Pi 4": {"my led": ("GPIO4", settings)},
})
```

`get_pins_for_platform` takes a mapping of platform name prefix to pins. It returns a list of `(request, offset)` for the entry matching the detected board.

# Edge Detection

A pin must be requested with edge detection for any of these to see events.

## wait_for_edge

```python
import gpiod
import gpiodevice
from gpiod.line import Bias, Edge

settings = gpiod.LineSettings(edge_detection=Edge.FALLING, bias=Bias.PULL_UP)
request, offset = gpiodevice.get_pin("GPIO4", "my button", settings)

event = gpiodevice.wait_for_edge(request, line=offset, timeout=5.0)
```

Blocks until an edge arrives. Returns the `gpiod` event, or `None` on timeout.

* `timeout` is in seconds or a `timedelta`. `None` waits indefinitely.
* `line` filters events to one offset. Omit it to take the first event on any line.
* `raise_on_timeout` raises `TimeoutError` instead of returning `None`.

## watch_pin

```python
import time
import gpiodevice
from gpiod.line import Bias, Edge

def handle_button(event):
    print(f"edge on line {event.line_offset}")

watch = gpiodevice.watch_pin(
    "GPIO4",
    edge=Edge.FALLING,
    bias=Bias.PULL_UP,
    debounce=0.02,
    callback=handle_button,
)

try:
    while True:
        time.sleep(1.0)
finally:
    watch.close()
```

Requests one pin and returns a started `Watch`.

* `callback` is called with the `gpiod` event on each edge.
* `debounce` is in seconds or a `timedelta`.

`watch_pin` owns the request it made. `close()` stops the thread and releases the line.

## Watch

```python
import gpiod
import gpiodevice
from gpiod.line import Bias, Edge

BUTTONS = {"A": "GPIO5", "B": "GPIO6"}
settings = gpiod.LineSettings(edge_detection=Edge.FALLING, bias=Bias.PULL_UP)

chip = gpiodevice.find_chip_by_pins(tuple(BUTTONS.values()))
offsets = {label: chip.line_offset_from_id(pin) for label, pin in BUTTONS.items()}
request = chip.request_lines(
    consumer="buttons",
    config={offset: settings for offset in offsets.values()}
)

def handler(label):
    return lambda event: print(f"button {label}")

with gpiodevice.Watch(request, {offset: handler(label) for label, offset in offsets.items()}) as watch:
    input("Press Ctrl+C to exit!\n")
```

Watches a request you made yourself. Edges are dispatched on a background thread.

`handlers` is a mapping of line offset to callable. Pass a single callable to use it for every line. Edges on lines with no handler are ignored.

As a context manager the watch starts on entry and closes on exit. Otherwise call `start()` and `stop()`. `start()` is idempotent.

`close()` stops the thread. It also releases the request, but only if the `Watch` owns it. A `Watch` you construct does not, unless you pass `manage_request=True`.

# Errors

```python
import gpiodevice

chip = gpiodevice.find_chip_by_pins("GPIO4", fatal=False)
if chip is None:
    ...
```

The `find_*` functions and `check_pins_available` raise `SystemExit` with a digest of everything they tried:

```
Woah there, suitable gpiochip not found!
  ✅  GPIO22: (line 22) found - /dev/gpiochip4 (pinctrl-rp1)!
  ⚠️   GPIO22: (line 22, GPIO22) currently claimed by some-other-app
  ✅  GPIO22: (line 22) found - /dev/gpiochip0 (pinctrl-rp1)!
  ⚠️   GPIO22: (line 22, GPIO22) currently claimed by some-other-app
  ❌  GPIO22: not found - /dev/gpiochip13 (gpio-brcmstb@107d508520)!
  ❌  GPIO22: not found - /dev/gpiochip10 (gpio-brcmstb@107d508500)!
```

Pass `fatal=False` to return `None` instead. Set `GPIODEVICE_DEBUG` in the environment to raise a `RuntimeError` with a traceback.

```python
import gpiodevice

chip = gpiodevice.find_chip_by_platform()
free = gpiodevice.check_pins_available(chip, {"my led": "GPIO4"}, fatal=False)
```

`check_pins_available` reports whether a set of pins are free. It does not request them.
