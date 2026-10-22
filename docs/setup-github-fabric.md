# ตั้งค่า GitHub + Fabric Git Integration (ทำครั้งแรกก่อนใช้ template)

คู่มือนี้พาตั้งค่าทุกอย่างที่อยู่นอกโค้ด (GitHub, Fabric, Service Principal) ให้ workflow ใน `.github/workflows/fabric-ci.yml` ทำงานได้
ทำตามลำดับ — ขั้นหลังพึ่งขั้นก่อน ส่วนรายละเอียดของ staging gate อยู่ที่ `docs/staging-gate.md`

## ภาพรวม: ใครเขียนอะไรลง workspace

| Workspace | เชื่อม Git Integration? | ใครเขียน item ลงไป |
|---|---|---|
| `dev` | **เชื่อม** กับ branch `dev` | นักพัฒนาสร้าง/แก้ใน Fabric UI แล้ว Commit เข้า Git |
| `staging` | ไม่เชื่อม | CI (`deploy.py`) เท่านั้น |
| `prod` | ไม่เชื่อม | CI (`deploy.py`) เท่านั้น หลัง reviewer อนุมัติ |

ให้ CI เป็นผู้เขียนเพียงทางเดียวใน staging/prod เพื่อไม่ให้ใครกด Update/Commit จาก UI ไปทับสิ่งที่ pipeline deploy ไว้

Flow: `feature/*` → PR เข้า `dev` → PR เข้า `main` → CI deploy staging → gate → deploy prod

---

## 1. สร้าง GitHub repo และ branch

1. สร้าง repo ใหม่จาก template นี้ (Private) หรือ copy ไฟล์ทั้งหมดเข้า repo ใหม่
2. ต้องมี branch `main` และ `dev` (ใช้ `staging` เพิ่มได้ ถ้าต้องการให้ PR เข้า `staging` รัน CI)

```bash
git checkout -b dev
git push -u origin dev
```

## 2. สร้าง Fabric workspace

สร้าง 3 workspace (`dev`, `staging`, `prod`) และถ้ามี endpoint item ให้สร้าง endpoint workspace ของแต่ละ environment เพิ่มด้วย

- Workspace ต้องอยู่บน Fabric capacity (Trial/Premium/Fabric) — Pro เปล่าใช้ Git Integration ไม่ได้
- **staging ควรอยู่บน capacity แยกจาก prod** (ขอจากผู้ดูแล capacity)
- เก็บ GUID ของแต่ละ workspace จาก URL: `https://app.fabric.microsoft.com/groups/<GUID>/...`
- กรอก GUID ลง `workspace-config.yml` (`dev` / `staging` / `prod`) — เป็นไฟล์เดียวที่ CI อ่าน GUID workspace หลัก
- endpoint workspace กรอกใน `endpoint-targets.yml`

## 3. สร้าง Service Principal (SP) สำหรับ CI

CI ใช้ SP เพราะ runner ไม่มี browser ให้ login และไม่ควรผูกกับ account ของคนใดคนหนึ่ง

1. **Azure Portal → Microsoft Entra ID → App registrations → New registration** ตั้งชื่อเช่น `sp-fabric-cicd`
2. **Certificates & secrets → New client secret** แล้ว copy ค่า secret ทันที (เห็นได้ครั้งเดียว)
3. จากหน้า Overview copy **Application (client) ID** และ **Directory (tenant) ID**
4. **Fabric → Admin portal → Tenant settings** เปิด **"Service principals can use Fabric APIs"** (ต้องเป็น Fabric admin — อาจเปิดให้เฉพาะ security group ที่ SP อยู่ได้)
5. เข้าทุก workspace (`dev`, `staging`, `prod` และ endpoint workspace) → **Manage access → Add people or groups** → เพิ่ม SP เป็น **Contributor**
   - `dev` ต้องให้ด้วย เพราะ `verify-staging-guids` อ่าน Dev เพื่อเทียบ GUID

> ข้อจำกัดที่รู้แล้ว: ถ้า item อ้างอิง Connection ที่ผูกกับ user (ไม่ใช่ SP) publish ด้วย SP จะ fail — ให้คนที่มีสิทธิ์บน Connection รัน `scripts/deploy_local.py` จากเครื่องตัวเองแทน (ดู README)

