"""reads and displays a fsdb table to the screen"""

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, FileType
from logging import debug, info, warning, error, critical
import logging
import sys
import re
import subprocess
import tempfile
from subprocess import Popen, PIPE, STDOUT
import shlex

from textual.app import App, ComposeResult
from textual.widgets import Button, DataTable, Static, Header, Label, Footer, TextLog, Input
from textual.containers import Container, ScrollableContainer
import pyfsdb


def parse_args():
    "Parse the command line arguments."
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter,
                            description=__doc__,
                            epilog="Exmaple Usage: pdbview FILE.fsdb")

    parser.add_argument("--log-level", "--ll", default="info",
                        help="Define the logging verbosity level (debug, info, warning, error, fotal, critical).")

    parser.add_argument("input_file", help="The file to view")

    args = parser.parse_args()
    log_level = args.log_level.upper()
    logging.basicConfig(level=log_level,
                        format="%(levelname)-10s:\t%(message)s")
    return args

class FsdbView(App):
    "FSDB File Viewer"

    CSS_PATH="pyfsdb_viewer.css"
    BINDINGS=[("q", "exit", "Quit"),
              ("r", "remove_row", "Remove row"),
              ("h", "show_history", "command History"),
              ("p", "pipe", "add command")]

    def __init__(self, input_file, *args, **kwargs):
        self.input_file = open(input_file, "r")
        self.added_comments = False
        super().__init__(*args, **kwargs)

    def debug(self, obj):
        with open("/tmp/debug.txt", "w") as d:
            d.write(str(obj) + "\n")

    def compose(self) -> ComposeResult:
        self.header = Header()
        
        self.ourtitle = Label(self.input_file.name, id="ourtitle")

        self.data_table = DataTable(fixed_rows=1, id="fsdbtable")

        self.footer = Footer()

        self.container = Container(self.header, self.ourtitle,
                                   self.data_table, self.footer, id="mainpanel")
        yield self.container

    def load_data(self) -> None:
        self.fsh = pyfsdb.Fsdb(file_handle=self.input_file)
        self.data_table.add_columns(*self.fsh.column_names)
        self.rows = self.fsh.get_all()
        self.data_table.add_rows(self.rows)

    def on_mount(self) -> None:
        self.load_data()
        self.data_table.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.exit(event.button.id)

    def action_exit(self):
        self.exit()

    def action_remove_row(self):
        row_id, _ = self.data_table.coordinate_to_cell_key(self.data_table.cursor_coordinate)

        self.data_table.remove_row(row_id)

    def action_pipe(self):
        "prompt for a command to run"

        class CommandInput(Input):
            def __init__(self, base_parent, *args, **kwargs):
                self.base_parent = base_parent
                super().__init__(*args, **kwargs)

            def action_submit(self):
                command = self.value
                self.base_parent.run_pipe(self.value)
                self.remove()

        self.command_input = CommandInput(self, id="command_input")

        # show the existing history and mount it afterward
        if not self.added_comments:
            self.action_show_history()
        self.mount(self.command_input, after = self.history_log)

        # focus it
        self.command_input.focus()


    def run_pipe(self, command="dbcolcreate foo"):
        "Runs a new command on the data, and re-displays the output file"
        
        command_parts = shlex.split(command)
        p = Popen(command_parts, stdout=PIPE, stdin=PIPE, stderr=PIPE)
        
        # run the specified command
        input_file = open(self.input_file.name, "r").read().encode()
        output_data = p.communicate(input=input_file)
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            self.debug(tmp.name)
            tmp.write(output_data[0])
            self.input_file = open(tmp.name, "r")
        self.data_table.clear(columns=True)
        self.load_data()
        self.action_show_history(force=True)

    def action_show_history(self, force=False):
        "show's the comment history"
        if self.added_comments:
            self.history_log.remove()
            self.added_comments = False
            if not force:
                return
        
        self.added_comments = True

        self.history_log = TextLog(id="history")
        self.mount(self.history_log, after = self.data_table)

        is_command = re.compile("# +\|")
        count = 0
        for comment in self.fsh.comments:
            if is_command.match(comment):
                count += 1
                self.history_log.write(comment.strip())

        # needs + 1 (maybe because of footer?)
        self.history_log.styles.height = count + 1


def main():
    args = parse_args()
    app = FsdbView(args.input_file)
    app.run()


if __name__ == "__main__":
    main()
