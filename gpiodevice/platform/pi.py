def get_gpiochip_labels():
    try:
        model = open("/proc/device-tree/model", "r").read()
        if model.startswith("Raspberry Pi"):
            return (
                "pinctrl-rp1", # Pi 5 - Bookworm, /dev/gpiochip4 maybe
                "pinctrl-bcm2711" # Pi 4 - Bullseye, /dev/gpiochip0 maybe
            )
    except IOError as e:
        pass

    return None