# CI/CD Template — Microsoft Fabric (GitHub Actions + fabric-cicd)

Starter template สำหรับ repo ใหม่ที่จะทำ CI/CD กับ Microsoft Fabric — ดึงมาจาก mechanism ที่พิสูจน์แล้วจริงใน `dataops-fabric-pilot` (ดีไซน์เต็มอยู่ที่ `DataOps-CICD-Workflow.md` ในรีโปเอกสารแยก) ตัดเหลือเฉพาะส่วนที่จำเป็นต่อการทำ CI (5 check pattern) + CD แบบ **dev → staging → prod** (มี staging เสมอ) + Live Data Quality Gate + deploy ข้าม workspace (endpoint) เป็น starting point สำหรับ repo ใหม่ — ไม่มี Fabric item จริงติดมาด้วย (ต้องเชื่อม Fabric Git Integration เอง ดู `docs/setup-github-fabric.md`)

---

## เริ่มจากตรงไหน

ทำตามลำดับ — ขั้นหลังพึ่งขั้นก่อน

| ขั้น | ทำอะไร | ดูที่ |
|---|---|---|
| 1 | สร้าง repo/branch (`dev`, `staging`, `main`), workspace, Service Principal, GitHub Secrets/Environment, เปิด Git Integration, ตั้ง branch protection | `docs/setup-github-fabric.md` |
| 2 | กรอก workspace GUID ของ `dev` / `staging` / `prod` | `workspace-config.yml` |
| 3 | สร้าง staging workspace (แยก Fabric Capacity จาก prod) และเข้าใจลำดับ job staging | `docs/staging-gate.md` |
| 4 | สร้าง item ผ่าน Fabric UI → Commit → item sync เข้า `fabric_items/` | กฎข้อ 1 ด้านล่าง |
| 5 | สร้าง config จาก item จริง: `python scripts/generate_ci_config.py` (`ci-config.yml`) และ `python scripts/generate_parameter.py` (`fabric_items/parameter.yml`) แล้วเติม test/contract ตาม pattern ของแต่ละ item | `docs/check-patterns-guide.md` |
| 6 | เปิด PR ทดลอง ดู job `test` → `dq-gate-dev` → `deploy-staging` ผ่านก่อนตั้งเป็น required check | `docs/staging-gate.md` |

---

## ผังโฟลเดอร์

```
ci-cd-template/
├── README.md                          ← ไฟล์นี้
├── ci-config.yml                      ← กฎว่า item ไหนเช็คแบบไหน (5 check pattern + _defaults ต่อ type)
├── workspace-config.yml               ← workspace GUID ต่อ environment (dev/staging/prod)
├── endpoint-targets.yml               ← item ที่ deploy ข้ามไปคนละ workspace + workspace ปลายทางต่อ environment
├── dq-gates.yml                       ← ลงทะเบียน live DQ gate (item + stages)
├── requirements.txt                   ← dependency ของ CI/สคริปต์
├── .env.example                       ← ตัวอย่าง .env สำหรับรันสคริปต์บนเครื่อง
├── .gitignore                         ← กัน .env, .venv, __pycache__, .pytest_cache
│
├── .github/
│   ├── workflows/fabric-ci.yml        ← workflow เดียวที่รัน CI + CD + DQ gate ทั้งหมด
│   └── PULL_REQUEST_TEMPLATE.md       ← เทมเพลต PR สำหรับงาน data pipeline
│
├── fabric_items/                      ← item หลักที่ sync จาก Fabric Git Integration (ถูก deploy)
│   ├── .gitkeep                       ← ไฟล์ว่างให้ git เก็บโฟลเดอร์ว่าง
│   └── parameter.yml                  ← remap GUID/ค่าต่อ environment ตอน deploy
├── fabric_items_endpoint/             ← item ของ endpoint workspace (Git Integration แยกสาย) — ว่างจนกว่าจะเชื่อม
│   └── .gitkeep
│
├── scripts/                           ← สคริปต์กลางของ CI/CD (ดูตารางด้านล่าง 13 ตัว)
│
├── tests/
│   ├── unit/                          ← test ต่อ Notebook (`test_<ชื่อ item>.py`) + เทมเพลต 2 ไฟล์
│   ├── schema/                        ← contract ต่อ Lakehouse/Warehouse + เทมเพลต
│   ├── data_quality/                  ← checkpoint + fixture CSV (กลไก CSV — ดูหมายเหตุสถานะด้านล่าง)
│   └── live_dq/                       ← เทมเพลต Notebook สำหรับ live DQ gate + README
│
└── docs/
    ├── setup-github-fabric.md         ← ตั้งค่าครั้งแรก (เริ่มที่นี่)
    ├── staging-gate.md                ← ลำดับ job staging + endpoint + การตั้งค่า
    ├── check-patterns-guide.md        ← คู่มือ check pattern + live DQ + เทมเพลตเต็ม
    └── implement-plan/
        ├── CICD-Rollout-Plan.docx     ← แผน implement สำหรับทีม (Phase 0–4, มาตรฐาน item, RACI)
        └── ONBOARDING.md              ← คู่มือใช้งานประจำวัน (สำเนา)
```

