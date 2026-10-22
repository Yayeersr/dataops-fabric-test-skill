# TEMPLATE — เทมเพลตทั่วไปสำหรับเทส transform logic ของ Notebook (ต่างจาก
# _TEMPLATE_dq_rule_check.py ที่เฉพาะเจาะจงกับ "DQ rule function" — ดู
# docs/check-patterns-guide.md ส่วนที่ 3)
#
# ขั้นตอนใช้งาน:
#   1. copy ไฟล์นี้ไปตั้งชื่อ tests/unit/test_<item_name>.py (ต้องตรงชื่อ Notebook item เป๊ะ
#      ไม่งั้น CI หาไม่เจอ error ทันที)
#   2. เขียนโค้ดใน Notebook เป็น "ฟังก์ชัน" (ไม่ใช่ script รันทื่อๆ ทั้งไฟล์) แล้วแก้
#      _NOTEBOOK_PATH / my_check_function ด้านล่างให้ตรงกับไฟล์/ฟังก์ชันจริง
#   3. เขียน test case ให้ครอบคลุมทั้งเคสผ่านและเคส fail อย่างน้อยอย่างละ 1 เคส
#
# วิธีนี้ทดสอบ "logic" ได้จริง (เช่น "ถ้า input แบบนี้ output ต้องเป็นแบบนี้") แต่ทดสอบ
# "ข้อมูลจริง" ไม่ได้ — นั่นคือหน้าที่ของ Live DQ Gate แทน (ดู check-patterns-guide.md ส่วนที่ 1)

import importlib.util
import os

import pandas as pd

_NOTEBOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "fabric_items", "<item_name>.Notebook", "notebook-content.py",
)

_spec = importlib.util.spec_from_file_location("<item_name>", _NOTEBOOK_PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

# ดึงฟังก์ชันที่ Notebook ประกาศไว้มาทดสอบตรงๆ — ต้อง refactor โค้ด Notebook ให้เป็นฟังก์ชันก่อน
# ถ้ายังเป็น script เปลือยๆ ทั้งไฟล์อยู่ (import แบบนี้จะรันทั้งไฟล์ทันทีตอน exec_module() ซึ่งอาจ
# error ถ้ามีโค้ดที่พึ่ง spark/notebookutils อยู่นอกฟังก์ชัน)
my_check_function = _module.my_check_function


def test_passes_with_good_input():
    df = pd.DataFrame({"column_name": [10, 5, 0]})
    assert my_check_function(df) is True


def test_fails_with_bad_input():
    df = pd.DataFrame({"column_name": [10, None, 0]})
    assert my_check_function(df) is False
