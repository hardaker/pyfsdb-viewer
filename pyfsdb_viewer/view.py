"""reads and displays a fsdb table to the screen"""

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, FileType
from logging import debug, info, warning, error, critical
import logging
import sys

from textual.app import App, ComposeResult
from textual.widgets import Button, DataTable, Label
import pyfsdb


def parse_args():
    "Parse the command line arguments."
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter,
                            description=__doc__,
                            epilog="Exmaple Usage: pdbview FILE.fsdb")

    parser.add_argument("--log-level", "--ll", default="info",
                        help="Define the logging verbosity level (debug, info, warning, error, fotal, critical).")

    parser.add_argument("input_file", type=FileType('r'),
                        nargs='?', default=sys.stdin,
                        help="")

    args = parser.parse_args()
    log_level = args.log_level.upper()
    logging.basicConfig(level=log_level,
                        format="%(levelname)-10s:\t%(message)s")
    return args


class FsdbView(App):
    def __init__(self, input_file, *args, **kwargs):
        self.input_file = input_file
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        self.title = Label(self.input_file.name)
        yield self.title

        self.t = DataTable(fixed_rows=1, id="fsdbtable")
        yield self.t

        self.button = Button("Close", id="close")
        yield self.button

    def on_mount(self) -> None:
        self.fsh = pyfsdb.Fsdb(file_handle=self.input_file)
        self.t.add_columns(*self.fsh.column_names)
        self.t.add_rows(self.fsh.get_all())
        self.t.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.exit(event.button.id)


def main():
    args = parse_args()
    app = FsdbView(args.input_file, css_path="pyfsdb_viewer.css")
    app.run()


if __name__ == "__main__":
    main()
