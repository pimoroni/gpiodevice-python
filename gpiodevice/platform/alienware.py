def get_gpiochip_labels():
    try:
        model = open("/sys/devices/virtual/dmi/id/board_name", "r").read()
        if model.startswith("Alienware m15"):
            return ("INT3450:00",)
    except IOError as e:
        pass

    return None