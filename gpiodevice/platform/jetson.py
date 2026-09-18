def get_name():
    try:
        with open("/proc/device-tree/model") as f:
            model = f.read()
        if model.startswith("NVIDIA Jetson"):
            return model
    except OSError:
        pass

    return None

def get_gpiochip_labels():
    if get_name() is not None:
        return (
            "tegra234-gpio-aon",
            "tegra234-gpio",
        )

    return None
