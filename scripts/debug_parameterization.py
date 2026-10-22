"""
Validate โครงสร้างของ fabric_items/parameter.yml แบบ local ก่อน commit/push จริง
ไม่ต้องมี Azure credential — รันได้บนเครื่อง dev ทันที

ทำไมใช้ private module (fabric_cicd._parameter._parameter.Parameter):
    Public API (FabricWorkspace) เรียก credential.get_token() ตั้งแต่ตอน construct object
    (เพื่อ query deployed items จาก live workspace) ก่อนจะไปถึงขั้นตอน validate parameter.yml
    เลยไม่มีทาง validate แบบ offline ผ่าน public API ได้เลย ต้องใช้ private module ตัวนี้แทน

ข้อจำกัด:
    - Validate ได้แค่ "โครงสร้าง" (type ถูกไหม, key ครบไหม, "_ALL_" ใช้ถูกไหม)
    - Validate ไม่ได้ว่า $items.Lakehouse.xxx.$id resolve ได้จริงไหม
      (ต้อง deploy จริงกับ credential จริงถึงจะรู้ — เพราะต้อง query live workspace)
    - เป็น private module (ขึ้นต้นด้วย _) — ถ้า fabric-cicd อัปเดต major version
      แล้วเปลี่ยน internal structure สคริปต์นี้อาจพังได้ ให้เช็ค changelog ก่อน upgrade

รัน:
    python scripts/debug_parameterization.py --environment prod
"""

import argparse
import os

from fabric_cicd._parameter._parameter import Parameter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ITEMS_DIR = os.path.join(BASE_DIR, "..", "fabric_items")

parser = argparse.ArgumentParser()
parser.add_argument("--environment", default="dev")
args = parser.parse_args()

Parameter(
    repository_directory=REPO_ITEMS_DIR,
    item_type_in_scope=["Notebook", "DataPipeline", "Dataflow", "Lakehouse"],
    environment=args.environment,
)

print(f"parameter.yml structure valid for environment='{args.environment}'")
print("Note: $items/$workspace variable resolution is NOT validated here — requires a live deploy.")
