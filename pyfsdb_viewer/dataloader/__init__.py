import pyfsdb


class DataLoader():
    def __init__(self):
        pass

    def debug(self, obj, savefile="/tmp/debug-lodaer.txt"):
        with open(savefile, "w") as d:
            d.write(str(obj) + "\n")
