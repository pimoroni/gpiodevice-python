def get_name():
    try:
        model = open("/proc/device-tree/model", "r").read()
        if model.startswith("NVIDIA Jetson"):
            return model
    except IOError:
        pass

    return None

def get_gpiochip_labels():
    if get_name() is not None:
        return (
            "tegra234-gpio-aon",
            "tegra234-gpio",
        )

    return None
