import sys


def run_action(name: str):
    handler = getattr(sys.modules[__name__], name + "_data")
    return handler()


def export_data() -> str:
    return "Exported data successfully"


def import_data() -> str:
    return "Imported data successfully"
