import pyfsdb


class DataLoader:
    def __init__(self):
        pass

    def debug(self, obj, savefile="/tmp/debug-lodaer.txt"):
        with open(savefile, "a") as d:
            d.write(str(obj) + "\n")

    @property
    def is_closed(self):
        return True

    def cleanup(self):
        pass
