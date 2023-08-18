import pyfsdb

class DataLoaderBase():
    def __init__(self):
        pass

class FsdbLoader():
    def __init__(self, input_file):
        super().__init__()

        self.input_file = input_file
        self.rows = []
        self.fsh = None

    @property
    def name(self):
        return self.fsh.file_handle.name

    @property
    def commands(self):
        try:
            return self.fsh.parse_commands()
        except Exception:
            return None

    def load_data(self) -> None:
        self.fsh = pyfsdb.Fsdb(file_handle=self.input_file)
        self.rows = []

    def load_more_data(self, current_rows, max_rows=128) -> None:
        more_rows = []
        for n, row in enumerate(self.fsh):
            more_rows.append(row)
            if max_rows and n == max_rows:
                break
        current_rows.extend(more_rows)
        return more_rows

    def column_names(self):
        return self.fsh.column_names

