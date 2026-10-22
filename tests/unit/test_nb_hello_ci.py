# Unit test ของ nb_hello_ci — import notebook-content.py แล้วเทสฟังก์ชัน greet() ตรงๆ
# (รูปแบบตาม tests/unit/_TEMPLATE_unit_test.py)

import importlib.util
import os

_NOTEBOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "fabric_items", "nb_hello_ci.Notebook", "notebook-content.py",
)

_spec = importlib.util.spec_from_file_location("nb_hello_ci", _NOTEBOOK_PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

greet = _module.greet


def test_greets_by_name():
    assert greet("CI/CD") == "Hello, CI/CD!"


def test_strips_whitespace():
    assert greet("  Fabric ") == "Hello, Fabric!"


def test_blank_or_none_falls_back_to_world():
    assert greet("") == "Hello, world!"
    assert greet("   ") == "Hello, world!"
    assert greet(None) == "Hello, world!"