---

## Workflow: `.github/workflows/fabric-ci.yml`

**Trigger**: `push` เข้า `dev` / `main` / `feature/**` · `pull_request` เข้า `staging` / `main` · `workflow_dispatch` (สั่งมือ ใช้กับ `dq-gate-poc` เท่านั้น)

| Job | รันเมื่อ | ทำอะไร | อ่าน config ไฟล์ไหน |
|---|---|---|---|
| `test` | ทุก push/PR | หา item จากไฟล์ `.platform` แล้วรัน check ตาม pattern ของแต่ละ item + สรุปผลเป็น Job Summary/PR comment | `ci-config.yml`, `tests/` |
| `dq-gate-dev` | `pull_request` | รัน live DQ gate บน workspace dev ก่อน deploy ไป staging (บน push จะ `skipped` ตามปกติ) | `dq-gates.yml`, `workspace-config.yml` |
| `deploy-staging` | PR เข้า `main`/`staging` และ push เข้า `main` | deploy `fabric_items/` เข้า staging | `workspace-config.yml` → `staging` |
| `verify-staging-guids` | หลัง `deploy-staging` | ตรวจ GUID ของ Dev ตกค้างใน staging (รายงานอย่างเดียว ไม่บล็อก) | `fabric_items/parameter.yml` |
| `dq-gate-staging` | หลัง `deploy-staging` | live DQ gate บน staging ก่อน deploy ไป prod | `dq-gates.yml` |
| `deploy-endpoints-staging` | หลัง `deploy-staging` | deploy endpoint item เข้า endpoint workspace ของ staging | `endpoint-targets.yml` → `targets.staging` |
| `deploy-prod` | push เข้า `main` (รอ approve ที่ Environment `production`) | deploy เข้า prod — ไม่รันถ้า job staging ใดล้มเหลว | `workspace-config.yml` → `prod` |
| `deploy-endpoints` | push เข้า `dev`/`main` | deploy endpoint item ตาม environment | `endpoint-targets.yml` |
| `dq-gate-poc` | หลัง `deploy-prod` หรือ `workflow_dispatch` | ยืนยันข้อมูลใน prod หลัง deploy (ไม่ใช่ gate ก่อน deploy) | `dq-gates.yml` |

ลำดับเต็ม: `test → dq-gate-dev → deploy-staging → (dq-gate-staging, deploy-endpoints-staging, verify-staging-guids) → deploy-prod → dq-gate-poc` (+ `deploy-endpoints`) — รายละเอียดที่ `docs/staging-gate.md`

---

## ไฟล์ config ที่ root

