import pyfsdb
import shlex
import tempfile
import time
import os
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

        self.temp_file = tempfile.NamedTemporaryFile(
            delete=False, prefix="pdbview-stdout-"
        )
        self.temp_errors = tempfile.NamedTemporaryFile(
            delete=False, prefix="pdbview-stderr-"
        )

        self.debug(f"command: {self.command}")
        self.debug(f"stdout: {self.temp_file.name}")
        self.debug(f"stderr: {self.temp_errors.name}")

        self.run_pipe(command)

    def run_pipe(self, command):
        try:
            self.debug(f"commddd: {self.command}")
            p = Popen(
                self.command,
                stdout=self.temp_file,
                stdin=open(self.input_file_name, "r"),
                stderr=self.temp_errors,
                text=True,
                shell=False,
            )

            self.sub_process = p

            stats = os.stat(self.temp_file.name)
            while stats.st_size == 0:
                time.sleep(0.01)
                stats = os.stat(self.temp_file.name)

            self.debug(stats)

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

    @property
    def is_closed(self):
        self.poll_results = self.sub_process.poll()
        return self.poll_results is not None

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

    def cleanup(self):
        if self.sub_process and self.sub_process.poll() == None:
            self.sub_process.terminate()
        os.unlink(self.temp_file.name)
        os.unlink(self.temp_errors.name)
