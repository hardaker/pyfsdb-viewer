import pyfsdb
import shlex
import tempfile
import time
from queue import SimpleQueue as FifoQueue
from concurrent.futures import ThreadPoolExecutor
from subprocess import Popen, PIPE, STDOUT
from logging import error

from . import DataLoader


class ProcessLoader(DataLoader):
    "Executes a process with a pipe to a new file and loads it at least in part"

    def __init__(self, command, input_file_name):
        super().__init__()

        # save the command
        if not isinstance(command, list):
            command = shlex.split(command)
        self.command = command

        self.executor = None
        self.queue = None
        self.input_file_name = input_file_name
        self.fsh = None

        self.temp_file = tempfile.NamedTemporaryFile(delete=False)

        self.run_pipe(command)

    def run_pipe(self, command):
        try:
            p = Popen(
                self.command,
                stdout=PIPE,
                stdin=open(self.input_file_name, "rb"),
                stderr=PIPE,
            )

            # this reads all data -- we need a better solution than this
            # need to do parallel reading and writing of data
            output_data = p.communicate()

            self.debug(output_data, savefile="/tmp/debug-test.txt")
            self.temp_file.write(output_data[0])  # save stdout to the file
            self.temp_file.close()

        except Exception as e:
            self.debug(f"failed with {e}")
            error(f"failed with {e}")

    @property
    def name(self):
        return self.temp_file.name

    @property
    def temp_file_handle(self):
        return open(self.name, "r")

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
        self.fsh = pyfsdb.Fsdb(file_handle=self.temp_file_handle)
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
        if not self.filename and not self.file_handle:
            raise ValueError("No filename or handle currently available for reading")
        # XXX: throw error on -1 parse
        return self

    def __next__(self):
        return next(self.fsh)