| ไฟล์ | หน้าที่ | แก้เมื่อไร |
|---|---|---|
| `ci-config.yml` | map item → check pattern (`unit_test` / `data_quality` / `structure` / `schema` / `none`); `_defaults.<type>` ลด boilerplate; `skip_check: true` + `skip_reason` ข้ามรายตัว; ไม่ระบุ = `unit_test` (fail-safe) | เพิ่ม item ใหม่ที่ pattern ต่างจาก default / item type ใหม่ / ข้ามชั่วคราว |
| `workspace-config.yml` | workspace GUID ต่อ environment (`dev` / `staging` / `prod`) ของ `fabric_items/` เท่านั้น — ไม่ใช่ secret | ครั้งแรก และทุกครั้งที่สร้าง workspace ใหม่ |
| `endpoint-targets.yml` | endpoint item ตัวไหน (`item_path`, `repo_dir`) deploy ไป workspace ไหนต่อ environment (`targets`) — เพิ่ม endpoint = เพิ่ม entry ไม่ต้องแก้ workflow | เพิ่ม/ย้าย endpoint |
| `dq-gates.yml` | gate ที่ต้องรัน (`item_type`: notebook/pipeline, `stages`: dev/staging/prod) — เพิ่ม gate = เพิ่ม entry ไม่ต้องแก้ workflow | เพิ่ม live DQ gate |
| `fabric_items/parameter.yml` | rule `find_replace` remap GUID (lakehouse/workspace) ให้ตรง environment ปลายทาง; ตอนนี้ว่างเปล่า | มี Notebook ตัวแรกที่ attach lakehouse / อ้างอิงข้าม workspace |
| `requirements.txt` | `fabric-cicd`, `pytest`, `great_expectations` (1.x), `pandas`, `azure-identity`, `PyYAML` | อัปเดต dependency |
| `.env.example` | ตัวอย่าง `.env` (`FABRIC_TENANT_ID` / `FABRIC_CLIENT_ID` / `FABRIC_CLIENT_SECRET`) สำหรับรัน `deploy.py` / `run_live_dq_item.py` บนเครื่อง — copy เป็น `.env` (ถูก `.gitignore` ห้าม commit) ส่วน `deploy_local.py` ไม่ต้องใช้เพราะ login ผ่าน browser | รันสคริปต์ local |
| `.gitignore` | กัน `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/` | แทบไม่ต้องแก้ |
| `.github/PULL_REQUEST_TEMPLATE.md` | เทมเพลต PR ที่ถามเรื่อง impact/downstream, breaking change, backfill และสถานะ test | ปรับตามทีม |

---

## Scripts (`scripts/`)

### ใช้ใน CI (workflow เรียกเอง)

| สคริปต์ | หน้าที่ | ตัวอย่างคำสั่ง |
|---|---|---|
| `deploy.py` | publish item ใต้ `fabric_items/` เข้า workspace ปลายทางด้วย Service Principal + ลบ item ที่หายจาก repo (`unpublish_all_orphan_items`; Lakehouse/Warehouse/SQL Database ไม่ถูกลบโดยดีฟอลต์); ล้าง `__pycache__` ก่อน publish; `--items-path` จำกัดเฉพาะ item เดียว (ข้าม unpublish) | `python scripts/deploy.py --workspace <GUID> --environment staging` · endpoint: `--repo-dir fabric_items_endpoint --items-path <item>.Lakehouse` |
| `deploy_endpoints.py` | อ่าน `endpoint-targets.yml` แล้ววนเรียก `deploy.py` ให้ทุก entry ที่มี target ตรงกับ environment (entry ที่ไม่มี target ถูกข้ามเงียบๆ) | `python scripts/deploy_endpoints.py --environment prod` |
| `run_live_dq_stage.py` | อ่าน `dq-gates.yml` แล้ววนเรียก `run_live_dq_item.py` ให้ทุก gate ของ stage นั้น (workspace ID อ่านจาก `workspace-config.yml`; ไม่มี gate = ผ่านพร้อม notice) | `python scripts/run_live_dq_stage.py --stage dev` |
| `run_live_dq_item.py` | สั่งรัน pipeline/notebook ที่มี live GX check ข้างในผ่าน Fabric REST API แล้ว poll จนจบ — fail ถ้า item fail | `python scripts/run_live_dq_item.py --workspace <GUID> --item-type notebook --item-name <ชื่อ> --timeout 1800` |
| `validate_pipeline_structure.py` | check = `structure`: ตรวจว่า activity ที่อ้างอิง item อื่น (`notebookId` ฯลฯ) มี item จริงใน repo (ไม่มี dangling reference) | `python scripts/validate_pipeline_structure.py "fabric_items/<folder>/"` |
| `validate_schema_contract.py` | check = `schema`: ตรวจว่ามี `tests/schema/<ชื่อ>.yml` และ format ถูก (ไม่ได้เทียบกับ schema จริงบน Fabric) | `python scripts/validate_schema_contract.py "fabric_items/<folder>/"` |
| `run_data_quality_checkpoint.py` | check = `data_quality`: อ่าน `tests/data_quality/checkpoints/dq_<ชื่อ>.yml` แล้วรัน Great Expectations 1.x กับ CSV fixture | `python scripts/run_data_quality_checkpoint.py dq_<ชื่อ>` |
| `verify_deployed_guids.py` | ตรวจหลัง deploy ว่าไม่มี GUID ของ Dev ตกค้างใน item ของ target (อ่านอย่างเดียว) — PASS ไม่ได้พิสูจน์ว่าชี้ถูกที่ ต้องดู INFO ด้วย ใช้เวลาหลายนาที | `python scripts/verify_deployed_guids.py --source <dev GUID> --target <prod GUID> [--allow <GUID>] [--forbid <GUID>] [--interactive]` |

