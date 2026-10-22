"""
Bulk-generate/update fabric_items/parameter.yml จาก metadata ที่ Fabric ฝังไว้ในไฟล์ item เอง
(notebook-content.py ของ Notebook, pipeline-content.json ของ DataPipeline) — ใช้ตอนมี item
attach lakehouse/connection จำนวนมาก ไม่ต้องไล่เปิดทีละไฟล์มาหา GUID เอง (คู่กับ generate_ci_config.py)

หลักการ (evidence-based, ไม่เดา):
  1. Notebook — Fabric เก็บทั้ง GUID และชื่อจริงไว้คู่กันในบล็อก METADATA แรกของทุก Notebook
     ที่ attach lakehouse (ยืนยันจริงจาก nb_test_source_and_destination.Notebook):
       dependencies.lakehouse.default_lakehouse             -> GUID lakehouse ตอนสร้าง (dev)
       dependencies.lakehouse.default_lakehouse_name         -> ชื่อ lakehouse
       dependencies.lakehouse.default_lakehouse_workspace_id -> GUID workspace ตอนสร้าง (dev)

  2. DataPipeline (Copy Activity) — เก็บ GUID เดียวกันของ lakehouse ไว้อีกจุดหนึ่งแยกต่างหาก
     ใน connectionSettings.properties.typeProperties.artifactId (ยืนยันจริงจาก
     pl_test_source_and_destination.DataPipeline) **แต่เป็นคนละ format กับ default_lakehouse
     ของ Notebook** (Fabric สลับ byte order ระหว่าง 2 จุดนี้ — ยืนยันแล้วว่าเป็น lakehouse
     เดียวกันจริง แค่คนละ string) เลย find_replace entry ของ Notebook จะ "ไม่ match" ค่านี้เลย
     ต้องมี entry แยกต่างหากสำหรับ DataPipeline โดยเฉพาะ ถึงจะ scan เจอ — ชื่อ lakehouse
     ฝังมาคู่กันที่ connectionSettings.name เหมือนกับฝั่ง Notebook เลยยัง resolve ชื่อได้เอง

  3. `externalReferences.connection` ใน DataPipeline คือ external Connection ID จริง —
     **ไม่มีชื่อกำกับมาด้วย** (ไม่ใช่ Fabric Git item) ไม่มีทาง resolve เป็น $items. lookup ได้
     สคริปต์นี้แค่ "เตือน" ให้คนกรอกค่าต่อ environment เอง ไม่เดาให้ (ดู DataOps-CICD-Workflow.md
     section 16 — เหตุผลเดียวกับที่ Copy Activity เจอปัญหา Service Principal permission)

  find_replace ของ fabric-cicd สแกน string ข้าม item ทั้งหมดที่ item_type ตรงกันอยู่แล้ว
  (ไม่ต้องมี item_name ต่อ entry) เลยต้องการ entry แค่ 1 ต่อ "GUID ที่ไม่ซ้ำกัน" ไม่ใช่ 1 ต่อ item

ข้อจำกัด:
  - ไม่แตะ entry เดิมที่มีอยู่แล้วใน parameter.yml (merge, ไม่ overwrite) — เขียนต่อท้ายไฟล์เป็น
    text เหมือน generate_ci_config.py เพื่อไม่ให้ comment เดิมหาย โดยสมมติว่า find_replace
    เป็น section สุดท้ายของไฟล์ (ตรงกับโครงสร้างจริงของ parameter.yml ตอนนี้)

ใช้:
    python scripts/generate_parameter.py            # เขียนทับ parameter.yml จริง
    python scripts/generate_parameter.py --dry-run  # print ผลลัพธ์ดูก่อน ไม่เขียนไฟล์
"""

import argparse
import io
import json
import os
import re
import sys

import yaml

# กัน console บน Windows แสดงภาษาไทยเพี้ยน (cp874 default) — ไม่กระทบตอนรันบน Linux/GitHub Actions
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.join(BASE_DIR, "..")
FABRIC_ITEMS_DIR = os.path.join(REPO_ROOT, "fabric_items")
PARAMETER_YML_PATH = os.path.join(FABRIC_ITEMS_DIR, "parameter.yml")

META_LINE_PREFIX = "# META "   # เว้นวรรคท้ายตั้งใจ — แยกจาก "# METADATA ****" (header marker คนละความหมาย)


