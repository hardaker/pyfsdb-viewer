import pyfsdb_viewer.dataloader.processloader as procload
from logging import error


def test_process_loader_full_file():
    pl = procload.ProcessLoader("pdbrow 'a > 3'", "pyfsdb_viewer/tests/oneline.fsdb")
    pl.load_data()
    assert pl.column_names == ["a", "b", "c"]
    assert True


def test_process_loader_empty_file():
    pl = procload.ProcessLoader("pdbrow 'a > 3'", "pyfsdb_viewer/tests/empty.fsdb")
    pl.load_data()
    assert pl.column_names == ["a", "b", "c"]
    assert True
