import glob
import os

import gpiod

__version__ = "0.0.1"

DEBUG = os.getenv("GPIODEVICE_DEBUG", None) is not None
CHIP_GLOB = "/dev/gpiochip*"

friendly_errors: bool = False


class ErrorDigest(RuntimeError):
    pass


class GPIOBaseError:
    def __init__(self, message: str, icon: str = " "):
        self.icon = icon
        self.message = message

    def __str__(self):
        return f"  {self.icon}  {self.message}"

    def __repr__(self):
        return str(self)


class GPIOError(GPIOBaseError):
    def __init__(self, message: str, icon: str = "⚠️ "):
        GPIOBaseError.__init__(self, message, icon)


class GPIONotFound(GPIOBaseError):
    def __init__(self, message: str, icon: str = "❌"):
        GPIOBaseError.__init__(self, message, icon)


class GPIOFound(GPIOBaseError):
    def __init__(self, message: str, icon: str = "✅"):
        GPIOBaseError.__init__(self, message, icon)


def error_digest(fn):
    def wrapper(*args, **kwargs):
        errors = []

        i = iter(fn(*args, **kwargs))

        while True:
            try:
                errors.append(next(i))
            except StopIteration as e:
                return e.value
            except ErrorDigest as e:
                msg = f"{e}\n" + "\n".join([str(e) for e in errors])
                if DEBUG:
                    raise RuntimeError(msg) from None
                else:
                    raise SystemExit(f"Woah there, {msg}")

    return wrapper


@error_digest
def check_pins_available(chip: gpiod.Chip, pins) -> bool:
    """Check if a list of pins are in use on a given gpiochip device.

    Raise a RuntimeError with a friendly list of in-use pins and their consumer if
    any are in used.

    """
    if pins is None:
        return True

    used = 0

    for (label, pin) in pins.items():
        if isinstance(pin, str):
            try:
                pin = chip.line_offset_from_id(pin)
            except OSError:
                yield GPIOError(f"{label}: (line {pin}) not found!")
                continue

        line_info = chip.get_line_info(pin)

        if line_info.used:
            used += 1
            yield GPIOError(f"{label}: (line {pin}) currently claimed by {line_info.consumer}")

    if used and friendly_errors:
        raise ErrorDigest("some pins we need are in use!")

    return used == 0


@error_digest
def find_chip_by_label(labels: (list[str], tuple[str], str), pins: dict[str, (int, str)] = None):
    """Try to find a gpiochip device matching one of a set of labels.

    Raise a RuntimeError with a friendly error digest if one is not found.

    """
    if isinstance(labels, str):
        labels = (labels,)

    for path in glob.glob(CHIP_GLOB):
        if gpiod.is_gpiochip_device(path):
            try:
                label = gpiod.Chip(path).get_info().label
            except PermissionError:
                yield GPIOError(f"{path}: Permission error!")
                continue

            if label in labels:
                chip = gpiod.Chip(path)
                if check_pins_available(chip, pins):
                    return chip
            else:
                yield GPIONotFound(f"{path}: this is not the GPIO we're looking for! ({label})")

    if friendly_errors:
        raise ErrorDigest("suitable gpiochip device not found!")

    return None


@error_digest
def find_chip_by_pins(pins: (list[str], tuple[str], str), ignore_claimed: bool = False):
    """Try to find a gpiochip device that includes all of the named pins.

    Does not care whether pins are in use or not.

    "pins" can be a single string, a list/tuple or a comma-separated string of names.

    """
    if isinstance(pins, str):
        if "," in pins:
            pins = [pin.strip() for pin in pins.split(",")]
        else:
            pins = (pins,)

    for path in glob.glob(CHIP_GLOB):
        if gpiod.is_gpiochip_device(path):
            try:
                chip = gpiod.Chip(path)
            except PermissionError:
                yield GPIOError(f"{path}: Permission error!")

            label = chip.get_info().label
            errors = False

            for id in pins:
                try:
                    offset = chip.line_offset_from_id(id)
                    yield GPIOFound(f"{id}: (line {offset}) found - {path} ({label})!")
                except OSError:
                    errors = True
                    yield GPIONotFound(f"{id}: not found - {path} ({label})!")
                    continue

                line_info = chip.get_line_info(offset)

                if not ignore_claimed and line_info.used:
                    errors = True
                    yield GPIOError(f"{id}: (line {offset}) currently claimed by {line_info.consumer}")

            if not errors:
                return chip

    if friendly_errors:
        raise ErrorDigest("suitable gpiochip not found!")

    return None
