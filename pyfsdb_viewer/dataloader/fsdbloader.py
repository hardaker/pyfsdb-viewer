import pyfsdb

from . import DataLoader


class FsdbLoader(DataLoader):
    "loads data from an existing FSDB file"

    def __init__(self, input_file):
        super().__init__()

        self.input_file = input_file
        self.rows = []
        self.fsh = pyfsdb.Fsdb(file_handle=self.input_file)

    @property
    def name(self):
        return self.fsh.file_handle.name

    @property
    def commands(self):
        try:
            return self.fsh.parse_commands()
        except Exception:
            return None

    @property
    def column_names(self):
        return self.fsh.column_names

    def load_data(self) -> None:
        self.rows = []

    def load_more_data(self, current_rows, max_rows=128) -> None:
        more_rows = []
        for n, row in enumerate(self.fsh):
            more_rows.append(row)
            if max_rows and n == max_rows:
                break
        current_rows.extend(more_rows)
        return more_rows

    def __iter__(self):
        """Returns an iterator object for looping over from the current file."""
        return self

    def __next__(self):
        return next(self.input_file)