def load_yaml(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _iter_item_dirs():
    """
    ไล่หา item folder แบบ recursive ผ่าน marker ".platform" (ไฟล์ที่ Fabric สร้างให้ทุก item จริง)
    แทน os.listdir ระดับเดียว — เพราะ item อาจอยู่ใต้ Fabric workspace folder ได้ (เช่น fabric_items/yayee/...)
    yield (name, fabric_type, full_path) ไม่ descend ต่อเข้าไปในโฟลเดอร์ item เอง (Tables/, Files/ ฯลฯ)
    """
    for dirpath, dirnames, filenames in os.walk(FABRIC_ITEMS_DIR):
        if ".platform" not in filenames:
            continue
        entry = os.path.basename(dirpath)
        if "." in entry:
            name, fabric_type = entry.rsplit(".", 1)
            yield name, fabric_type, dirpath
        dirnames[:] = []  # หยุดไต่ลึกต่อจาก item folder นี้


def list_fabric_items():
    return sorted((name, fabric_type) for name, fabric_type, _ in _iter_item_dirs())


def extract_first_metadata_block(notebook_text):
    """
    คืน dict ของบล็อก METADATA แรกในไฟล์ (บล็อกระดับ notebook ที่มี "dependencies")
    ไม่ใช่บล็อก METADATA ของแต่ละ cell (ซึ่งมีแค่ "language" เฉยๆ ไม่มี dependencies)
    """
    block_lines = []
    collecting = False
    for line in notebook_text.splitlines():
        if line.startswith(META_LINE_PREFIX):
            block_lines.append(line[len(META_LINE_PREFIX):])
            collecting = True
        elif collecting:
            break  # จบบล็อกแรกแล้ว ไม่ต้องอ่านต่อ

    if not block_lines:
        return None

    try:
        return json.loads("\n".join(block_lines))
    except json.JSONDecodeError:
        return None


def scan_notebook_lakehouse_refs():
    """
    ไล่ทุก Notebook item หา default_lakehouse ref จริง
    คืน (lakehouse_refs, workspace_ids, unnamed_known_ids, unresolved_notebooks)
      lakehouse_refs: dict {guid: name} ของ default_lakehouse ที่เจอ
      workspace_ids: set ของ default_lakehouse_workspace_id ที่เจอ
      unnamed_known_ids: set ของ known_lakehouses id ที่ไม่ใช่ default_lakehouse (ไม่มีชื่อกำกับ)
      unresolved_notebooks: list ชื่อ notebook ที่ parse metadata ไม่ได้ (ไฟล์ผิดรูปแบบที่คาด)
    """
    lakehouse_refs = {}
    workspace_ids = set()
    unnamed_known_ids = set()
    unresolved_notebooks = []

    for name, fabric_type, item_dir in sorted(_iter_item_dirs()):
        if fabric_type != "Notebook":
            continue
        content_path = os.path.join(item_dir, "notebook-content.py")
        if not os.path.exists(content_path):
            unresolved_notebooks.append(name)
            continue

        with open(content_path, encoding="utf-8") as f:
            text = f.read()

        metadata = extract_first_metadata_block(text)
        if metadata is None:
            unresolved_notebooks.append(name)
            continue

        lakehouse = metadata.get("dependencies", {}).get("lakehouse")
        if not lakehouse:
            continue  # notebook นี้ไม่ได้ attach lakehouse เลย ข้ามไปเฉยๆ ไม่ใช่ error

        default_id = lakehouse.get("default_lakehouse")
        default_name = lakehouse.get("default_lakehouse_name")
        workspace_id = lakehouse.get("default_lakehouse_workspace_id")

        if default_id and default_name:
            lakehouse_refs[default_id] = default_name
        if workspace_id:
            workspace_ids.add(workspace_id)

        for known in lakehouse.get("known_lakehouses", []):
            known_id = known.get("id")
            if known_id and known_id != default_id:
                unnamed_known_ids.add(known_id)

    return lakehouse_refs, workspace_ids, unnamed_known_ids, unresolved_notebooks


def walk_json(node):
    """ไล่ทุก dict ใน JSON tree แบบ recursive (รองรับ dict/list ซ้อนกันกี่ชั้นก็ได้)"""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk_json(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk_json(item)


def scan_pipeline_refs():
    """
    ไล่ทุก DataPipeline หา Lakehouse connectionSettings (Copy Activity source/sink) และ
    external Connection reference — โครงสร้างจริงที่เจอ (pl_test_source_and_destination):
        connectionSettings: {
          name: "lh_test_lakehouse",
          properties: {
            type: "Lakehouse",
            typeProperties: { artifactId: "...", workspaceId: "00000000-...", ... },
            externalReferences: { connection: "..." }
          }
        }
    คืน (lakehouse_refs, connection_ids, unresolved_pipelines)
      lakehouse_refs: dict {artifact_id: name} — ชื่อ lakehouse ฝังคู่มาด้วยเหมือน Notebook
      connection_ids: set ของ externalReferences.connection ที่เจอ (ไม่มีชื่อกำกับ ต้องกรอกเอง)
      unresolved_pipelines: list ชื่อ pipeline ที่ parse JSON ไม่ได้เลย (ไฟล์ผิด format)
    """
    lakehouse_refs = {}
    connection_ids = set()
    unresolved_pipelines = []

    for name, fabric_type, item_dir in sorted(_iter_item_dirs()):
        if fabric_type != "DataPipeline":
            continue
        content_path = os.path.join(item_dir, "pipeline-content.json")
        if not os.path.exists(content_path):
            unresolved_pipelines.append(name)
            continue

        try:
            with open(content_path, encoding="utf-8") as f:
                pipeline_json = json.load(f)
        except json.JSONDecodeError:
            unresolved_pipelines.append(name)
            continue

        for node in walk_json(pipeline_json):
            properties = node.get("properties")
            if not isinstance(properties, dict) or properties.get("type") != "Lakehouse":
                continue

            type_properties = properties.get("typeProperties", {})
            artifact_id = type_properties.get("artifactId")
            lakehouse_name = node.get("name")
            if artifact_id and lakehouse_name:
                lakehouse_refs[artifact_id] = lakehouse_name

            external_refs = properties.get("externalReferences")
            if isinstance(external_refs, dict):
                connection_id = external_refs.get("connection")
                if connection_id:
                    connection_ids.add(connection_id)

    return lakehouse_refs, connection_ids, unresolved_pipelines


def build_lakehouse_entries(refs, item_type, known_lakehouse_names, existing_find_values):
    """
    สร้าง find_replace entry จาก {guid: name} — ใช้ร่วมกันได้ทั้ง Notebook และ DataPipeline
    แค่เปลี่ยน item_type เพราะ format ของ guid ที่ต้อง find คนละค่ากันตามที่เจอจริง
    คืน (new_entries, skipped_unresolved)
    """
    new_entries = []
    skipped_unresolved = []

    for guid, name in sorted(refs.items()):
        if guid in existing_find_values:
            continue
        if name not in known_lakehouse_names:
            skipped_unresolved.append((guid, name))
            continue
        new_entries.append({
            "find_value": guid,
            "replace_value": {"_ALL_": f"$items.Lakehouse.{name}.$id"},
            "item_type": item_type,
        })

    return new_entries, skipped_unresolved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="แสดงผลลัพธ์ ไม่เขียนไฟล์จริง")
    args = parser.parse_args()

    existing_config = load_yaml(PARAMETER_YML_PATH)
    existing_find_replace = existing_config.get("find_replace") or []
    existing_find_values = {rule.get("find_value") for rule in existing_find_replace if isinstance(rule, dict)}

    known_lakehouse_names = {name for name, fabric_type in list_fabric_items() if fabric_type == "Lakehouse"}

    nb_lakehouse_refs, workspace_ids, unnamed_known_ids, unresolved_notebooks = scan_notebook_lakehouse_refs()
    pl_lakehouse_refs, connection_ids, unresolved_pipelines = scan_pipeline_refs()

    nb_entries, nb_skipped = build_lakehouse_entries(
        nb_lakehouse_refs, "Notebook", known_lakehouse_names, existing_find_values
    )
    pl_entries, pl_skipped = build_lakehouse_entries(
        pl_lakehouse_refs, "DataPipeline", known_lakehouse_names, existing_find_values
    )

    workspace_entries = []
    for guid in sorted(workspace_ids):
        if guid in existing_find_values:
            continue
        workspace_entries.append({
            "find_value": guid,
            "replace_value": {"_ALL_": "$workspace.$id"},
            "item_type": "Notebook",
        })

    new_entries = nb_entries + workspace_entries + pl_entries
    skipped_unresolved = nb_skipped + pl_skipped

    print(f"Notebook: พบ lakehouse GUID {len(nb_lakehouse_refs)} รายการ, workspace GUID {len(workspace_ids)} รายการ")
    print(f"DataPipeline: พบ lakehouse artifactId {len(pl_lakehouse_refs)} รายการ, external connection {len(connection_ids)} รายการ")
    print(f"Entry เดิมใน parameter.yml: {len(existing_find_replace)} รายการ")
    print(f"Entry ใหม่ที่จะเพิ่ม: {len(new_entries)} รายการ")
    print()

    if unresolved_notebooks:
        print("⚠️  Notebook ที่ parse metadata ไม่ได้ (เช็คไฟล์เอง — อาจไม่ใช่ format ที่คาด):")
        for name in unresolved_notebooks:
            print(f"  - {name}")
        print()

    if unresolved_pipelines:
        print("⚠️  DataPipeline ที่ parse JSON ไม่ได้ (เช็คไฟล์เอง — อาจไม่ใช่ format ที่คาด):")
        for name in unresolved_pipelines:
            print(f"  - {name}")
        print()

    if skipped_unresolved:
        print("⚠️  ชื่อ lakehouse ที่เจอในไฟล์ item แต่หา item folder จริงไม่เจอ (ข้าม ไม่ auto-เขียน):")
        for guid, name in skipped_unresolved:
            print(f"  - {name} (guid={guid}) — เช็คว่าถูกลบ/เปลี่ยนชื่อไปแล้วหรือเปล่า")
        print()

    if unnamed_known_ids:
        print("⚠️  known_lakehouses guid อื่นที่ไม่มีชื่อกำกับ (ต้องเติม entry เองแยก ไม่เดาให้):")
        for guid in sorted(unnamed_known_ids):
            print(f"  - {guid}")
        print()

    if connection_ids:
        print("⚠️  external Connection ID ที่เจอใน DataPipeline (ไม่มีชื่อกำกับ ไม่ auto-generate ให้ —")
        print("     ต้องกรอกค่าจริงของแต่ละ environment เอง หลัง grant permission ให้ Service Principal แล้ว):")
        for guid in sorted(connection_ids):
            in_config = " (มี entry อยู่แล้ว)" if guid in existing_find_values else " (ยังไม่มี entry)"
            print(f"  - {guid}{in_config}")
        print()

    if not new_entries:
        print("ไม่มี entry ใหม่ต้องเพิ่ม — ไม่แตะไฟล์เลย (กัน comment ในไฟล์เดิมหาย)")
        return

    print("Entry ที่จะเพิ่ม:")
    for entry in new_entries:
        target = entry["replace_value"]["_ALL_"]
        print(f"  [{entry['item_type']}] {entry['find_value']} -> {target}")
    print()

    appended_yaml = yaml.dump(new_entries, allow_unicode=True, sort_keys=False, default_flow_style=False)
    # เยื้อง 2 ช่องให้ตรงกับ list item ที่อยู่ใต้ key "find_replace:" เดิม (ดู parameter.yml จริง)
    indented_yaml = "\n".join(f"  {line}" if line.strip() else line for line in appended_yaml.splitlines())

    if args.dry_run:
        print("--dry-run: ไม่เขียนไฟล์จริง — นี่คือส่วนที่จะต่อท้ายไฟล์เดิม:")
        print()
        print(indented_yaml)
        return

    if not existing_find_replace and not os.path.exists(PARAMETER_YML_PATH):
        # ไฟล์ยังไม่มีเลย — เขียนใหม่พร้อม key "find_replace:" ให้ครบ
        with open(PARAMETER_YML_PATH, "w", encoding="utf-8") as f:
            f.write("# fabric-cicd parameter file — สร้างโดย generate_parameter.py\n")
            f.write("# อ้างอิง: https://microsoft.github.io/fabric-cicd/latest/config_files/parameter/\n\n")
            f.write("find_replace:\n")
            f.write(indented_yaml)
        print(f"สร้าง {PARAMETER_YML_PATH} ใหม่เรียบร้อย ({len(new_entries)} entries)")
        return

    # ต่อท้ายไฟล์เดิมเป็น text แทนการ yaml.dump ทั้งไฟล์ใหม่ — กัน comment ในไฟล์เดิมหายไปหมด
    # สมมติว่า find_replace เป็น section สุดท้ายของไฟล์ (ตรงกับโครงสร้างจริงตอนนี้)
    with open(PARAMETER_YML_PATH, encoding="utf-8") as f:
        text = f.read()
    # template ตั้งต้นเป็น "find_replace: []" — ต่อ list item ท้ายไฟล์ตรงๆ จะได้ YAML ที่ผิด
    # ต้องเปลี่ยนเป็น block ("find_replace:") ก่อน
    text = re.sub(r"^find_replace:\s*\[\]\s*$", "find_replace:", text, flags=re.MULTILINE)
    with open(PARAMETER_YML_PATH, "w", encoding="utf-8") as f:
        f.write(text.rstrip("\n") + "\n\n# --- เพิ่มโดย generate_parameter.py ---\n" + indented_yaml + "\n")

    print(f"ต่อท้าย {PARAMETER_YML_PATH} เรียบร้อย ({len(new_entries)} entries ใหม่)")


if __name__ == "__main__":
    sys.exit(main())
