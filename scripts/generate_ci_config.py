"""
Bulk-generate/update ci-config.yml จาก fabric_items/ จริงในเครื่อง — ใช้ตอน onboard
item จำนวนมาก (หลักร้อย) เข้า pattern-based CI ครั้งแรก โดยไม่ให้ CI พังทันทีทั้งหมด

หลักการ (evidence-based, ไม่เดา):
  1. หา fabric_type จาก suffix ของ folder (.Notebook / .DataPipeline / .Lakehouse / ...)
  2. เช็คว่ามีไฟล์ evidence รองรับ pattern ไหนอยู่แล้วจริง:
       - tests/unit/test_<name>.py               -> unit_test
       - tests/data_quality/checkpoints/dq_<name>.yml -> data_quality
       - shared script (structure/schema) + _defaults ระบุ pattern นั้นให้ type นี้ -> ใช้ pattern นั้นได้เลย
         (structure/schema ไม่ต้องมีไฟล์ต่อ item เพราะใช้ script กลาง)
  3. ถ้าไม่มี evidence รองรับเลย (pattern ที่ต้องมีไฟล์เฉพาะ แต่ยังไม่มีใครเขียน)
       -> ใส่ skip_check: true + skip_reason อัตโนมัติ ("bulk onboarding ...")
       เพื่อให้ CI ไม่พังทันทีตอน onboard วันแรก แต่ยังเห็นชัดว่าเป็นหนี้ทางเทคนิคที่ต้องเคลียร์
  4. ไม่แตะ entry ที่มีอยู่แล้วใน ci-config.yml เดิม (merge, ไม่ overwrite)
  5. ไม่แตะ _defaults block เดิม

ใช้:
    python scripts/generate_ci_config.py            # เขียนทับ ci-config.yml จริง
    python scripts/generate_ci_config.py --dry-run  # print ผลลัพธ์ดูก่อน ไม่เขียนไฟล์
"""

import argparse
import io
import os
import sys
from datetime import date

import yaml

# กัน console บน Windows แสดงภาษาไทยเพี้ยน (cp874 default) — ไม่กระทบตอนรันบน Linux/GitHub Actions
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.join(BASE_DIR, "..")
FABRIC_ITEMS_DIR = os.path.join(REPO_ROOT, "fabric_items")
CI_CONFIG_PATH = os.path.join(REPO_ROOT, "ci-config.yml")
TESTS_UNIT_DIR = os.path.join(REPO_ROOT, "tests", "unit")
GE_CHECKPOINTS_DIR = os.path.join(REPO_ROOT, "tests", "data_quality", "checkpoints")

# pattern ที่ "ต้องมีไฟล์เฉพาะต่อ item" ถึงจะใช้ default ของ type นั้นได้เลย
# structure/schema ไม่อยู่ในนี้เพราะใช้ script กลาง ไม่ต้องมีไฟล์ต่อ item
PATTERNS_NEEDING_EVIDENCE = {"unit_test", "data_quality"}


