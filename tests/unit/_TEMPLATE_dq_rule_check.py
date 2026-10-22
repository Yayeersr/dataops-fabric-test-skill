# TEMPLATE — เทมเพลตเฉพาะสำหรับเทส "DQ rule function" ของ Notebook ด้วย mock data (ต่างจาก
# tests/unit/test_<name>.py ทั่วไปที่เทส transform logic เฉยๆ — ดู docs/check-patterns-guide.md
# ส่วนที่ 3) ตั้งใจตั้งชื่อไฟล์นี้ลงท้ายด้วย _check.py ไม่ใช่ _test.py เพราะ repo นี้ไม่มี
# pytest.ini/pyproject.toml กำหนด python_files เอง pytest จะใช้ default pattern
# (test_*.py / *_test.py) สแกนหา — ถ้าตั้งชื่อ _test.py ไฟล์ TEMPLATE ที่มีแต่ placeholder
# นี้จะถูกเก็บไปรันจริงใน CI แล้ว fail ทันที
#
# ขั้นตอนใช้งาน:
#   1. copy ไฟล์นี้ไปตั้งชื่อ tests/unit/test_<item_name>.py (ต้องลงท้าย _test.py หรือขึ้นต้น
#      test_ ถึงจะถูก pytest เก็บไปรันจริง — ตรงข้ามกับไฟล์ TEMPLATE นี้)
#   2. เขียนฟังก์ชันกฎ (ส่วน "notebook-side" ด้านล่าง) ไว้ในตัว Notebook item จริงที่สร้างผ่าน
#      Fabric UI แล้ว (ห้าม hand-write ไฟล์ item เอง — ดูกฎ UI-first)
#   3. แก้ส่วน "test-side" ด้านล่างให้ import จาก path ของ item จริง แล้วเขียนเคส PASS/FAIL
#      ของตัวเองแทน placeholder
#
# ตัวอย่างจริงที่ใช้ pattern นี้อยู่แล้ว (เทมเพลตนี้ก็อปโครงมาจากคู่นี้ตรงๆ):
#   fabric_items/fern/nb_fern_dq_check.Notebook/notebook-content.py (ฟังก์ชัน check_qty_on_hand_not_null)
#   tests/unit/test_nb_fern_dq_check.py


# ── ส่วน "notebook-side" — เขียนใน <item_name>.Notebook/notebook-content.py จริง (ไม่ใช่ไฟล์นี้) ──
#
# import great_expectations as gx
#
# _ge_context = gx.get_context(mode="ephemeral")
# _ge_batch_definition = (
#     _ge_context.data_sources.add_pandas("pandas")
#     .add_dataframe_asset(name="<ชื่อ asset>")
#     .add_batch_definition_whole_dataframe("batch")
# )
#
#
# def check_<ชื่อกฎ>(pdf):
#     # 1 ฟังก์ชัน = 1 กฎ — ง่ายต่อการเทส ไม่ต้องพึ่ง spark/notebookutils เลย
#     batch = _ge_batch_definition.get_batch(batch_parameters={"dataframe": pdf})
#     expectation = gx.expectations.<ExpectationClass>(column="<ชื่อ column>")
#     return batch.validate(expectation).success
#
#
# if __name__ == "__main__":
#     # ส่วนที่พึ่ง spark จริง แยกไว้นอกฟังก์ชัน + ใต้ guard นี้เสมอ — ตอน pytest import
#     # ไฟล์นี้ (exec_module ทั้งไฟล์) __name__ จะไม่ใช่ "__main__" เลยข้ามส่วนนี้ไปไม่ error
#     df = spark.table("<ชื่อตาราง>").toPandas()
#     assert check_<ชื่อกฎ>(df), "Data quality check failed: <อธิบายกฎสั้นๆ>"


# ── ส่วน "test-side" — ไฟล์นี้เองหลัง copy+rename แล้ว ────────────────────────────────
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

check_<ชื่อกฎ> = _module.check_<ชื่อกฎ>


def test_passes_with_good_data():
    df = pd.DataFrame({"<ชื่อ column>": [<ค่าที่ผ่านกฎ>]})
    assert check_<ชื่อกฎ>(df) is True


def test_fails_with_bad_data():
    df = pd.DataFrame({"<ชื่อ column>": [<ค่าที่ผิดกฎ>]})
    assert check_<ชื่อกฎ>(df) is False