### รันมือ (เครื่องมือช่วย — ไม่มีก็รัน CI ได้)

| สคริปต์ | หน้าที่ | ใช้ตอนไหน / ตัวอย่าง |
|---|---|---|
| `generate_ci_config.py` | bulk-generate `ci-config.yml` จาก item จริงใน `fabric_items/` (ไม่มีหลักฐาน test/checkpoint → ใส่ `skip_check` + เหตุผลอัตโนมัติ) | onboard item จำนวนมากครั้งแรก · `python scripts/generate_ci_config.py --dry-run` |
| `generate_parameter.py` | bulk-generate `parameter.yml` จาก metadata ที่ Fabric ฝังในไฟล์ item (Notebook/DataPipeline); ไม่แตะ entry เดิม; เตือนเรื่อง Connection ที่ต้องกรอกเอง | หลังเพิ่ม Notebook ที่ attach lakehouse · `python scripts/generate_parameter.py --dry-run` |
| `generate_parameter_all_types.py` | หา GUID ที่ต้อง remap **ทุก item type** โดยเทียบกับ item จริงใน Dev ผ่าน Fabric REST API (ต้องมี credential อ่าน Dev) | หลังเพิ่ม item ใหม่ที่อาจฝัง GUID · `python scripts/generate_parameter_all_types.py --workspace dev --dry-run` (`--interactive` login ผ่าน browser) |
| `debug_parameterization.py` | validate โครงสร้าง `parameter.yml` แบบ offline ไม่ต้องมี credential (ตรวจโครงสร้างได้ ไม่ได้ตรวจว่า `$items...` resolve ได้จริง) | ก่อน push · `python scripts/debug_parameterization.py --environment staging` |
| `deploy_local.py` | deploy แบบ login ผ่าน browser แทน Service Principal — fallback เมื่อ SP ไม่มีสิทธิ์บน Connection; รันผ่าน GitHub Actions ไม่ได้ ข้าม PR review ต้องแจ้งทีมทุกครั้ง | `python scripts/deploy_local.py --workspace <GUID> --environment prod` (flag เหมือน `deploy.py`) |

---

## tests/ และเทมเพลต

> ไฟล์ `_TEMPLATE*` ไม่ถูก pytest เก็บไปรัน และไม่ถูก deploy — ต้อง copy ไปตั้งชื่อใหม่ให้ตรงชื่อ item ก่อนใช้

| ไฟล์ | หน้าที่ |
|---|---|
| `tests/unit/_TEMPLATE_unit_test.py` | เทมเพลตทั่วไปเทส transform logic ของ Notebook → copy เป็น `tests/unit/test_<ชื่อ item>.py` (ชื่อต้องตรง item เป๊ะ) |
| `tests/unit/_TEMPLATE_dq_rule_check.py` | เทมเพลตเฉพาะเทส "DQ rule function" ด้วย mock data — ตั้งชื่อลงท้าย `_check.py` ตั้งใจให้ pytest ไม่เก็บไปรันเอง (copy ไปเป็น `test_<ชื่อ>.py` ก่อนใช้) |
| `tests/schema/_TEMPLATE.yml` | contract ของ Lakehouse/Warehouse → copy เป็น `tests/schema/<ชื่อ item>.yml` |
| `tests/data_quality/checkpoints/dq_TEMPLATE.yml` | เทมเพลต checkpoint (จัด expectation ตาม 7 มิติ DQ) → copy เป็น `dq_<ชื่อ item>.yml` |
| `tests/data_quality/checkpoints/dq_selftest_good.yml`, `dq_selftest_bad.yml` | worked example คู่ผ่าน/ไม่ผ่าน เพื่อพิสูจน์ว่ากลไกทำงาน |
| `tests/data_quality/fixtures/dq_selftest_good_data.csv`, `dq_selftest_bad_data.csv` | ข้อมูล CSV ของ self-test ข้างบน |
| `tests/live_dq/_TEMPLATE_nb_live_dq.py` | โค้ด Notebook live DQ (GX) ให้ copy ไปวางทีละ cell ใน Notebook จริง (live DQ ไม่ใช่ 1 ใน 5 check pattern) |
| `tests/live_dq/README.md` | ขั้นตอนตั้ง live DQ gate + snippet `ci-config.yml`/`dq-gates.yml` + วิธีทดสอบ 2 เคส (ข้อมูลดี/เสีย) |