def load_yaml(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def list_fabric_items():
    # recursive ผ่าน os.walk + marker ".platform" (ไฟล์ที่ Fabric สร้างให้ทุก item จริง) แทนการ
    # os.listdir ระดับเดียว — เพราะ item อาจอยู่ใต้ Fabric workspace folder ได้ (เช่น fabric_items/yayee/...)
    # ไม่ descend ต่อเข้าไปในโฟลเดอร์ item เอง (Tables/, Files/ ฯลฯ) เพราะข้างในไม่มี item ซ้อนอีก
    items = []
    for dirpath, dirnames, filenames in os.walk(FABRIC_ITEMS_DIR):
        if ".platform" not in filenames:
            continue
        entry = os.path.basename(dirpath)
        if "." in entry:
            name, fabric_type = entry.rsplit(".", 1)
            items.append((name, fabric_type))
        dirnames[:] = []  # หยุดไต่ลึกต่อจาก item folder นี้
    items.sort()
    return items


def has_unit_test(name):
    return os.path.exists(os.path.join(TESTS_UNIT_DIR, f"test_{name}.py"))


def has_dq_checkpoint(name):
    return os.path.exists(os.path.join(GE_CHECKPOINTS_DIR, f"dq_{name}.yml"))


def decide_entry(name, fabric_type, defaults, existing_entry, today_str):
    """
    คืนค่า (entry_dict_or_None, resolved_check, source)
    - entry_dict_or_None: None แปลว่าไม่ต้องเขียน entry ใหม่ (ใช้ default ได้เลย หรือมี entry เดิมอยู่แล้ว)
    - resolved_check: check pattern ที่ item นี้จะได้ใช้จริง (โชว์ให้เห็นเสมอ ไม่ว่าจะมาจากไหน)
    - source: อธิบายว่า pattern นี้มาจากไหน (สำหรับ print ตาราง ให้เห็นครบทุกตัว ไม่ใช่แค่ตัวที่เพิ่งเพิ่ม)
    """

    if existing_entry is not None:
        existing_check = existing_entry.get("check") if isinstance(existing_entry, dict) else None
        if existing_entry.get("skip_check"):
            resolved = existing_check or defaults.get(fabric_type, "unit_test")
            return None, resolved, "existing entry (skip_check — already marked, not touched)"
        resolved = existing_check or defaults.get(fabric_type, "unit_test")
        return None, resolved, "existing entry in ci-config.yml (explicit override, not touched)"

    default_check = defaults.get(fabric_type)

    if default_check is None:
        # ไม่มี default ให้ type นี้เลย -> fallback ปกติคือ unit_test (fail-safe เข้มสุด)
        return None, "unit_test", f"no _defaults entry for type '{fabric_type}' — fell back to unit_test"

    if default_check not in PATTERNS_NEEDING_EVIDENCE:
        # structure / schema / none -> ใช้ script กลาง ไม่ต้องมีไฟล์ต่อ item เลย
        return None, default_check, f"_defaults.{fabric_type} = {default_check} (shared script, no file needed)"

    if default_check == "unit_test" and has_unit_test(name):
        return None, "unit_test", f"_defaults.{fabric_type} = unit_test (test file exists)"

    if default_check == "data_quality" and has_dq_checkpoint(name):
        return None, "data_quality", f"_defaults.{fabric_type} = data_quality (checkpoint exists)"

    # ไม่มี evidence รองรับ default ที่ต้องมีไฟล์เฉพาะ -> skip ไว้ก่อน ไม่ให้ CI พังทันที
    entry = {
        "skip_check": True,
        "skip_reason": (
            f"Bulk onboarding {today_str} — ยังไม่มี "
            f"{'unit test' if default_check == 'unit_test' else 'data quality checkpoint'} "
            f"ให้ item นี้ ต้องเขียนเพิ่มแล้วเอา skip_check ออก"
        ),
    }
    return entry, default_check, f"NEW skip_check — no {default_check} evidence found yet (ต้องเขียนเพิ่ม)"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="แสดงผลลัพธ์ ไม่เขียนไฟล์จริง")
    args = parser.parse_args()

    config = load_yaml(CI_CONFIG_PATH)
    defaults = config.get("_defaults", {})
    today_str = date.today().isoformat()

    items = list_fabric_items()
    added = []
    table_rows = []  # (name, fabric_type, resolved_check, source) — ทุก item ไม่ว่าจะเปลี่ยนหรือไม่

    for name, fabric_type in items:
        existing_entry = config.get(name)
        entry, resolved_check, source = decide_entry(name, fabric_type, defaults, existing_entry, today_str)

        if entry is not None:
            config[name] = entry
            added.append((name, fabric_type, resolved_check, source))

        table_rows.append((name, fabric_type, resolved_check, source))

    # ตารางเต็ม — เห็นทุก item ว่าได้ pattern อะไร มาจากไหน ไม่ใช่แค่ตัวที่เพิ่งเพิ่ม
    name_w = max(len(r[0]) for r in table_rows) + 2
    type_w = max(len(r[1]) for r in table_rows) + 2
    check_w = max(len(r[2]) for r in table_rows) + 2

    print("=== ตารางเต็ม: ทุก item ได้ check pattern อะไร มาจากไหน ===")
    print(f"{'ITEM'.ljust(name_w)}{'TYPE'.ljust(type_w)}{'CHECK'.ljust(check_w)}SOURCE")
    for name, fabric_type, resolved_check, source in table_rows:
        print(f"{name.ljust(name_w)}{fabric_type.ljust(type_w)}{resolved_check.ljust(check_w)}{source}")
    print()

    print(f"พบ item ทั้งหมด: {len(items)}  |  เพิ่ม entry ใหม่: {len(added)}")
    print()

    if added:
        print("⚠️  ตัวที่เพิ่ง auto-skip (ต้องตามไปเขียน test จริงแล้วเอา skip_check ออกทีหลัง):")
        for name, fabric_type, resolved_check, source in added:
            print(f"  [{fabric_type}] {name} -> {resolved_check}")
        print()

    if not added:
        print("ไม่มี entry ใหม่ต้องเพิ่ม — ไม่แตะไฟล์เลย (กัน comment ในไฟล์เดิมหาย)")
        return

    new_entries = {name: config[name] for name, _fabric_type, _resolved_check, _source in added}
    appended_yaml = yaml.dump(new_entries, allow_unicode=True, sort_keys=False, default_flow_style=False)

    if args.dry_run:
        print("--dry-run: ไม่เขียนไฟล์จริง — นี่คือส่วนที่จะต่อท้ายไฟล์เดิม:")
        print()
        print(appended_yaml)
        return

    # ต่อท้ายไฟล์เดิมเป็น text แทนการ yaml.dump ทั้งไฟล์ใหม่ — กัน comment ในไฟล์เดิมหายไปหมด
    # (yaml.dump ไม่ preserve comment เลย ถ้า load ทั้งไฟล์มาแล้ว dump ทับ)
    with open(CI_CONFIG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n# --- เพิ่มโดย generate_ci_config.py ({today_str}) ---\n")
        f.write(appended_yaml)

    print(f"ต่อท้าย {CI_CONFIG_PATH} เรียบร้อย ({len(added)} entries ใหม่)")


if __name__ == "__main__":
    sys.exit(main())
