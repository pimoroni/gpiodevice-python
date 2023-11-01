from . import alienware, pi


def get_gpiochip_labels():
    for platform in (pi,alienware):
        labels = platform.get_gpiochip_labels()
        if labels is not None:
            return labels
    raise RuntimeError("No compatible platform detected!")