---

## docs/

| ไฟล์ | เปิดตอนไหน |
|---|---|
| `docs/setup-github-fabric.md` | **เริ่มที่นี่** — ตั้งค่าครั้งแรก: repo/branch, workspace, Service Principal, GitHub Secrets/Environment, Git Integration, branch protection, ทดลองก่อนใช้จริง, rollback โค้ดด้วย `git revert` |
| `docs/staging-gate.md` | **อ่านก่อนเปิดใช้ staging** — ลำดับ job, ขั้นตอนตั้งค่า, endpoint item, ข้อควรรู้ |
| `docs/check-patterns-guide.md` | เลือก pattern ให้ item, live DQ vs CSV, เทมเพลตเต็ม (Notebook code, pipeline activity, ci-config entry, workflow job), contract schema, `skip_check` |
| `docs/implement-plan/CICD-Rollout-Plan.docx` | แผน implement สำหรับทีม: ขอบเขต, มาตรฐานที่ item ต้องตรงก่อน onboard, Phase 0–4, บทบาท, ความเสี่ยง |
| `docs/implement-plan/ONBOARDING.md` | คู่มือใช้งานประจำวัน: daily workflow, เพิ่ม item, ปรับ item/config ให้ deploy ได้, troubleshooting (สำเนา — ลิงก์ไป `DataOps-CICD-Workflow.md` ในไฟล์นั้นชี้ไปรีโปเอกสารแยก) |

### `data_quality` (CSV fixture) — เทมเพลตพร้อมใช้ แต่สถานะยังไม่ฟันธง

`tests/data_quality/checkpoints/dq_TEMPLATE.yml` + worked example (`dq_selftest_good.yml`/`dq_selftest_bad.yml` คู่กับ fixture CSV ใน `tests/data_quality/fixtures/`) มากับ template นี้เพื่อพิสูจน์ว่ากลไกใช้งานได้จริง — **แต่ก่อนใช้เป็น default จริงบน item สำคัญ ให้คุยกับทีมก่อนว่ามี workspace/ทีมอื่นใช้ไฟล์ CSV แบบนี้อยู่แล้วหรือเปล่า** (ดูรายละเอียดสถานะที่ `docs/check-patterns-guide.md` ส่วนที่ 5 และ `DataOps-CICD-Workflow.md` ของรีโปเอกสารแยก) — Live DQ Gate ยังเป็นทางเลือกที่แนะนำสำหรับข้อมูล production จริงไม่ว่าผลจะออกมายังไง ต่างจาก check pattern `data_quality` ตรงที่ live gate เช็คข้อมูลจริงบน Lakehouse/Warehouse ผ่าน Spark/Notebook ที่ deploy ไปแล้ว จึงเป็น CI job แยกที่รันหลัง deploy ไม่ใช่ส่วนหนึ่งของ job `test`

---

## สิ่งที่ตั้งใจไม่รวมมาใน template นี้

- **Fabric item ตัวอย่าง/ทดสอบ** (Notebook/Pipeline/Lakehouse demo ต่างๆ) — repo นี้ตั้งใจให้เริ่มจากศูนย์ item จริงจะ sync เข้ามาเองผ่าน Fabric Git Integration หลังเชื่อมต่อ

---

## ข้อจำกัด/กฎที่ต้องรู้ก่อนเริ่มงาน

1. **สร้าง item ผ่าน Fabric UI หรือ MCP เท่านั้น** — ห้าม hand-write ไฟล์ item ตรงเข้า `fabric_items/` เอง (logicalId จะไม่ตรง ทำให้ Fabric sync conflict) ต้องกด **Commit ผ่าน Fabric UI (Source Control panel) เสมอ** ไม่ว่าจะสร้างวิธีไหน

2. **ชื่อไฟล์ test ต้องตรงชื่อ item เป๊ะ** — `nb_xxx.Notebook` ↔ `tests/unit/test_xxx.py` ไม่ตรง CI หาไม่เจอ error ทันที

3. **`ci-config.yml` เป็น fail-safe เข้ม** — ไม่ระบุ = ต้องมี unit test เสมอ (default) ถ้าจะข้ามต้องเขียน `skip_check: true` + `skip_reason` เสมอ ห้ามปล่อยว่าง ไม่งั้น CI fail แทนที่จะผ่านเงียบๆ