## 4. ตั้ง GitHub Secrets และ Environment

**Secrets** — repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret | ค่า |
|---|---|
| `FABRIC_CLIENT_ID` | Application (client) ID ของ SP |
| `FABRIC_CLIENT_SECRET` | client secret ของ SP |
| `FABRIC_TENANT_ID` | Directory (tenant) ID |

**Environment `production`** — repo → Settings → Environments → New environment ชื่อ `production` เป๊ะ (workflow อ้างชื่อนี้):

- เปิด **Required reviewers** แล้วเลือกคนที่ต้องอนุมัติก่อนขึ้น prod
- **Deployment branches and tags** → Selected branches → เฉพาะ `main`
- ถ้าไม่ตั้ง `deploy-prod` จะรันทันทีโดยไม่มีใครอนุมัติ

## 5. เปิด Git Integration ฝั่ง Fabric

### 5.1 เตรียมสิทธิ์ (ทำครั้งเดียว)

- Tenant settings ต้องเปิด Git Integration ให้ผู้ใช้ (ชื่อการตั้งค่าอาจต่างตามเวอร์ชัน เช่น "Users can synchronize workspace items with their Git repositories" และตัวที่เกี่ยวกับ GitHub) — ถ้ากด Connect ไม่ได้ให้ขอ Fabric admin ตรวจ
- Fabric ต้องมี credential ต่อ GitHub: ใน workspace settings → Git integration → **Add account** ใส่ GitHub Personal Access Token (fine-grained: สิทธิ์ **Contents: Read and write** และ **Metadata: Read** บน repo นี้)
  - PAT ผูกกับคนที่สร้าง — ถ้าคนนั้นออกจากทีม Git Integration ของ workspace จะหยุด ควรบันทึกว่าใครเป็นเจ้าของและวันหมดอายุ

### 5.2 เชื่อม `dev` workspace

1. เข้า workspace `dev` → **Workspace settings → Git integration**
2. เลือก **GitHub** → เลือก account/repo
3. Branch: `dev`
4. Folder: `/fabric_items`
5. กด **Connect and sync**

เชื่อมเฉพาะ `dev` เท่านั้น — อย่าเชื่อม staging/prod (ดูตารางภาพรวม)

> โฟลเดอร์ `fabric_items_endpoint/` สำหรับ endpoint item ที่มี Git Integration แยกของ dev-endpoint workspace — เชื่อมแบบเดียวกัน แต่ชี้ Folder ไปที่ `/fabric_items_endpoint`

### 5.3 ทดสอบการเชื่อมต่อ

- **Workspace → Git:** สร้าง Notebook ใน `dev` → เปิด **Source control** → **Commit** → ต้องเห็นโฟลเดอร์ `*.Notebook` ใน branch `dev` ของ GitHub
- **Git → Workspace:** แก้ไฟล์ใน GitHub (branch `dev`) → กลับมาที่ workspace → Source control → **Update** → ต้องเห็นการเปลี่ยนแปลง
- ถ้า Commit ไม่ขึ้นใน GitHub ให้เช็คว่า branch ที่ workspace ผูกไว้ตรงกับ branch ที่ไปดู

### 5.4 กฎที่ต้องจำ

- สร้าง/แก้ item ผ่าน Fabric UI (หรือ MCP) แล้ว **Commit ผ่าน Source control panel** เท่านั้น — อย่าเขียนไฟล์ item ใน `fabric_items/` ด้วยมือ (logicalId ไม่ตรง ทำให้ sync conflict)
- ชื่อ item ต้องตรงกับไฟล์ test (`nb_xxx.Notebook` ↔ `tests/unit/test_xxx.py`)

## 6. ตั้ง Branch protection (Settings → Branches)

| Branch | ตั้งค่า |
|---|---|
| `main` | Require pull request (อย่างน้อย 1 review) · บังคับกับ admin · ห้าม force push/ลบ · Required status checks: `test`, `dq-gate-dev`, `dq-gate-staging` |
| `dev` | ห้าม force push และห้ามลบเท่านั้น — **ห้ามบังคับ PR หรือ required check** เพราะจะบล็อกการ Commit จาก Fabric |

หมายเหตุ

