from . import alienware, pi, radxa, jetson

PLATFORMS = (pi, alienware, radxa, jetson)


def get_gpiochip_labels():
    for platform in PLATFORMS:
        labels = platform.get_gpiochip_labels()
        if labels is not None:
            return labels
    raise RuntimeError("No compatible platform detected!")


def get_name():
    for platform in PLATFORMS:
        name = platform.get_name()
        if name is not None:
            return name
    raise RuntimeError("No compatible platform detected!")
