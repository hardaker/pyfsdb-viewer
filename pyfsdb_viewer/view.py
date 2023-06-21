"""reads and displays a fsdb table to the screen"""

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, FileType
from logging import debug, info, warning, error, critical
import os
import logging
import sys
import re
import subprocess
import tempfile
from subprocess import Popen, PIPE, STDOUT
import shlex

from textual.app import App, ComposeResult
from textual.widgets import Button, DataTable, Static, Header, Label, Footer, TextLog, Input
from textual.containers import Container, ScrollableContainer, Horizontal
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
              ("h", "show_history", "command History"),
              ("a", "add_column", "Add column"),
              ("d", "remove_column", "Delete column"),
              ("f", "filter", "Filter"),
              ("e", "eval", "Eval"),
              ("p", "pipe", "add command"),
              ("s", "save", "Save"),
              ("u", "undo", "Undo")]

    def __init__(self, input_file, *args, **kwargs):
        self.input_file = open(input_file, "r")
        self.input_files = [input_file]
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

    def reload_data(self):
        self.data_table.clear(columns=True)
        self.load_data()

    def load_data(self) -> None:
        self.fsh = pyfsdb.Fsdb(file_handle=self.input_file)
        self.data_table.add_columns(*self.fsh.column_names)
        self.rows = self.fsh.get_all()
        self.data_table.add_rows(self.rows)
        self.ourtitle.update(self.input_file.name)

    def on_mount(self) -> None:
        self.load_data()
        self.data_table.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.exit(event.button.id)

    def action_exit(self):
        self.exit()

    def action_undo(self):
        self.debug(self.input_files)
        self.input_files.pop()
        self.debug(self.input_files[-1])
        self.input_file = open(self.input_files[-1], "r")
        self.data_table.clear(columns=True)
        self.reload_data()

    def action_remove_row(self):
        row_id, _ = self.data_table.coordinate_to_cell_key(self.data_table.cursor_coordinate)

        self.data_table.remove_row(row_id)

    def mount_cmd_input_and_focus(self, widget, prompt="argument: ", show_history=True):
        "binds a standard input box and mounts after history"

        self.label = Label(prompt, classes="entry_label")

        # show the history to date if appropriate
        if show_history and not self.added_comments:
            self.action_show_history()

        container = Horizontal(self.label, widget, classes="entry_dialog")

        # show the new widget after the history
        self.mount(container, after = self.history_log)

        # and focus the keyboard toward it
        widget.focus()
        return container

    def action_add_column(self):
        "add a new column to the data"
        class ColumnInput(Input):
            def __init__(self, base_parent, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.base_parent = base_parent
                self.removeme = self

            def action_submit(self):
                command = self.value
                self.base_parent.run_pipe(["dbcolcreate", self.value])
                self.removeme.remove()


        self.column_input = ColumnInput(self)
        self.column_input.removeme = self.mount_cmd_input_and_focus(self.column_input, "column name:")

    def action_save(self):
        "saves the current contents to a new file"
        class ActionSave(Input):
            def __init__(self, base_parent, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.base_parent = base_parent
                self.removeme = self

            def action_submit(self):
                path = self.value
                current = self.base_parent.input_file
                os.rename(self.base_parent.input_files[-1], str(path))
                self.base_parent.input_file = path
                self.base_parent.input_files[-1] = path
                self.removeme.remove()

        self.save_info = ActionSave(self)
        # TODO: , show_history=False
        self.save_info.removeme = self.mount_cmd_input_and_focus(self.save_info, "file name:")

    def action_remove_column(self):
        "drops the current column by calling dbcol"
        columns = self.data_table.ordered_columns
        new_columns = []
        for n, column in enumerate(columns):
            if self.data_table.cursor_column != n:
                new_columns.append(str(column.label))

        # TODO: allow passing of exact arguments in a list
        self.run_pipe(['dbcol'] + new_columns)
        self.debug(new_columns)

    def action_filter(self):
        "apply a row filter with pdbrow"

        class FilterInput(Input):
            def __init__(self, base_parent, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.base_parent = base_parent
                self.removeme = self

            def action_submit(self):
                command = self.value
                self.base_parent.run_pipe(["pdbrow", self.value])
                self.removeme.remove()

        self.filter_input = FilterInput(self)
        self.filter_input.removeme = self.mount_cmd_input_and_focus(self.filter_input, "pdbrow filter: ")

    def action_eval(self):
        "Evaluate rows with a pdbroweval expression"

        class FilterInput(Input):
            def __init__(self, base_parent, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.base_parent = base_parent
                self.removeme = self

            def action_submit(self):
                command = self.value
                self.base_parent.run_pipe(["pdbroweval", self.value])
                self.removeme.remove()

        self.eval_input = FilterInput(self)
        self.eval_input.removeme = self.mount_cmd_input_and_focus(self.eval_input, "pdbroweval expr: ")
        

    def action_pipe(self):
        "prompt for a command to run"

        class CommandInput(Input):
            def __init__(self, base_parent, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.base_parent = base_parent
                self.removeme = self

            def action_submit(self):
                command = self.value
                self.base_parent.run_pipe(self.value)
                self.removeme.remove()

        self.command_input = CommandInput(self)
        self.command_input.removeme = self.mount_cmd_input_and_focus(self.command_input, "command: ")

    def run_pipe(self, command_parts="dbcolcreate foo"):
        "Runs a new command on the data, and re-displays the output file"
        
        if not isinstance(command_parts, list):
            command_parts = shlex.split(command)
        p = Popen(command_parts, stdout=PIPE, stdin=PIPE, stderr=PIPE)
        
        # run the specified command
        input_file = open(self.input_file.name, "r").read().encode()
        output_data = p.communicate(input=input_file)
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            self.debug(tmp.name)
            tmp.write(output_data[0])
            self.input_files.append(tmp.name)
            self.input_file = open(tmp.name, "r")
        self.reload_data()
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
