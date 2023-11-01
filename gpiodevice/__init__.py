import glob

import gpiod

from . import errors, platform

__version__ = "0.0.1"


CHIP_GLOB = "/dev/gpiochip*"


friendly_errors: bool = False


@errors.collect
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
                yield errors.GPIOError(f"{label}: (line {pin}) not found!")
                continue

        line_info = chip.get_line_info(pin)

        if line_info.used:
            used += 1
            yield errors.GPIOError(f"{label}: (line {pin}, {line_info.label}) currently claimed by {line_info.consumer}")

    if used and friendly_errors:
        raise errors.ErrorDigest("some pins we need are in use!")

    return used == 0


@errors.collect
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
                yield errors.GPIOError(f"{path}: Permission error!")
                continue

            if label in labels:
                chip = gpiod.Chip(path)
                if check_pins_available(chip, pins):
                    return chip
            else:
                yield errors.GPIONotFound(f"{path}: this is not the GPIO we're looking for! ({label})")

    if friendly_errors:
        raise errors.ErrorDigest("suitable gpiochip device not found!")

    return None


@errors.collect
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
                yield errors.GPIOError(f"{path}: Permission error!")

            label = chip.get_info().label
            errors = False

            for id in pins:
                try:
                    offset = chip.line_offset_from_id(id)
                    yield errors.GPIOFound(f"{id}: (line {offset}) found - {path} ({label})!")
                except OSError:
                    errors = True
                    yield errors.GPIONotFound(f"{id}: not found - {path} ({label})!")
                    continue

                line_info = chip.get_line_info(offset)

                if not ignore_claimed and line_info.used:
                    errors = True
                    yield errors.GPIOError(f"{id}: (line {offset}, {line_info.label}) currently claimed by {line_info.consumer}")

            if not errors:
                return chip

    if friendly_errors:
        raise errors.ErrorDigest("suitable gpiochip not found!")

    return None


def find_chip_by_platform():
    labels = platform.get_gpiochip_labels()
    return find_chip_by_label(labels)
