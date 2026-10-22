# Onboarding & Operating Manual: DataOps CI/CD for Microsoft Fabric

คู่มือนี้เขียนให้ **ใช้แทนการเปิด [`DataOps-CICD-Workflow.md`](./DataOps-CICD-Workflow.md) ในการทำงานประจำวัน** — ทุกขั้นตอนที่ต้องทำจริง (setup, daily workflow, เพิ่ม item ใหม่, แก้ปัญหา, rollback) อยู่ในไฟล์นี้ครบ ไม่ต้องสลับไปเปิดเอกสารหลักระหว่างทำงาน เอกสารหลักยังเก็บไว้สำหรับ design rationale เต็มรูป + pilot findings log แบบละเอียด (ดูลิงก์ท้ายไฟล์)

**สถานะข้อมูลในคู่มือนี้**: อ้างอิงจาก pilot repo `dataops-fabric-pilot` ที่ผ่านการทดสอบจริงแล้ว (ดู section "สถานะจริงตอนนี้" ด้านล่าง) — ไม่ใช่ design แบบเต็มรูปที่ยังไม่ implement

---

## สารบัญ

1. [TL;DR](#tldr)
2. [สถานะจริงตอนนี้ vs. Design เต็มรูป](#สถานะจริงตอนนี้-vs-design-เต็มรูป)
3. [Setup ครั้งแรก](#setup-ครั้งแรก)
   - [3.1 เครื่องมือบนเครื่องตัวเอง](#31-เครื่องมือบนเครื่องตัวเอง)
   - [3.2 Service Principal (ถ้ายังไม่มี/ต้องตั้งใหม่)](#32-service-principal-ถ้ายังไม่มีต้องตั้งใหม่)
   - [3.3 Fabric Workspace + Git Integration](#33-fabric-workspace--git-integration)
   - [3.4 GitHub Secrets / Environments / Branch Protection](#34-github-secrets--environments--branch-protection)
4. [Daily Workflow](#daily-workflow)
5. [CI Design: Pattern-Based Check (สำคัญ ต้องเข้าใจก่อนแก้อะไร)](#ci-design-pattern-based-check)
6. [Quick Start: เพิ่ม Fabric Item ใหม่](#quick-start-เพิ่ม-fabric-item-ใหม่)
7. [ปรับ Item และ Config ให้ Deploy ได้](#ปรับ-item-และ-config-ให้-deploy-ได้)
8. [เจอปัญหา ทำยังไง (Troubleshooting)](#เจอปัญหา-ทำยังไง-troubleshooting)
9. [Data Rollback vs Code Rollback](#data-rollback-vs-code-rollback)
10. [Repo Structure อ้างอิง](#repo-structure-อ้างอิง)
11. [Collaboration Model](#collaboration-model)
12. [รายละเอียดเพิ่มเติม/ประวัติ](#รายละเอียดเพิ่มเติมประวัติ)

---

## TL;DR

ทีมนี้ใช้ **GitHub Actions + `fabric-cicd`** เป็น CI/CD ให้ Microsoft Fabric — แก้ Notebook/Pipeline/Lakehouse ผ่าน **Fabric UI ก่อนเสมอ** (ห้าม hand-write ไฟล์ item ตรงเข้า git) แล้ว sync เข้า git อัตโนมัติผ่าน Git Integration, ผ่าน PR + automated check ตาม pattern ที่ประกาศไว้ใน `ci-config.yml`, แล้ว deploy เข้า production อัตโนมัติตอน merge เข้า `main` (รอ manual approval ก่อนรันจริง)

หลักการเดียวที่ทุกอย่างในคู่มือนี้อ้างอิงกลับมา: **git คือความจริงหนึ่งเดียว (single source of truth)** แต่ละ workspace มีทิศทางไหลของข้อมูลทางเดียวเท่านั้น ห้ามสวนทาง

---

## สถานะจริงตอนนี้ vs. Design เต็มรูป

Design เต็มรูปมี 3 environment (dev/staging/prod, 3 branch คู่กัน) แต่ **pilot ตอนนี้มีแค่ 2 workspace ใช้งานจริง** — ใช้ข้อมูลชุดนี้เป็นหลักเวลาทำงานจริง อย่ายึดตาม diagram/slide 3-env ที่ยังเป็นเป้าหมายระยะยาว:

| Environment | Workspace | Workspace ID | สถานะ |
|---|---|---|---|
| Dev | `spl-cicd-dev` | `<WORKSPACE_ID_DEV>` | ✅ ใช้งานจริง — แก้ผ่าน Fabric UI เท่านั้น |
| Staging | *(ยังไม่มี workspace แยก)* | — | ⚠️ Concept เท่านั้น — ดู `deploy-test-job.yml` (draft ยังไม่ได้ใช้) |
| Production | `spl-cicd-prd` | `<WORKSPACE_ID_PROD>` | ✅ ใช้งานจริง |

**ผลที่ตามมา**: merge จริงตอนนี้คือ `dev → main` ตรงๆ (ไม่มี `staging` แทรกกลาง) และ Fabric Capacity ของ staging/prod **ยังไม่ได้แยกกัน** ตามที่ Microsoft แนะนำ — ต้องวางแผนก่อนเข้า rollout เต็มรูป

Lakehouse หลักที่ใช้ทดสอบ: `lh_test_lakehouse` (มีอยู่ทั้ง Dev และ Prod แยกกัน คนละ Lakehouse ID — `parameter.yml` เป็นตัว remap ให้อัตโนมัติตอน deploy)

### CI/CD Flow จริง (ตอนนี้)

```
Fabric UI (สร้าง/แก้ item ใน ws-pilot-dev/spl-cicd-dev)
    ↓ Source Control → Commit
GitHub (branch: dev)
    ↓ Push
GitHub Actions: job "test"
    ├── อ่าน ci-config.yml → รู้ว่า item ไหนต้องเช็คแบบไหน
    ├── รัน check ตาม pattern (unit_test / structure / schema / data_quality / none)
    └── Post ตาราง summary กลับเข้าหน้า Actions run (Job Summary)
    ↓ เปิด PR dev → main → Review → Merge
GitHub Actions: job "deploy-prod" (auto-trigger ตอน push เข้า main)
    ├── รอ Manual Approval (GitHub Environment protection: production)
    ├── fabric-cicd: publish_all_items() + unpublish_all_orphan_items()
    └── parameter.yml remap GUID ให้ตรง environment ปลายทาง
    ↓
Production Workspace (spl-cicd-prd)
```

---

## Setup ครั้งแรก

### 3.1 เครื่องมือบนเครื่องตัวเอง

1. **Git** — clone repo `dataops-fabric-pilot` จาก **โฟลเดอร์ parent ที่ว่าง**
   ```bash
   cd path/to/empty-parent-folder
   git clone https://github.com/<org>/dataops-fabric-pilot.git
   ```
   ⚠️ **อย่า** `cd` เข้าโฟลเดอร์ที่ตั้งชื่อรอ repo ไว้แล้วก่อน clone — เจอ repo ซ้อนกัน 2 ชั้นมาแล้วจริงระหว่าง pilot
2. **GitHub CLI (`gh`)** — ติดตั้งแล้วรัน `gh auth login` (เลือก GitHub.com → HTTPS → login ผ่าน browser) ใช้เปิด/ดู PR และ Actions run จาก terminal ได้เลยไม่ต้องสลับไปเว็บ
3. **Python 3.11+** — `pip install -r requirements.txt` ใน root ของ `dataops-fabric-pilot`
4. **(เฉพาะถ้าต้องรัน script ที่คุย Fabric API ตรง เช่น `deploy_local.py` แบบ local)** copy `.env.example` → `.env` แล้วใส่ค่า Service Principal จริง (ถามเจ้าของ SP หรือดู GitHub Actions secret ของ repo)
   ⚠️ **ห้ามพิมพ์ secret ลงคำสั่ง shell/chat ตรงๆ เด็ดขาด** ใส่ในไฟล์ `.env` เท่านั้น (ไฟล์นี้ถูก `.gitignore` ไว้แล้ว)

### 3.2 Service Principal (ถ้ายังไม่มี/ต้องตั้งใหม่)

**ทำไมต้องใช้ Service Principal แทน PAT หรือ login ส่วนตัว**: PAT/interactive login ผูกกับ account คนสร้าง — คนออกจากทีมระบบพัง ส่วน SP เป็น identity ขององค์กร ไม่ผูกกับใคร, รันบน GitHub Actions runner ได้จริง (ไม่มีหน้าจอให้ login), จำกัดสิทธิ์ได้ชัดเจน, และ audit log แยกจาก user จริง

ขั้นตอน:

1. **Azure Portal → Microsoft Entra ID → App registrations → New registration** — ตั้งชื่อ เช่น `sp-fabric-cicd-pilot` → **Register**
2. เข้าแอปที่สร้าง → **Certificates & secrets → New client secret** → copy ค่า secret ไว้ทันที (เห็นได้ครั้งเดียว)
3. หน้า **Overview** ของแอป copy **Application (client) ID** และ **Directory (tenant) ID** ไว้
4. **Fabric → Tenant admin settings** (ต้องเป็น admin องค์กร) → เปิด **"Service principals can use Fabric APIs"** — ถ้าจำกัดด้วย security group ต้องเพิ่ม SP เข้ากลุ่มด้วย ไม่ใช่แค่เปิด toggle
5. เข้าแต่ละ workspace (`ws-pilot-dev`/`spl-cicd-dev`, `ws-pilot-target`/`spl-cicd-prd`) → **Manage access → Add people or groups** → ใส่ชื่อแอปที่สร้าง → สิทธิ์ **Contributor**
   ⚠️ **ให้สิทธิ์ SP แค่ staging และ production เท่านั้น — ห้ามให้ SP เขียนเข้า dev workspace** (เหตุผลดู "00 · ภาพรวมระบบ" ด้านล่าง)

โค้ดที่ใช้ SP แทน interactive login (ใน `deploy.py`/`deploy_local.py`):

```python
import os
from azure.identity import ClientSecretCredential

credential = ClientSecretCredential(
    tenant_id=os.environ["FABRIC_TENANT_ID"],
    client_id=os.environ["FABRIC_CLIENT_ID"],
    client_secret=os.environ["FABRIC_CLIENT_SECRET"],
)
```

Checklist:
- [ ] สร้าง App registration (SP) ใน Azure AD
- [ ] สร้าง client secret + เก็บ Client ID, Tenant ID
- [ ] ขอ/รอ IT เปิด "Service principals can use Fabric APIs"
- [ ] ให้สิทธิ์ Contributor แก่ SP ใน staging/production workspace เท่านั้น
- [ ] เก็บ 3 ค่าใน GitHub Secrets (ดู 3.4)
- [ ] ทดสอบ deploy ทั้งจากเครื่อง (`deploy_local.py`) และผ่าน GitHub Actions

### 3.3 Fabric Workspace + Git Integration

1. [app.fabric.microsoft.com](https://app.fabric.microsoft.com) → **Workspaces → + New workspace**
2. ตั้งชื่อ (เช่น `ws-pilot-dev`) → **License mode ต้องเป็น capacity ที่รองรับ Fabric** (Trial/Premium/Fabric capacity) — Git Integration ใช้ไม่ได้กับ Pro license เปล่าๆ → **Apply**
3. ทำซ้ำสำหรับ workspace เป้าหมาย (`ws-pilot-target`/production)
4. **เชื่อม Git Integration**: เข้า workspace → **Workspace settings → Git integration** → เลือก **GitHub** → ใส่ repo URL → เลือก branch (`dev` สำหรับ dev workspace, `main` สำหรับ production) → เลือก root folder (เช่น `/fabric_items`) → **Connect and sync**
   ⚠️ **workspace 2 อันต้องผูกกับ branch คนละตัว ห้ามชี้ไป branch เดียวกัน**

### 3.4 GitHub Secrets / Environments / Branch Protection

**A. GitHub Secrets** (`repo → Settings → Secrets and variables → Actions → New repository secret`) — เพิ่ม 3 ค่า: `FABRIC_CLIENT_ID`, `FABRIC_CLIENT_SECRET`, `FABRIC_TENANT_ID`
⚠️ ต้องอยู่ใน **Secrets** เท่านั้น ห้ามอยู่ใน tab Variables (ค่าจะโชว์เป็น plain text ให้ทุกคนที่อ่าน repo เห็น)

**B. GitHub Environments** (`repo → Settings → Environments`) — สร้าง environment ชื่อ **`production`** เป๊ะ (ต้องตรงกับที่อ้างในไฟล์ workflow) → เปิด **Required reviewers**
⚠️ ไม่มีขั้นนี้ deploy เข้า production จะรันทันทีโดยไม่มีใคร approve

**C. Branch protection** (`repo → Settings → Branches`) — บังคับ PR + อย่างน้อย 1 approve + CI ผ่าน ก่อน merge เข้า `main` (และ `staging` ถ้ามี)
หมายเหตุ: GitHub ไม่ให้ approve PR ของตัวเอง — ถ้าทำงานคนเดียว (solo) ต้องปรับ rule ชั่วคราวหรือหาคนที่สอง และถ้า repo อยู่บน personal free plan บาง rule จะไม่ enforce เต็มรูป (ต้อง GitHub Organization แบบ Team/Enterprise)

**D. ไฟล์ในตัว repo** — `ci-config.yml` (ประกาศ check pattern ต่อ item) + `.github/workflows/fabric-ci.yml` (logic การรัน CI)
⚠️ ชื่อไฟล์ test ต้องตรงกับชื่อ item เป๊ะ (ตัด suffix type ออก) ไม่ตรง CI จะ error ทันที ไม่ปล่อยผ่านเงียบๆ — และ `on.push.branches` ต้องมีทุก branch ที่มี job ผูกเงื่อนไข `if: ref == ...` อยู่จริง (ลืมใส่แล้ว job นั้นจะไม่ทำงานเลยแบบเงียบๆ — เคยเจอมาแล้ว ดู section 7)

### ทดสอบว่าเชื่อมต่อทำงานจริง

| Test | วิธีทำ | เกณฑ์ผ่าน |
|---|---|---|
| A: workspace → Git | สร้าง item เปล่าๆ ใน dev workspace → Source control → Commit | เห็นไฟล์ใหม่ใน GitHub branch `dev` |
| B: Git → workspace | แก้ไฟล์ item ตรงบน GitHub → กลับไป Source control panel → Update | Fabric UI แสดงการเปลี่ยนแปลงที่แก้จาก GitHub |
| C: CI trigger | Push commit เล็กๆ เข้า `dev` | Actions tab เห็น workflow รันขึ้นเอง และ job `test` ผ่าน (เขียว) |
| D: Deploy ข้าม workspace | เพิ่ม deploy step เรียก `fabric-cicd` publish จาก `main` เข้า workspace เป้าหมาย | item ไปโผล่ใน workspace ปลายทางจริง |

---

## Daily Workflow

ลำดับจริงที่ต้องผ่านทุกครั้ง ตั้งแต่แก้โค้ดจนถึงขึ้น production:

1. **แก้งานใน `feature/xxx`** — แก้ Notebook/Pipeline/Lakehouse/Warehouse ฯลฯ **ผ่าน Fabric UI ใน dev workspace เท่านั้น** (ห้าม hand-write ไฟล์ item ตรงเข้า git — logicalId ไม่ตรงของจริง ทำให้ Fabric sync conflict จนกด commit จาก workspace ไม่ได้เลย) + เพิ่ม/แก้ `ci-config.yml` ถ้าเป็น item ใหม่ + เขียน test คู่กัน
2. **Commit ผ่าน Fabric's Source Control panel** → sync เข้า branch `dev` บน GitHub อัตโนมัติ
3. **CI ตรวจสอบอัตโนมัติ (`test` ✅)** — รันตาม check pattern ที่ประกาศไว้ใน `ci-config.yml` ไม่ต้องรู้จัก Fabric item type เอง (ดู section ถัดไป) — ถ้าเป็น item type ใหม่ที่ไม่เคยมีมาก่อนใน repo เช็คตาม [Quick Start เพิ่ม Item ใหม่](#quick-start-เพิ่ม-fabric-item-ใหม่) ก่อน push ไม่งั้น CI จะ fail แบบงงๆ
4. **เปิด PR `dev → main`** → รอ `test` job ผ่าน → Review → Merge
5. **Merge → `deploy-prod` รันอัตโนมัติ** (ผ่าน Service Principal) → **รอ Manual Approval** จาก required reviewer (Actions tab) → deploy เข้า production

> Dev workspace เป็น workspace เดียวที่ **ห้าม** เป็นเป้าหมายของ CI/CD deploy — ให้ dev แก้เองผ่าน Git Integration เท่านั้น มิฉะนั้นจะเกิดสถานะ **Uncommitted** ค้างตลอดเวลา เพราะ Fabric ไม่รู้จักการเขียนที่มาจาก REST API ว่ามาจาก git จริง

---

## CI Design: Pattern-Based Check

**หลักการ**: Fabric มี item type เป็นสิบๆ ตัว (Notebook, Dataflow, DataPipeline, Lakehouse, Warehouse, KQL Database, Eventstream, ...) และเพิ่มเรื่อยๆ — เขียน CI แบบ `if/elif` ตาม Fabric type ตรงๆ ไม่ scale ได้ **แทนที่จะให้ workflow รู้จัก Fabric type เอง ให้ `ci-config.yml` แม็ป item ไปหา "check pattern" ที่มีอยู่แค่ ~5 แบบคงที่**

| Check Pattern | ใช้กับ item ลักษณะไหน |
|---|---|
| `unit_test` | มีโค้ด/logic จริงให้ test (เช่น Notebook, Spark Job Definition) |
| `data_quality` | Low-code/visual ไม่มีโค้ดให้ unit test ต้องรันจริงแล้วเช็ค output (เช่น Dataflow Gen2) |
| `structure` | เป็น config/orchestration เช็คแค่โครงสร้าง (เช่น DataPipeline) |
| `schema` | เป็น storage เช็ค schema ตรง contract ไหม (เช่น Lakehouse, Warehouse, KQL Database) |
| `none` | ยังไม่มี automated check ที่เหมาะ — ต้องประกาศไว้ชัดเจนว่า "ตั้งใจข้าม" ไม่ใช่ลืม |

**ทำไม scale ได้จริง**: Fabric เพิ่ม item type ใหม่ → แค่เพิ่ม entry ใน `ci-config.yml` แม็ปไป pattern ที่มีอยู่แล้ว **ไม่ต้องแตะ `fabric-ci.yml` เลย** — engineering effort ผูกกับจำนวน pattern (คงที่) ไม่ใช่จำนวน item type ของ Fabric (เพิ่มเรื่อยๆ)

### `ci-config.yml` — ตัวอย่างจริง

```yaml
# check ที่รองรับ: unit_test | data_quality | structure | schema | none
# ไม่ระบุ = default เป็น unit_test เสมอ (fail-safe เข้มสุด)

# _defaults ต่อ fabric_type — ลด boilerplate: item ที่ check pattern ตรงกับ
# default ของ type ตัวเอง ไม่ต้องเขียน entry เลย
_defaults:
  Notebook: unit_test
  DataPipeline: structure
  Lakehouse: schema
  Warehouse: schema

nb_sales_transform:
  fabric_type: Notebook
  check: unit_test

df_customer_ingest:
  fabric_type: Dataflow
  check: data_quality

pl_legacy_pipeline:
  fabric_type: DataPipeline
  check: structure
  skip_check: true
  skip_reason: "กำลัง deprecate ไม่คุ้มเขียน validation ใหม่ — จะลบ item นี้ใน Q3"

rpt_sales_dashboard:
  fabric_type: Report
  check: none    # <- ประกาศชัดว่า "ยังไม่มี check ที่เหมาะ" ไม่ใช่ลืมทำ
```

ลำดับ resolve check pattern ของแต่ละ item: **item override → `_defaults.<type>` → `unit_test` (fail-safe เข้มสุด)**

**Opt-out รายตัว** (`skip_check: true` + `skip_reason` บังคับ) ใช้ได้กับทุก pattern รวม `structure`/`schema` — ต่างจาก `check: none` ตรงที่ยัง label ไว้ว่า item นี้ "ควรจะ" เช็คแบบไหน (เผื่อกลับมาเปิดทีหลัง) ส่วน `check: none` คือไม่มี check ที่คาดหวังเลย — **skip ที่ไม่มี `skip_reason` ต้อง fail CI เสมอ ไม่ปล่อยผ่านเงียบๆ**

### Job Summary — รู้ได้ทันทีว่า item ไหนเช็คอะไรไปบ้าง

CI สร้างตารางสรุปอัตโนมัติผ่าน `$GITHUB_STEP_SUMMARY` ทุกครั้งที่รัน (แม้ step ก่อนหน้า fail ก็ยังสรุปให้เห็น):

```
| Item                | Fabric Type  | Check Pattern | Status |
|---------------------|--------------|----------------|--------|
| nb_sales_transform   | Notebook     | unit_test      | ✅     |
| df_customer_ingest   | Dataflow     | data_quality   | ✅     |
| rpt_sales_dashboard  | Report       | none           | ⏭️ skipped (intentional) |
```

Reviewer เปิด Actions run เห็นภาพรวมทันทีว่า item ไหนเช็คอะไรและผ่านไหม ไม่ต้องเปิด `ci-config.yml` เอง — ถ้าเห็น `❌ missing` หรือ `⚠️ unknown pattern` รู้ทันทีว่าต้องแก้ก่อน approve

---

## Quick Start: เพิ่ม Fabric Item ใหม่

```
1. สร้าง/แก้ item ผ่าน Fabric UI (Dev workspace) เท่านั้น
2. Source Control → Commit → Push (เข้า branch dev)
3. Pull มา local
4. ถ้า check pattern ตรงกับ _defaults ของ type อยู่แล้ว → ไม่ต้องแก้ ci-config.yml
   ถ้าต้องการ pattern อื่น หรือ skip_check → เพิ่ม entry ใน ci-config.yml
5. ถ้า check: unit_test → เขียน tests/unit/test_<item_name>.py
6. รัน pytest local ให้ผ่านก่อน push
7. Push feature branch → เปิด PR → รอ CI → Review → Merge เข้า main
8. Approve deploy-prod ใน Actions tab
```

### ถ้าเป็น Fabric item type ที่ไม่เคยมีในระบบเลย (เช่น Warehouse, Eventhouse ครั้งแรก) — เช็คให้ครบ 4 ข้อนี้

เจอปัญหาซ้ำมาแล้วหลายรอบ (เช่น Warehouse) เพราะลืมข้อใดข้อหนึ่งด้านล่าง:

1. **`scripts/deploy.py`/`deploy_local.py`'s `item_type_in_scope`** — เช็คว่า type ใหม่รวมอยู่ในนี้แล้ว (ปกติครอบคลุมครบทุก type ที่ `fabric-cicd` เวอร์ชันที่ติดตั้งจริงรองรับ — sync จาก `fabric_cicd.constants.ItemType` ถ้า library อัปเดตแล้วมี type เพิ่ม)
2. **`ci-config.yml`'s `_defaults.<fabric_type>`** — **ต้องเพิ่มเสมอ** ไม่งั้น item ประเภทนั้นจะ fallback ไปที่ `unit_test` แล้ว CI fail ทันทีเพราะหา `tests/unit/test_<name>.py` ไม่เจอ
3. **เช็ค validator ที่ผูกกับ pattern ที่เลือก (`structure`/`schema`) ว่าเข้าใจ format ไฟล์ของ item type นั้นจริงไหม** — ถ้าไม่มั่นใจ ใช้ `skip_check: true` + เหตุผลไปก่อน อย่าปล่อยให้ CI "ผ่าน" แบบหลอกๆ ทั้งที่ validator ไม่ได้เช็คอะไรจริง
4. **เช็ค `parameter.yml`** — item ใหม่ฝัง GUID ของ dev workspace ไว้ใน content ไหม (เช่น Notebook ที่ attach Lakehouse) ถ้าใช่ต้อง remap ข้าม environment ด้วย `$items.<type>.<name>.$id`/`$workspace.$id` — ระวัง GUID บางที่เก็บเป็น **byte-swapped form** (คนละ representation จาก canonical GUID ที่เห็นใน URL) ต้อง grep หาใน raw file จริงเสมอ อย่าเดา

---

## ปรับ Item และ Config ให้ Deploy ได้

`scripts/deploy.py` (publish ด้วย `fabric-cicd`), `deploy_endpoints.py` และ `deploy_local.py` publish ทุก item ใต้ `fabric_items/` เข้า workspace ของ environment ที่ระบุ (`--workspace`, `--environment`) แล้วลบ item ที่หายไปจาก repo ผลลัพธ์จะถูกต้องก็ต่อเมื่อ item และ config ตรงตามหัวข้อนี้ — ใช้ตอน onboard โปรเจกต์ใหม่ หรือเอา item เดิมเข้า CI/CD ครั้งแรก

### ไฟล์และค่าที่ต้องตั้งต่อโปรเจกต์

| ไฟล์/ที่ตั้งค่า | ต้องใส่อะไร | ใครอ่านค่านี้ |
|---|---|---|
| `workspace-config.yml` | workspace GUID ของ `dev` / `staging` / `prod` (ดูจาก URL `.../groups/<GUID>/...`) — ไม่ใช่ secret commit ได้ | CI jobs, `deploy_local.py`, live DQ gate |
| GitHub Secrets | `FABRIC_CLIENT_ID`, `FABRIC_CLIENT_SECRET`, `FABRIC_TENANT_ID` ของ Service Principal | ทุก job ที่ deploy หรือรัน DQ |
| GitHub Environment `production` | Required reviewers + deployment branch = `main` | job `deploy-prod` |
| `fabric_items/` | item ที่ sync จาก Fabric Git Integration โครงสร้าง `<ชื่อ>.<Type>/` — ห้ามมี `__pycache__`/`.pyc` ในโฟลเดอร์ item | `deploy.py` |
| `fabric_items/parameter.yml` | rule remap GUID/ค่าที่ต่างกันต่อ environment (ดูด้านล่าง) | `fabric-cicd` ตอน publish |
| `ci-config.yml` | `_defaults` ต่อ item type + entry override หรือ `skip_check` + `skip_reason` | job `test` |
| `endpoint-targets.yml` | item ที่ deploy ไป workspace อื่น: `item_path`, `repo_dir`, `targets` (dev/staging/prod → GUID) | `deploy_endpoints.py` |
| `dq-gates.yml` | live DQ gate: ชื่อ item, `item_type` (notebook/pipeline), `stages` | `run_live_dq_stage.py` |
| `.env` (เฉพาะรันบนเครื่อง) | `FABRIC_TENANT_ID` / `FABRIC_CLIENT_ID` / `FABRIC_CLIENT_SECRET` — ห้าม commit | `deploy.py` ตอนทดสอบ local |

> **staging**: repo ที่สร้างจาก `ci-cd-template` อ่าน workspace ID ของ staging จาก `workspace-config.yml` (key `staging`) ส่วน pilot repo เดิมเปิดใช้ staging ด้วย repo variable `STAGING_WORKSPACE_ID` — เช็ค `.github/workflows/fabric-ci.yml` ของ repo ที่ใช้อยู่ก่อนตั้งค่า

### สิทธิ์ที่ต้องมี

- Service Principal เป็น **Contributor** บน workspace staging และ prod (รวม endpoint workspace ของแต่ละ environment ถ้ามี)
- **ไม่ให้สิทธิ์ SP บน dev workspace** — dev แก้โดยคนผ่าน Fabric UI เท่านั้น
- Fabric admin เปิด tenant setting "Service principals can use Fabric APIs"
- item ใหม่ที่ deploy จะมี SP เป็น owner ส่วน item ที่มีอยู่แล้วจะถูก update เนื้อหา โดย owner เดิมไม่เปลี่ยน
- คนที่รัน `deploy_local.py` ต้องมีสิทธิ์บน Connection ที่ item อ้างอิง (ใช้เมื่อ SP ไม่มีสิทธิ์เท่านั้น)

### ปรับ item และ `parameter.yml` ตามสถานการณ์

| สถานการณ์ใน item | อาการถ้าไม่ปรับ | สิ่งที่ต้องทำ |
|---|---|---|
| Notebook attach Lakehouse (workspace เดียวกับที่ deploy) | รันผ่านแต่เขียนข้อมูลผิดที่ (ยังชี้ Lakehouse ของ Dev) | เพิ่ม 2 rule (ตัวอย่างด้านล่าง) หรือรัน `generate_parameter.py --dry-run` แล้วตรวจ |
| Notebook/pipeline อ้าง Lakehouse ต่าง workspace | `$items.<type>.<name>.$id` หา item ไม่เจอ เพราะมองได้เฉพาะ workspace ที่ deploy อยู่ | เขียน rule คู่ GUID dev → แต่ละ environment เอง ใช้ key เฉพาะ `staging`/`prod` (ห้าม `_ALL_`) + ลงทะเบียนใน `endpoint-targets.yml`; ถ้าเลี่ยงได้ให้ notebook หา item จากชื่อตอนรัน |
| DataPipeline มี Copy Activity ที่ใช้ Lakehouse/Warehouse | `deploy-prod` fail: `User does not have access to the connection` | เปลี่ยนเป็น **Notebook Activity** (Spark/T-SQL ใน workspace เดียวกัน) ไม่ต้องพึ่ง Connection |
| DataPipeline มี `externalReferences.connection` (Connection ภายนอกจริง) | ไม่มีชื่อกำกับ resolve อัตโนมัติไม่ได้ | กรอก Connection ID ต่อ environment เองใน `parameter.yml` — `generate_parameter.py` จะเตือนให้ ไม่เดาให้ |
| GUID รูปแบบ "สลับ" ในไฟล์ pipeline | ดูเหมือนต้องเขียน rule | เทียบกับ `logicalId` ใน `.platform` ก่อน — ถ้าตรงกัน `fabric-cicd` แทนให้เอง ไม่ต้องเขียน rule |
| Lakehouse / Warehouse | `ci-config.yml` default = `schema` ถ้าไม่มี contract CI fail; item พวกนี้ไม่ถูกลบอัตโนมัติ | สร้าง `tests/schema/<ชื่อ>.yml` ตามแม่แบบ; ลบเองใน workspace เมื่อไม่ใช้แล้ว |
| item type ใหม่ (Dataflow, Eventstream ฯลฯ) | fallback เป็น `unit_test` แล้ว CI fail | เพิ่ม `_defaults.<type>` ใน `ci-config.yml` หรือ `skip_check` + `skip_reason` ไปก่อน |

**ตัวอย่าง `parameter.yml` — Notebook attach Lakehouse ใน workspace เดียวกัน**

```yaml
find_replace:
  - find_value: "<LAKEHOUSE_GUID_ของ_DEV>"
    replace_value:
      _ALL_: "$items.Lakehouse.<ชื่อ_lakehouse>.$id"
    item_type: "Notebook"
  - find_value: "<WORKSPACE_GUID_ของ_DEV>"
    replace_value:
      _ALL_: "$workspace.$id"
    item_type: "Notebook"
```

**ตัวอย่าง `parameter.yml` — Lakehouse อยู่คนละ workspace (ต้องระบุค่าต่อ environment เอง)**

```yaml
  - find_value: "<LAKEHOUSE_GUID_ของ_ENDPOINT_DEV>"
    replace_value:
      staging: "<LAKEHOUSE_GUID_ของ_ENDPOINT_STAGING>"
      prod: "<LAKEHOUSE_GUID_ของ_ENDPOINT_PROD>"
    item_type: "Notebook"
    item_name: "<ชื่อ_notebook>"
```

**ตัวอย่าง `endpoint-targets.yml` — เพิ่ม endpoint ใหม่ด้วย config อย่างเดียว ไม่แก้ workflow**

```yaml
lh_endpoint_example:
  item_path: lh_endpoint_example.Lakehouse
  repo_dir: fabric_items_endpoint
  targets:
    staging: "<WORKSPACE_ID_ENDPOINT_STAGING>"
    prod: "<WORKSPACE_ID_ENDPOINT_PROD>"
```

**Notebook ที่อ้าง Lakehouse ข้าม workspace — ใน notebook เองต้องทำอะไร**

หลักการ: **ไม่ต้องแก้ notebook ให้เป็นค่าของ prod/staging** — ให้ notebook เก็บค่าของ Dev ไว้ตามที่ Fabric UI สร้าง แล้วให้ `parameter.yml` สลับเป็นค่าของแต่ละ environment ตอน deploy (ผลทดสอบ endpoint: ไม่ว่าจะเขียน path ในโค้ดเอง หรือกด Add data item attach ผ่าน UI ก็ต้องมี rule ใน `parameter.yml` เหมือนกันทั้งคู่)

| วิธีที่ notebook อ้างถึง Lakehouse | ใน notebook | ใน `parameter.yml` |
|---|---|---|
| attach ผ่าน UI (Add data item / default lakehouse) | ไม่ต้องแก้อะไร — Fabric ฝัง GUID ของ Dev ไว้ใน METADATA ให้เอง | rule `find_value` = GUID Lakehouse/workspace ของ Dev; ข้าม workspace ระบุค่า `staging`/`prod` เอง |
| เขียน `abfss://<workspace>@onelake.dfs.fabric.microsoft.com/<lakehouse>/...` ในโค้ด | ใช้ GUID ของ Dev เป็น string ตัวอักษรตรงๆ (literal) และให้ตรงกับ `find_value` ทุกตัวอักษร | rule เดียวกัน — `fabric-cicd` ค้นหา string ทั้งไฟล์ item แล้วแทนที่ทุกจุดที่เจอ |

สิ่งที่ต้องระวังใน notebook:
- ห้ามประกอบ GUID จาก string หลายท่อน หรือสร้างขึ้นตอนรัน เพราะ `find_replace` หาเจอเฉพาะ string ที่ปรากฏเป็นข้อความตรงๆ ในไฟล์
- ถ้า GUID ของ Dev ปรากฏหลายที่ ไม่ต้องแยก rule — 1 `find_value` แทนที่ให้ทุกจุด แต่ถ้ามี Lakehouse หลายตัวต้องมี rule ต่อ GUID ที่ไม่ซ้ำกัน
- ถ้า Lakehouse ปลายทางถูกสร้างใหม่ (GUID เปลี่ยน) ต้องเพิ่ม rule ของ GUID ใหม่ — อย่าลบ rule เดิมจนกว่าจะไม่มีไฟล์ไหนใช้ค่าเดิม
- ไม่ต้องใส่ `item_name` ถ้าอยากให้ rule ครอบคลุมทุก Notebook; ใส่เมื่อค่านั้นใช้เฉพาะ notebook ตัวนั้น
- ทางเลือกที่ไม่ต้องมี rule ต่อ environment คือให้ notebook หา Lakehouse จากชื่อตอนรัน (**ยังไม่ได้ทดสอบใน pilot** — ทดสอบก่อนใช้จริง)
- หลัง deploy ตรวจเสมอว่าข้อมูลเขียนไป Lakehouse ของ environment นั้นจริง (`verify_deployed_guids.py` + ดู path ของตารางปลายทาง)

**กฎของ `parameter.yml` ที่พลาดบ่อย**

- `replace_value` ต้องเป็น dictionary เสมอ; ถ้าใช้ key `_ALL_` ต้องเป็น key เดียวในนั้น (ผสมกับ `staging`/`prod` จะ validation fail)
- key ของ environment ต้องเป็น `dev` / `staging` / `prod` เท่านั้น — พิมพ์ผิด `fabric-cicd` จะข้าม rule นั้นเงียบๆ โดยไม่ error
- อย่าลบหรือแก้ `find_value` เดิม จนกว่าไฟล์ item ทุกตัวจะไม่มีค่านั้นแล้ว; ถ้า item ถูกสร้างใหม่ (id เปลี่ยน) ต้องเพิ่ม rule ของ id ใหม่ก่อน sync เข้า git
- GUID ที่ hardcode ข้าม workspace พังทุกครั้งที่ item ถูกสร้างใหม่

### ลำดับการแก้และคำสั่งตรวจก่อน push

1. audit item เดิมเทียบกฎด้านบน แล้วแก้ item ที่ผิด (แก้ผ่าน Fabric UI แล้ว commit จาก workspace)
2. รัน `python scripts/generate_ci_config.py` สร้าง entry ใน `ci-config.yml` แล้วเติม test หรือ `skip_check`
3. รัน `python scripts/generate_parameter.py --dry-run` ดูผล แล้วรันจริงและเติม rule ที่สคริปต์เตือน (Connection, ข้าม workspace)
4. ตรวจ `parameter.yml` แบบ offline (ไม่ต้องมี credential):
   ```bash
   python scripts/debug_parameterization.py --environment staging
   ```
5. รัน `pytest` ในเครื่องให้ผ่านก่อน push
6. ทดสอบ deploy ด้วย `.env` ของตัวเอง (ตัวอย่าง: item ปกติ และ endpoint ที่ scope ทีละ item):
   ```bash
   python scripts/deploy.py --workspace <WORKSPACE_ID> --environment staging

   python scripts/deploy.py --workspace <ENDPOINT_WORKSPACE_ID> --environment prod \
     --repo-dir fabric_items_endpoint --items-path lh_endpoint_example.Lakehouse
   ```
7. หลัง deploy ไป prod ทุกครั้งรัน `python scripts/verify_deployed_guids.py` — PASS ไม่ได้พิสูจน์ว่าชี้ถูกที่ ต้องดูรายการ INFO ด้วย

> `--items-path` ทำให้ `deploy.py` ข้าม `unpublish_all_orphan_items()` เพราะ scoped dir มีแค่ item เดียว ถ้าไม่ใส่จะลบ item ที่หายจาก repo ออกจาก workspace (soft delete) ส่วน Lakehouse/Warehouse/SQL Database ไม่ถูกลบโดยดีฟอลต์ (กันข้อมูลหาย)

---

## เจอปัญหา ทำยังไง (Troubleshooting)

| ปัญหา | สาเหตุ | วิธีแก้ |
|---|---|---|
| 🔴 `deploy-prod` fail ด้วย `User does not have access to the connection used in the Pipeline` | **Known issue** — Copy Activity ที่ sink/source เป็น Fabric-native storage (Lakehouse **หรือ** Warehouse) ต้องพึ่ง Connection ที่ Authentication kind ไม่มีตัวเลือก Service Principal เลย (มีแค่ user OAuth) — SP ที่ deploy จึงไม่มีสิทธิ์บน connection นั้นเสมอ | ดู runbook เต็มด้านล่าง — สรุปสั้นๆ: รัน `python scripts/deploy_local.py --environment prod` จากเครื่องคนที่มีสิทธิ์บน connection (login ผ่าน browser ด้วยบัญชีตัวเอง) เป็น fallback |
| 🔴 deploy fail ด้วย "empty payload" หลัง publish | รัน pytest แล้ว import notebook ตรงๆ ทำให้เกิด `.pyc`/`__pycache__` ข้างในโฟลเดอร์ item — fabric-cicd ส่งทุกไฟล์ที่เจอเป็น definition part | ล้าง `__pycache__` ใน `deploy.py` ก่อน publish ทุกครั้ง (มีอยู่แล้วใน `_clean_pycache()`) — เช็ค `.gitignore` ก่อน commit ทุกครั้งด้วย เพราะหลุดเข้า repo เป็นระยะ |
| 🔴 pytest fail ด้วย `NameError: name 'spark' is not defined` | Notebook cell เรียก `spark` ตรงๆ ตอน import — `spark` มีแค่ใน runtime ของ Fabric จริง ไม่มีตอน pytest import ทั้งไฟล์ | ห่อ driver cell ด้วย `if __name__ == "__main__":` |
| 🔴 CI fail เพราะ item ใหม่ไม่มี check pattern / หา test ไม่เจอ | ลืมเพิ่ม entry ใน `ci-config.yml` หรือ `_defaults.<type>` (โดยเฉพาะ item type ที่ไม่เคยมีมาก่อน เช่น Warehouse) | ดู [Quick Start เพิ่ม Item ใหม่](#quick-start-เพิ่ม-fabric-item-ใหม่) เช็คให้ครบ 4 ข้อ |
| 🔴 Auto-deploy ทับ production โดยไม่มี approval | สลับ workspace ID ระหว่าง dev/production เพราะเข้าใจผิดว่า GUID ไหนคือ environment ไหน | จดบันทึกและตรวจสอบ workspace ID คู่กับ environment ให้ชัดเจนตั้งแต่ต้น (ดูตารางใน "สถานะจริงตอนนี้") อย่าจำจากบริบทเฉยๆ |
| 🔴 ข้อมูลไปโผล่ผิด workspace/Lakehouse โดยไม่มี error | ยังไม่ได้ remap GUID ของ Dev ใน item หรือ environment key ใน `parameter.yml` พิมพ์ผิด (`fabric-cicd` ข้าม rule เงียบๆ) | เพิ่ม/แก้ rule ตาม [ปรับ Item และ Config ให้ Deploy ได้](#ปรับ-item-และ-config-ให้-deploy-ได้) แล้วรัน `verify_deployed_guids.py` |
| 🟡 item ที่ลบจาก repo ยังอยู่ใน workspace | Lakehouse/Warehouse/SQL Database ไม่ถูก unpublish โดยดีฟอลต์ (กันข้อมูลหาย) หรือ deploy แบบ `--items-path` (ข้าม unpublish) | ลบเองใน workspace ถ้าแน่ใจ |
| 🟡 log แดง `Item name ... not found in the repository directory` | rule ของ item อื่นใน `parameter.yml` ตอน deploy แบบ scoped | `deploy.py` กรอง rule ให้แล้ว ไม่กระทบผลจริง |
| 🟡 Notebook ใน Fabric ยังเป็นโค้ดเก่าหลัง merge | Git Integration ไม่ sync กลับเข้า workspace อัตโนมัติ | กด **Update all** ใน Source Control ของ workspace |
| 🟡 Merge เข้า `main` กี่ครั้งก็ไม่มี workflow run เกิดขึ้นเลย | `on.push.branches` ใน workflow ไม่มี `main` ทั้งที่ job `deploy-prod` เช็คเงื่อนไข `event_name == 'push' && ref == main` | เช็คว่าทุก branch ที่มีเงื่อนไข `if: ref==...` อยู่ใน trigger list จริง |
| 🟡 Dev workspace ค้างสถานะ "Uncommitted" ตลอดเวลา | Dev workspace เล่น 2 บทบาท — ทั้งให้คนแก้ผ่าน UI และเป็นเป้าหมาย CI/CD deploy พร้อมกัน Fabric ไม่รู้จักการเขียนจาก REST API ว่ามาจาก git จริง | ห้าม CI/CD deploy เข้า dev workspace เด็ดขาด — dev แก้ผ่าน Git Integration ของมันเองเท่านั้น |
| Git integration กด Connect ไม่ได้ | Workspace license ไม่รองรับ (ต้องเป็น Fabric capacity ไม่ใช่ Pro เปล่า) | เปลี่ยน capacity ของ workspace |
| SP เข้า workspace ไม่ได้ | ยังไม่เปิด "Service principals can use Fabric APIs" หรือยังไม่ได้เพิ่มสิทธิ์ Contributor | ทำตาม [3.2](#32-service-principal-ถ้ายังไม่มีต้องตั้งใหม่) |
| Commit จาก workspace ไม่ขึ้นใน GitHub | เช็ค branch ที่ workspace ผูกไว้ตรงกับ branch ที่ไปดูหรือไม่ | เช็คใน Workspace settings → Git integration |
| Deploy approval prompt หาไม่เจอในหน้า PR ที่ merge ไปแล้ว | กล่อง "checks passed" ใต้ merge commit โชว์แค่ checks จาก `pull_request` event (ก่อน merge) — deploy-prod เป็น `push` event แยกต่างหาก | เข้า **Actions tab** หา workflow run ที่ trigger จาก push event ของ merge commit โดยตรง ไม่ใช่หาใน PR page |

### Runbook เต็ม: `deploy-prod` fail ด้วย connection-permission error

deploy.py จะพิมพ์ `::error::` เตือนให้อัตโนมัติถ้าเจอ error class นี้ (ไม่ silent):

1. เช็คว่า error message มีคำว่า `User does not have access to the connection` ไหม (ถ้าใช่ = known issue นี้ คนละแบบกับโค้ด/definition ผิด)
2. เช็คว่า `test` job (ก่อน `deploy-prod`) ผ่านไปแล้วหรือยัง — ถ้าผ่านแล้วแปลว่าโค้ด/definition ถูกต้อง ปลอดภัยที่จะใช้ fallback ด้านล่างได้เลย ไม่ต้องรอแก้โค้ดก่อน
3. คนที่มีสิทธิ์บน connection ที่ item นั้นอ้างอิง (ปกติคือคนที่สร้าง connection เอง) รัน:
   ```bash
   python scripts/deploy_local.py --environment prod
   ```
   (เปิด browser ให้ login ด้วยบัญชีตัวเอง แทน Service Principal — ไม่ต้องพิมพ์ workspace GUID เอง สคริปต์ resolve ให้อัตโนมัติจาก `--environment`)
4. รู้ไว้ก่อนรัน: item ที่ยังไม่เคยมีอยู่ใน target workspace เลยจะถูก**สร้างใหม่** (owner = คนที่รัน) ส่วน item ที่มีอยู่แล้วจะแค่**update เนื้อหา** (owner เดิมไม่เปลี่ยน)
5. วิธีนี้ **ข้าม PR review ของรอบนั้นไปเลย** (push ตรงจากเครื่อง ไม่ผ่าน git) — แจ้งทีมใน PR/channel ว่าทำ manual deploy ไปแล้ว เพราะไม่มี audit trail อัตโนมัติเหมือน merge ปกติ

> **ข้อควรระวัง**: นี่คือ fallback ใช้ครั้งคราวเท่านั้น ไม่ใช่ทางหลัก — ถ้าต้องใช้บ่อยแปลว่าถึงเวลาแก้ที่ต้นตอจริงจัง เช่น ขอสิทธิ์ `Tenant.ReadWrite.All` ให้ SP เพื่อทำ [Assign Item Identity](https://learn.microsoft.com/en-us/rest/api/fabric/articles/item-management/tutorial-associate-item-identity-spn) (สิทธิ์นี้กว้างระดับทั้ง tenant ต้องผ่าน IT/security review ก่อน — ยังไม่ทดสอบจริง) หรือเปลี่ยนไปใช้ **Notebook Activity** (Spark/T-SQL อ่าน-เขียนภายใน workspace เดียวกัน) แทน **Copy Activity** ตั้งแต่ต้น — วิธีนี้ยืนยันแล้วว่าใช้ได้จริงและไม่ชนปัญหา connection permission เลย เพราะไม่ต้องพึ่ง Connection object ใดๆ (ใช้ได้กับทั้ง Lakehouse-to-Lakehouse และ Warehouse sink) ทางเลือกอื่นสำหรับกรณี "แค่ต้องการอ้างอิงข้อมูล ไม่ต้อง transform" คือ **OneLake Shortcuts** — ง่ายกว่า ไม่ต้องเขียนโค้ด Spark และไม่ชนปัญหา connection เลย แต่ไม่เหมาะถ้าต้องมี ETL logic จริง

---

## Data Rollback vs Code Rollback

> ⚠️ **Git เก็บแค่ definition ของ item (โค้ด/config) ไม่ได้เก็บ data จริงในตาราง** — revert commit + redeploy item เก่า **ไม่ทำให้ข้อมูลที่ pipeline เวอร์ชันใหม่เขียนไปแล้วกลับเป็นเดิมอัตโนมัติ**

```
revert commit → redeploy item เวอร์ชันเก่า
   → โค้ด/pipeline กลับเป็นเดิม ✅
   → ข้อมูลที่เวอร์ชันใหม่เขียนไปแล้วในตาราง ยังคงอยู่เหมือนเดิม ❌
```

ต้องมีแผนจัดการข้อมูลแยกต่างหาก **ควบคู่กับ** code rollback เสมอ

### เครื่องมือหลัก — Delta Lake Time Travel / Restore

Lakehouse table ใน Fabric เป็น **Delta table** โดย default — ทุก insert/update/delete/overwrite ไม่เขียนทับของเดิม แต่สร้าง version ใหม่ log ไว้ ทำให้ย้อนดู/ย้อนคืนได้โดยไม่ต้องมี backup แยก

```sql
-- 1. เช็คประวัติ version ก่อนเสมอ อย่าเดา
DESCRIBE HISTORY lh_sales_raw.sales_by_region;

-- 2. ดูข้อมูลของ version เก่า (read-only ไม่กระทบตารางปัจจุบัน)
SELECT * FROM lh_sales_raw.sales_by_region VERSION AS OF 12;

-- 3. ย้อนตารางกลับเป็น version เก่าจริง (เปลี่ยน current state)
RESTORE TABLE lh_sales_raw.sales_by_region TO VERSION AS OF 12;
```

`SELECT ... VERSION AS OF` = ดูเฉยๆ ไม่เปลี่ยนอะไร — `RESTORE TABLE` = สั่งย้อนจริง version เก่ากลายเป็น current state ทันที

⚠️ **จุดพลาดที่เจอจริงระหว่างทดสอบ**: version **นับจาก 0 และเรียงตามเวลาที่เขียน** — ไม่ใช่ "เลขน้อยกว่า = ถูกต้องกว่าเสมอ" (รอบทดสอบจริงเคยเลือกผิด version เพราะสัญชาตญาณเดาแบบนั้น) **ต้องรัน `DESCRIBE HISTORY` เช็คเสมอ ห้ามเดาเลข version**

**ข้อจำกัด**: ย้อนได้แค่ในช่วง retention period เท่านั้น (`delta.logRetentionDuration`, default 30 วัน — เช็คค่าจริงของแต่ละตารางเอง) ถ้ามีคนรัน `VACUUM` ไปแล้วจะย้อนไม่ได้อีก และใช้ได้กับ **Lakehouse table เท่านั้น** — ไม่ครอบคลุม Warehouse, KQL Database, หรือข้อมูลที่ export ออกไปนอก Fabric แล้ว (เช่น Power BI import mode ที่ cache ไว้)

### Decision Tree

```
พบว่า pipeline เวอร์ชันใหม่มีบั๊ก
        │
        ▼
เคยรันจริงและเขียนข้อมูลไปแล้วหรือยัง?
   ยัง → Code rollback พอ ไม่ต้องทำอะไรกับ data
   เคยรันแล้ว → เช็คว่าอยู่ในช่วง retention ของ Delta log ไหม (DESCRIBE HISTORY)
        อยู่ในช่วง        → RESTORE TABLE กลับ version ก่อนบั๊ก + code rollback
        เกินช่วง retention → รัน backfill (re-ingest จากต้นทางใหม่ หรือกู้จาก backup ภายนอกถ้ามี)
                              → ไม่มีทางกู้คืนได้ 100% เป๊ะ ต้องแจ้ง stakeholder ว่าข้อมูลช่วงไหนไม่แม่นยำ
        │
        ▼
มี downstream ที่ query ต่อจากตารางนี้ไหม (dashboard, model, pipeline อื่น)?
   มี → แจ้งเจ้าของ downstream ให้ refresh/re-validate (Power BI import mode อาจ cache ค่าเก่าค้างไว้)
```

### Runbook เมื่อเกิดเหตุจริง

1. **หยุด pipeline ที่เกี่ยวข้องก่อน** (pause/disable trigger) กันรันซ้ำทับข้อมูลที่กำลังกู้คืน
2. **Code rollback**: revert commit บน `main` → ให้ `deploy-prod` deploy item เวอร์ชันเก่ากลับเข้า production
3. **เช็คตารางที่ได้รับผลกระทบทุกตัว** ด้วย `DESCRIBE HISTORY` — บันทึก version/timestamp ก่อนเวลาที่บั๊กเริ่มรัน
4. **ตัดสินใจตาม decision tree** — restore หรือ backfill
5. **Restore/backfill ทีละตาราง เริ่มจากต้นน้ำ (bronze) ไล่ไปปลายน้ำ (silver → gold)** — ถ้าสลับลำดับข้อมูลจะไม่ตรงกัน
6. **ตรวจสอบ row count / spot-check ค่าสำคัญ** หลัง restore ก่อนเปิด pipeline ให้รันต่อ
7. **แจ้ง downstream owner** ให้ refresh/re-validate
8. **เปิด pipeline กลับให้รันตามปกติ**
9. **บันทึก incident** — root cause, ตารางที่กระทบ, วิธีกู้คืนที่ใช้จริง

**ป้องกันไว้ก่อน**: เขียน notebook แบบ **idempotent** (`MERGE`/`overwrite` แทน `append` เปล่าๆ), ตั้ง retention ของตารางสำคัญให้ยาวกว่า default, **ห้ามรัน `VACUUM` มือเปล่าโดยไม่เช็คก่อน** (ลบไฟล์เก่าที่ time travel/restore ต้องใช้ทิ้งถาวร)

**เครื่องมือช่วย**: `draft-rollback_helper.py` (root ของ repo นี้) เป็นดราฟต์เนื้อหาสำหรับ Fabric Notebook ที่ช่วย automate ขั้นตอน 3 และ 5 — ดึง `DESCRIBE HISTORY` ให้เอง, auto เลือก version ก่อนหน้า current 1 ก้าวถ้าไม่รู้เลขที่ต้องการ, รัน `RESTORE TABLE` จริง, เขียน log ลงตาราง `rollback_incident_log` อัตโนมัติ — ยังเป็น draft ไฟล์ `.py` เฉยๆ ต้อง copy โค้ดแต่ละ cell ไปสร้างเป็น Notebook จริงผ่าน Fabric UI ก่อนใช้งาน (ตามกฎ UI-first — ห้าม hand-write item ไฟล์ตรงเข้า git) จุดที่ตั้งใจให้เป็น manual: พิมพ์ชื่อตารางซ้ำเพื่อยืนยันก่อน restore และเลือก `target_version` เจาะจงเอง — กันมือลั่น restore ผิดตาราง/ผิด version

✅ **ทดสอบจริงแล้ว** (2026-08-28, ใน `ws-pilot-dev`): เขียนข้อมูลผิด (v1, คูณ 10) ทับของถูก (v0) → `DESCRIBE HISTORY` เห็น 2 version → `RESTORE TABLE ... VERSION AS OF 0` กู้คืนสำเร็จ ค่ากลับมาตรงเป๊ะ — ยืนยันว่า mechanism ใช้งานได้จริง 100%

---

## Repo Structure อ้างอิง

```
dataops-fabric-pilot/
├── .github/
│   ├── workflows/fabric-ci.yml        ← CI logic: อ่าน ci-config.yml, รันเช็คตาม pattern
│   └── PULL_REQUEST_TEMPLATE.md       ← checklist ที่โผล่อัตโนมัติทุกครั้งที่เปิด PR
│
├── fabric_items/                       ← sync จาก Fabric Git Integration (ห้ามแก้ path/ไฟล์นี้เอง)
│   ├── lh_test_lakehouse.Lakehouse
│   ├── nb_sales_transform.Notebook
│   ├── pl_test_pipeline.DataPipeline
│   └── parameter.yml                  ← fabric-cicd: remap GUID ข้าม environment
│
├── ci-config.yml                       ← แม็ป item → check pattern (มี _defaults ต่อ type)
├── scripts/
│   ├── deploy.py                       ← publish_all_items() + unpublish_all_orphan_items()
│   ├── deploy_local.py                 ← เหมือน deploy.py แต่ใช้ interactive login (fallback)
│   ├── debug_parameterization.py       ← validate parameter.yml แบบ offline (ไม่ต้องมี credential)
│   ├── validate_pipeline_structure.py  ← shared script สำหรับ check: structure
│   └── validate_schema_contract.py     ← shared script สำหรับ check: schema
│
├── tests/unit/test_<item_name>.py      ← 1 ไฟล์ต่อ item ที่ check: unit_test
├── great_expectations/checkpoints/     ← สำหรับ check: data_quality (ยังไม่มี checkpoint จริงในตอนนี้)
└── requirements.txt
```

**Naming convention ที่ CI พึ่งพา**: ตัด suffix (`.Notebook`, `.Dataflow` ฯลฯ) ออกจากชื่อ item แล้วชื่อไฟล์ test/checkpoint ต้องตรงเป๊ะ เช่น `nb_sales_transform.Notebook` → `tests/unit/test_sales_transform.py`

**Known Gaps ปัจจุบัน**: ไม่มี Staging workspace จริง (merge เข้า `staging` ผ่านแค่ check ไม่ deploy จริง), `great_expectations/checkpoints/` ยังว่างเปล่า (ยังไม่มี item ไหนใช้ `check: data_quality` จริง), ยังไม่แยก Fabric Capacity ระหว่าง staging/prod, rollback test ยังไม่ครอบคลุมทุก schema-change scenario

---

## Collaboration Model

สองโมเดลที่ใช้ได้ เลือกตามขนาดทีม/capacity ที่มี:

**Personal workspace ต่อ dev** (ป้องกันชนกัน 100%) — แต่ละคนมี workspace ของตัวเอง ผูกกับ branch แบบ 1:1 ต่อครั้ง (แต่ตัว workspace เอง **reuse ข้ามงานได้** ไม่ต้องสร้างใหม่ทุก feature — พองานเก่า merge จบแล้วสลับไปผูก branch ใหม่ได้เลย) แก้เสร็จ commit → PR เข้า `staging` — trade-off: ใช้ capacity/license มากขึ้น

**Shared workspace** (ทุกคนอยู่ workspace เดียวกัน) — ใช้ได้เมื่อ capacity จำกัดและแบ่งงานกันทำ **item คนละตัว** ชัดเจน ⚠️ Fabric workspace ที่ผูก Git ไม่มีแนวคิด "working copy ส่วนตัว" — สองคนแก้ item เดียวกันพร้อมกัน คนที่ save ทีหลัง overwrite คนแรกทันที (ข้อมูลหายจริง ไม่ใช่แค่ merge conflict) กติกาที่ต้องมี: naming convention แยกตามเจ้าของ (`nb_nan_sales_transform`), แยก schema/table prefix สำหรับ sandbox, commit บ่อยและเร็ว, แจ้งทีมก่อนแตะ shared/core item

**ตัวแบ่งที่แม่นกว่า "CI vs CD"**: ไม่ใช่ CI ไม่มีข้อจำกัดเสมอไป — ขึ้นกับว่า **"อ่านอย่างเดียว" (รันได้ทุกที่ ไม่แตะ Fabric) vs "เขียน/เปลี่ยนสถานะจริง"** (ต้อง scope ให้อยู่ใน workspace ที่ไม่กระทบคนอื่น) Unit test บน mock data รันบน CI runner เปล่าได้เลย ส่วน data quality check ที่ query จริงจาก Lakehouse ต้องมี workspace/sample data ที่ปลอดภัยรองรับ

**Branch protection**: ห้าม merge เข้า `main` โดยตรง ต้องผ่าน PR + อย่างน้อย 1 approve + CI ผ่านเสมอ — Feature branch ควรอายุไม่เกิน 2-3 วัน (notebook/pipeline JSON merge conflict แก้ manual ยากกว่าโค้ดทั่วไปมาก งานใหญ่ให้ตัดเป็นหลาย PR เล็ก)

---

## รายละเอียดเพิ่มเติม/ประวัติ

สิ่งที่ยังอยู่ใน [`DataOps-CICD-Workflow.md`](./DataOps-CICD-Workflow.md) เพราะเป็นข้อมูลอ้างอิง/ประวัติที่ไม่ต้องเปิดระหว่างทำงานประจำวัน:

| อยากรู้เรื่อง | ไปที่ section |
|---|---|
| Design เต็มรูป 3-environment/3-branch (เป้าหมายระยะยาว ยังไม่ implement) | 2-3 |
| ตัวอย่าง YAML เต็มของทุก workflow variant (feature-branch CI/CD, personal-workspace deploy) | 4, 9 |
| Pilot phase-by-phase test plan (Phase 0-5) + running findings log แบบละเอียดทุกรายละเอียดการทดลอง | 14 |
| ประวัติการทดลอง Connection/Service Principal เต็มรูป (Workspace Identity, Item Identity, Dataflow SP auth) | 14 (ในตาราง findings), `SP-Connection-Experiment-Plan.md` |
| สไลด์นำเสนอทีม/สคริปต์ workshop สำหรับ onboard ทีมกว้าง | 17 |
| แผน rollout แบบ Gantt chart | `CI-CD-Rollout-Gantt-TH.csv` |
| ตัวอย่างการ collaborate ระหว่าง dev หลายคนแบบ scenario เดโม | `Demo-Scenario-Team-Collaboration.md` |
