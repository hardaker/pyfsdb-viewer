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
from textual.widgets import (
    Button,
    DataTable,
    Static,
    Header,
    Label,
    Footer,
    TextLog,
    Input,
    Checkbox,
)

from textual.containers import (
    Container,
    ScrollableContainer,
    Horizontal,
    Vertical,
    VerticalScroll,
)

from textual.binding import Binding

from pyfsdb_viewer.dataloader.fsdbloader import FsdbLoader
from pyfsdb_viewer.dataloader.processloader import ProcessLoader


def parse_args():
    "Parse the command line arguments."
    parser = ArgumentParser(
        formatter_class=ArgumentDefaultsHelpFormatter,
        description=__doc__,
        epilog="Exmaple Usage: pdbview FILE.fsdb",
    )

    parser.add_argument(
        "--log-level",
        "--ll",
        default="info",
        help="Define the logging verbosity level (debug, info, warning, error, fotal, critical).",
    )

    parser.add_argument(
        "-n",
        "--max-rows",
        default=1024,
        type=int,
        help="Maximum number of rows to load at start",
    )

    parser.add_argument("input_file", help="The file to view")

    args = parser.parse_args()
    log_level = args.log_level.upper()
    logging.basicConfig(level=log_level, format="%(levelname)-10s:\t%(message)s")
    return args


def convert_bindings(binding_list):
    "converts a set of tuples with extra information into a minimal binding set"
    out = []
    for binding in binding_list:
        if isinstance(binding, tuple):
            out.append((binding[0], binding[1], binding[2]))
        else:
            out.append(binding)