- เลือก required check ได้หลังจาก workflow รันครั้งแรกแล้วเท่านั้น (ชื่อ job ต้องเคยรายงานผลมาก่อน) และอย่าตั้ง check ที่ไม่มี job รายงาน ไม่งั้น PR จะค้างรอตลอด
- job ที่ถูก skip ด้วยเงื่อนไข `if` ถือว่าผ่านสำหรับ required check
- เปลี่ยนชื่อ job ใน workflow = ต้องกลับมาแก้รายการ required check ที่นี่ด้วย

## 7. ทดลองก่อนใช้จริง

flow staging ยังไม่เคยรันครบทั้งเส้นบน GitHub จริง ให้ทดลองตามลำดับ:

1. Push commit เล็กๆ เข้า `feature/test-ci` → ดูแท็บ Actions ว่า job `test` ผ่าน
2. เปิด PR เข้า `dev` แล้ว merge
3. เปิด PR `dev` → `main` → ดูว่า `dq-gate-dev` → `deploy-staging` → `dq-gate-staging` รันตามลำดับ
4. Merge เข้า `main` → `deploy-prod` ต้องหยุดรอ reviewer อนุมัติ → อนุมัติ → `dq-gate-poc` รัน

## 8. Rollback ด้วย git revert

ใช้ `git revert` บน `main` — ไม่ใช้ `git reset`/force push เพราะ branch ถูก protect และต้องเก็บประวัติไว้

1. หา commit (หรือ merge commit) ที่ต้องการย้อน
2. สร้าง branch แล้ว revert (`-m 1` ถ้าเป็น merge commit)

   ```bash
   git checkout -b revert/<ชื่อ> main
   git revert -m 1 <merge-commit-sha>
   git push -u origin revert/<ชื่อ>
   ```
3. เปิด PR เข้า `main` → ผ่าน CI → merge → pipeline deploy staging → gate → prod เหมือน release ปกติ
4. ซิงค์ `dev` ให้ตรงกับ `main` (merge `main` กลับเข้า `dev`) แล้วกด **Update** ใน Source control ของ `dev` workspace ไม่งั้นครั้งต่อไปที่ Commit จาก `dev` จะเอาของที่ revert ไปกลับมาใหม่

ข้อจำกัด

- revert ย้อนได้เฉพาะ **โค้ด/definition ของ item** ไม่ย้อนข้อมูลใน Lakehouse/Warehouse — ถ้าข้อมูลเสียต้องใช้ Delta time travel/restore แยกต่างหาก (ดู section 16 ของ `DataOps-CICD-Workflow.md`)
- ถ้า commit ที่ revert เป็นการ **เพิ่ม item** ใหม่ `deploy.py` จะ unpublish item นั้นจาก workspace ปลายทาง ยกเว้น Lakehouse/Warehouse/SQL Database ที่ไม่ถูกลบ by default จึงอาจต้องลบเองถ้าไม่ต้องการ
- revert ต้องผ่าน gate ปกติ — กรณีฉุกเฉินที่ gate ล้มเพราะข้อมูลเสียอยู่แล้ว ต้องตัดสินใจร่วมกับ reviewer ว่าจะรอแก้ข้อมูลก่อนหรือไม่ (template ไม่มีทางลัดข้าม gate ให้โดยตั้งใจ)

---

## Checklist

- [ ] สร้าง repo + branch `main`, `dev`
- [ ] สร้าง workspace `dev` / `staging` / `prod` (+ endpoint workspace ถ้ามี), staging แยก capacity จาก prod
- [ ] กรอก GUID ใน `workspace-config.yml` (และ `endpoint-targets.yml` ถ้ามี)
- [ ] สร้าง SP + เปิด "Service principals can use Fabric APIs" + ให้ Contributor ทุก workspace
- [ ] ตั้ง GitHub Secrets 3 ค่า
- [ ] สร้าง Environment `production` + Required reviewers + จำกัดเฉพาะ branch `main`
- [ ] เชื่อม Git Integration ของ `dev` workspace กับ branch `dev` (folder `/fabric_items`)
- [ ] ทดสอบ Commit และ Update ทั้งสองทิศทาง
- [ ] ตั้ง branch protection `main` และ `dev` ตามตาราง
- [ ] ทดลอง flow ทั้งเส้นด้วย PR ทดลอง
