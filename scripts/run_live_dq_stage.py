import os
import sys
import argparse
import subprocess
import yaml

# อ่าน dq-gates.yml แล้ววน run_live_dq_item.py ให้ทุก gate ที่มี stage ตรงกับ --stage —
# เพิ่ม gate ใหม่แก้แค่ dq-gates.yml ไม่ต้องแก้ fabric-ci.yml (pattern เดียวกับ deploy_endpoints.py)
# workspace ID ของแต่ละ stage อ่านจาก workspace-config.yml (key dev / staging / prod)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GATES_PATH = os.path.join(BASE_DIR, "..", "dq-gates.yml")
WORKSPACE_CONFIG_PATH = os.path.join(BASE_DIR, "..", "workspace-config.yml")
GATE_SCRIPT = os.path.join(BASE_DIR, "run_live_dq_item.py")

parser = argparse.ArgumentParser()
parser.add_argument("--stage", required=True, choices=["dev", "staging", "prod"])
args = parser.parse_args()

with open(GATES_PATH, encoding="utf-8") as f:
    gates = yaml.safe_load(f) or {}
with open(WORKSPACE_CONFIG_PATH, encoding="utf-8") as f:
    workspaces = yaml.safe_load(f) or {}

selected = {name: spec for name, spec in gates.items() if args.stage in (spec.get("stages") or [])}
if not selected:
    print(f"::notice::ไม่มี live DQ gate ใน dq-gates.yml สำหรับ stage '{args.stage}' — ข้าม", flush=True)
    sys.exit(0)

workspace_id = workspaces.get(args.stage)
if not workspace_id or str(workspace_id).startswith("<"):
    # มี gate ให้รันแต่ยังไม่ได้กรอก workspace ID — ต้อง fail ไม่ปล่อยผ่านเงียบๆ
    print(f"::error::workspace-config.yml → {args.stage} ยังไม่ได้กรอก GUID แต่มี gate ที่ต้องรัน", flush=True)
    sys.exit(1)

failed = []
for item_name, spec in selected.items():
    cmd = [
        sys.executable, GATE_SCRIPT,
        "--workspace", str(workspace_id),
        "--item-type", spec.get("item_type", "notebook"),
        "--item-name", item_name,
    ]
    print(f"::group::Live DQ gate '{item_name}' -> workspace {workspace_id} (stage={args.stage})", flush=True)
    result = subprocess.run(cmd)
    print("::endgroup::", flush=True)
    if result.returncode != 0:
        failed.append(item_name)

if failed:
    print(f"::error::Live DQ gate fail: {', '.join(failed)}", flush=True)
    sys.exit(1)