class FsdbView(App):
    "FSDB File Viewer"

    CSS_PATH = "pyfsdb_viewer.css"
    KEYS = [
        ("?", "help", "Help", "Display this help"),
        ("q", "cancel", "Close/Quit", "Close the current dialog or Quit pdbview"),
        (
            "a",
            "add_column",
            "Add column",
            "Add a new column to the table (uses dbcolcreate)",
        ),
        (
            "d",
            "remove_column",
            "Delete column",
            "Remove the current column from the table (uses dbcol)",
        ),
        (
            "c",
            "select_columns",
            "Select columns",
            "Select which columns to keep (uses dbcol)",
        ),
        (
            "h",
            "show_history",
            "command History",
            "Shows the command history that created the file",
        ),
        ("f", "filter", "Filter", "Filter the data (uses pdbrow)"),
        ("e", "eval", "Eval", "Evaluate every row (uses pdbroweval)"),
        ("|", "pipe", "add command", "Pass the data through any command"),
        (
            "l",
            "load_more_data",
            "Load more",
            "Load more data if the display is truncated",
        ),
        Binding("escape", "cancel", "Cancel", show="false"),
        Binding("z", "show_debug_log", "Debug", show="false"),
        ("s", "save", "Save", "Save the current dataset as a new file"),
        ("u", "undo", "Undo", "Undo the previous change (go backward in history)"),
    ]
    BINDINGS = [(x[0], x[1], x[2]) if isinstance(x, tuple) else x for x in KEYS]

    def __init__(self, input_file, *args, **kwargs):
        self.debug_log = []

        self.loader = FsdbLoader(open(input_file, "r"))
        self.input_files = [self.loader]
        self.added_comments = False
        self.current_screen = None
        self.empty_table = False
        self.row_count = 0

        self.max_rows = None
        if "max_rows" in kwargs:
            self.max_rows = kwargs["max_rows"]
            del kwargs["max_rows"]

        super().__init__(*args, **kwargs)

    def error(self, err_string, prompt="error: "):
        "displays an error message (will be a dialog box)"
        lab = Label(err_string)
        self.mount_and_focus(
            lab,
            prompt=prompt,
            buttons={"Close": self.action_cancel()},
        )

    def debug(self, obj, location="/tmp/debug.txt"):
        self.debug_log.append(str(obj))
        with open(location, "a") as d:
            d.write(str(obj) + "\n")

    def compose(self) -> ComposeResult:
        self.header = Header()

        self.debug(f"{self.loader}")
        self.ourtitle = Label(self.loader.name, id="ourtitle")

        self.data_table = DataTable(fixed_rows=1, id="fsdbtable")

        self.footer = Footer()

        self.container = Container(
            self.header, self.ourtitle, self.data_table, self.footer, id="mainpanel"
        )
        yield self.container

    def reload_data(self):
        self.clear(True)
        self.load_data()

    def load_data(self) -> None:
        "Creates a new FsdbLoader from the current input file and loads the view"
        self.loader.load_data()
        self.data_table.add_columns(*self.loader.column_names)
        self.rows = []
        self.action_load_more_data()
        self.ourtitle.update(self.loader.name)

    def on_mount(self) -> None:
        self.load_data()
        self.data_table.focus()

    def close_current_screen(self):
        self.buttons = None
        if self.current_screen:
            self.current_screen.remove()
            self.current_screen = None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if self.buttons:
            button_label = str(event.control.label)
            if button_label in self.buttons:
                self.debug(f"callback for {button_label}")
                if self.buttons[button_label]:
                    self.debug(f"no callback defined for for {button_label}")
                    self.buttons[button_label](event)
            else:
                self.debug(f"failed to find callback for {button_label}")
                self.close_current_screen()  # default is close

        else:
            self.error("no buttons/actions were defined")

    def action_exit(self):
        self.clean_and_exit()

    #
    # Actions from events
    #

    def clear(self, clear_columns=False):
        self.data_table.clear(columns=clear_columns)
        self.row_count = 0
        self.empty_table = True

    def action_load_more_data(self, clear_data=False) -> None:

        # note: the textual object count always returns 0, so we track rows ourselves
        if self.empty_table or clear_data:
            self.clear()

        added_rows = self.loader.load_more_data(self.rows, self.max_rows)
        self.debug(
            f"adding {len(added_rows)} rows (closed={self.loader.is_closed}, current={self.row_count}"
        )

        if len(added_rows) > 0:
            self.data_table.add_rows(added_rows)
            self.row_count += len(added_rows)
            self.empty_table = False

        elif self.row_count == 0 and not self.loader.is_closed:
            self.data_table.add_rows([["!! no data yet (use 'l' to load more) !!"]])
            self.empty_table = True

        elif self.row_count == 0:
            self.data_table.add_rows([["!! EMPTY FILE !!"]])
            self.empty_table = True

    def clean_and_exit(self):
        for loader in self.input_files:
            loader.cleanup()
        self.exit()

    def action_cancel(self, event=None):
        if self.current_screen:
            self.current_screen.remove()
            self.current_screen = None
        else:
            self.clean_and_exit()

    def action_undo(self, event=None):
        last_loader = self.input_files.pop()
        last_loader.cleanup()
        self.loader = self.input_files[-1]
        self.clear(True)
        self.reload_data()

    def action_help(self, event=None):
        tl = TextLog()
        tl.write("ESC:  exit a dialog box")
        for n, binding in enumerate(self.KEYS):
            if isinstance(binding, tuple):
                helptext = binding[2]
                if len(binding) > 3:
                    helptext = binding[3]
                tl.write(f"{binding[0] + ':':<4}  {helptext}")
        c = self.mount_and_focus(tl, "Help: (pres ESC to exit)")
        tl.styles.height = n + 1
        c.styles.height = n + 5

    def mount_and_focus(
        self,
        widget,
        prompt="argument: ",
        buttons={},
        ok_callback=None,
        class_name="entry_dialog",
        widget_height=0,
    ):
        "binds a standard input box and mounts after history"

        self.close_current_screen()  # close anything existing

        self.current_widget = widget
        self.label = Label(prompt, classes="entry_label")

        container = Vertical(self.label, widget, classes=class_name)

        # use default buttons if the ok_callback was created
        if len(buttons) == 0 and ok_callback:
            buttons = {"Ok": ok_callback, "Cancel": self.action_cancel}

        if len(buttons) > 0:
            button_horiz = Horizontal(classes="entry_button_row")
            for button in buttons:
                button_widget = Button(button, classes="entry_button")
                button_horiz.compose_add_child(button_widget)

            container.compose_add_child(button_horiz)

        # show the new widget after the history
        self.mount(container)

        # and focus the keyboard toward it
        widget.focus()
        self.current_screen = container
        self.buttons = buttons
        self.debug(f"buttons: {self.buttons}")
        return container

    def run_command_with_arguments(self, command_name, prompt):
        "runs a given command after prompting for an input value"

        saved_self = self

        def action_submit(self):
            "callback with the value stored in the saved Input"
            saved_self.debug(self)
            value = saved_self.prompter.value
            saved_self.debug(f"running: {command_name} / {value}")
            saved_self.run_pipe([command_name, value])
            saved_self.close_current_screen()

        def action_submit_noargs():
            action_submit(None)

        self.prompter = Input()
        self.prompter.action_submit = action_submit_noargs
        self.mount_and_focus(self.prompter, prompt=prompt, ok_callback=action_submit)

    def action_add_column(self):
        "add a new column to the data with pdbcolcreate"

        self.run_command_with_arguments("dbcolcreate", "Create a new column: ")

    def action_select_columns(self):
        "Allows a user to select a bunch of columns to display"
        columns = []
        for column in self.data_table.ordered_columns:
            cbox = Checkbox(
                str(column.label), disabled=False, value=True, classes="column-select"
            )
            columns.append(cbox)

        saved_self = self

        def action_submit(self):
            keep_columns = []
            for column in columns:
                if column.value:
                    keep_columns.append(str(column.label))
            saved_self.debug(f"keeping columns: {keep_columns}")

            saved_self.run_pipe(["dbcol"] + keep_columns)
            saved_self.close_current_screen()

        def action_disable(self):
            for column in columns:
                column.value = False

        def action_enable(self):
            for column in columns:
                column.value = True

        buttons = {
            "Ok": action_submit,
            "Check All": action_enable,
            "Uncheck All": action_disable,
            "Cancel": self.action_cancel,
        }

        v = Vertical(*columns)
        v.styles.height = len(columns) * 3
        c = self.mount_and_focus(
            v,
            "Select columns to display",
            buttons=buttons,
        )
        c.styles.height = len(columns) * 3 + 8
        columns[0].focus()

    def action_filter(self):
        "apply a row filter with pdbrow"

        self.run_command_with_arguments("pdbrow", "pdbrow filter: ")

    def action_eval(self):
        "Evaluate rows with a pdbroweval expression"

        self.run_command_with_arguments("pdbroweval", "pdbroweval expr: ")

    def save_current(self, button):
        path = str(self.save_info.value)
        os.rename(self.input_files[-1].name, path)
        self.loader = FsdbLoader(path)
        self.input_files[-1] = self.loader
        self.ourtitle.update(path)

    def action_save(self):
        "saves the current contents to a new file"

        if len(self.input_files) == 1:
            self.error("Cannot rename the unmodified original file")
            return

        self.save_info = Input()
        self.mount_and_focus(
            self.save_info, "Save data to file:", ok_callback=self.save_current
        )

    def action_remove_column(self):
        "drops the current column by calling dbcol"
        columns = self.data_table.ordered_columns
        new_columns = []
        for n, column in enumerate(columns):
            if self.data_table.cursor_column != n:
                new_columns.append(str(column.label))

        # TODO: allow passing of exact arguments in a list
        self.run_pipe(["dbcol"] + new_columns)

    def action_pipe(self):
        "prompt for a command to run"

        saved_self = self

        def run_entered_full_command(input_widget=None):
            self.run_pipe(saved_self.input_widget.value)
            saved_self.close_current_screen()

        self.input_widget = Input()
        self.input_widget.action_submit = run_entered_full_command

        self.mount_and_focus(
            self.input_widget,
            "Pipe date through a command: ",
            ok_callback=run_entered_full_command,
        )

    def run_pipe(self, command_parts="dbcolcreate foo"):
        "Runs a new command on the data, and re-displays the output file"

        self.loader = ProcessLoader(command_parts, self.loader.name)

        # save the new temporary file name
        self.input_files.append(self.loader)

        # load it all up
        self.reload_data()

    def action_show_debug_log(self):
        self.debug("showing debug log")
        self.debug_log_ui = TextLog(id="debug_log")
        for line in self.debug_log:
            self.debug_log_ui.write(line)
        self.mount_and_focus(
            self.debug_log_ui, class_name="text_dialog", buttons=["Close"]
        )

    def action_show_history(self, force=False):
        "show's the command history that created the file"

        self.debug("showing history")
        self.history_log = TextLog(id="history")

        if self.loader.commands is None:
            # this means pyfsdb couldn't get them
            self.history_log.write("[HISTORY UNAVAILABLE]")
        else:
            for command in self.loader.fsh.commands:
                self.history_log.write(command)

        self.mount_and_focus(
            self.history_log, class_name="text_dialog", buttons=["Close"]
        )


def main():
    args = parse_args()
    app = FsdbView(args.input_file, max_rows=args.max_rows)
    app.run()


if __name__ == "__main__":
    main()