4. **`parameter.yml` ระวัง environment key พิมพ์ผิด** — ถ้า key (`dev`/`staging`/`prod` — workflow ส่ง `staging` เข้า `deploy.py` ตอน `deploy-staging`) ไม่ตรงกับที่ `deploy.py --environment` ส่งเข้าไป **fabric-cicd จะข้าม rule นั้นไปเงียบๆ ไม่ error เตือน** ต้องเช็คเอง

5. **staging บังคับมีเสมอ** — ก่อน push ครั้งแรกต้องสร้าง staging workspace (แยก Fabric Capacity จาก prod), ให้ Service Principal เข้าถึง, และกรอก GUID ใน `workspace-config.yml` → `staging` ไม่งั้น `deploy-staging` fail และ `deploy-prod` ไม่รัน ขั้นตอนเต็มที่ `docs/staging-gate.md` — ⚠️ flow staging ยังไม่เคยรันครบทั้งเส้นบน GitHub จริง ทดลองด้วย PR ทดลองก่อนบังคับเป็น required check

6. **ก่อน push เข้า `main` ต้องตั้งค่า GitHub Environment `production`** (Settings → Environments) พร้อม Required reviewers ไม่งั้น `deploy-prod` จะรันทันทีไม่มีใครอนุมัติก่อน

7. **GitHub Actions secrets ที่ต้องตั้ง**: `FABRIC_CLIENT_ID`, `FABRIC_CLIENT_SECRET`, `FABRIC_TENANT_ID` (ของ Service Principal ที่มีสิทธิ์บน workspace ปลายทาง)

8. **`skip_check` คือหนี้เทคนิค** ไม่ใช่คำตอบถาวร — ต้องมีคนกลับมาเขียน test/contract จริงแล้วเอา flag ออกทีหลัง

9. **ตั้งกฎ branch และ environment ก่อนใช้งานจริง** (Settings → Branches / Environments — ต้องเป็นผู้ดูแล repo):
   - `main`: PR-only + review อย่างน้อย 1 คน + บังคับกับ admin + ห้าม force push/ลบ และ required status check = `test`, `dq-gate-dev`, `dq-gate-staging` (job เหล่านี้มีใน workflow แล้ว)
     เพิ่ม check อื่น (เช่น job DQ gate) เป็น required ได้ **เฉพาะเมื่อ workflow ของคุณมี job ชื่อนั้นรายงานผลจริง** — ถ้าตั้ง required check ที่ไม่มี job รายงาน PR จะค้างรอตลอด
     (job ที่ถูก skip ด้วยเงื่อนไข `if` GitHub นับเป็นผ่าน — `dq-gate-dev` skipped บน push จึงไม่บล็อก; ถ้าไม่มี gate ใน `dq-gates.yml` job ผ่านพร้อม notice) ดู `docs/staging-gate.md`
   - `dev`: ถ้าใช้ Fabric Git Integration commit เข้า `dev` ตรง **อย่าบังคับ PR/required check บน `dev`** (จะบล็อกการ commit จาก Fabric) ตั้งแค่ห้าม force push และห้ามลบ
   - environment `production`: Required reviewers + **deployment branch policy = เฉพาะ `main`**

10. **บทเรียนเรื่อง GUID ที่เจอจาก pilot** (รายละเอียดใน section 14 ของ `DataOps-CICD-Workflow.md`):
    - GUID รูปแบบ "สลับ" ที่เห็นในไฟล์ DataPipeline มักเป็น **logicalId** ใน `.platform` (`fabric-cicd` แทนให้เองตอน publish) — เช็คกับ `.platform` ก่อนเพิ่ม rule ใน `parameter.yml` และอ่านค่าจริงใน target workspace ยืนยันก่อนสรุปว่ามี gap
    - อย่าลบหรือแก้ `find_value` ของ rule เดิม จนกว่าไฟล์ item ทุกตัวจะไม่มีค่านั้นแล้ว ถ้า item ถูกสร้างใหม่ (id เปลี่ยน) ต้องเพิ่ม rule สำหรับ id ใหม่ก่อน sync เข้า git
    - id ที่ hardcode ข้าม workspace พังทุกครั้งที่ item ถูกสร้างใหม่ — ถ้าเลี่ยงได้ให้ notebook หา item จากชื่อตอนรัน
    - `verify_deployed_guids.py` PASS ≠ ชี้ถูกที่ — ดู INFO ด้วยเสมอ

ดูบริบทดีไซน์เต็ม (ทำไมถึงเป็น pattern-based, environment strategy, git branching ฯลฯ) ได้ที่ `DataOps-CICD-Workflow.md` ของรีโปเอกสารแยก
