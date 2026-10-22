# Staging gate — ตรวจ data quality ที่ staging ก่อน deploy ขึ้น prod

> ⏸️ **สถานะปัจจุบัน: staging ถูกปิดชั่วคราว** (ยังไม่มี staging workspace) — flow จริงคือ dev → `dq-gate-dev` → prod
> `deploy-staging` ใส่ `false &&` (job staging ทั้งชุด skipped) และ `deploy-prod`/`deploy-endpoints` รอแค่ `test` + `dq-gate-dev`
> required check บน `main` ใช้แค่ `test`, `dq-gate-dev` · เปิดกลับ: สร้าง staging workspace → กรอก GUID ใน `workspace-config.yml`
> → ลบ `false &&` ที่ `deploy-staging` → ใส่ `deploy-staging, dq-gate-staging, deploy-endpoints-staging` กลับใน `needs` + เงื่อนไข `result == 'success'`
> ของ `deploy-prod` และ `deploy-endpoints` (ดู comment `[STAGING DISABLED]` ใน workflow)

template นี้บังคับมี staging เสมอ: `deploy-prod` จะไม่รันถ้า `deploy-staging`, `dq-gate-staging`
หรือ `deploy-endpoints-staging` ไม่สำเร็จ

> ⚠️ flow นี้ยังไม่เคยรันครบทั้งเส้นบน GitHub จริง (เงื่อนไข `always()` ใน `needs` ตรวจแค่ YAML parse +
> ลำดับ graph) — ทดลองด้วย PR ทดลองก่อนตั้งเป็น required check (ขั้นตอนที่ 5 ด้านล่าง)

## ทำไมต้องมี

`dq-gate-poc` รันหลัง `deploy-prod` — ถ้าเจอของเสียก็ขึ้น production ไปแล้ว (ตรวจได้ แต่กันไม่ได้)
`dq-gate-dev` (ตรวจที่ Dev ตอนเปิด PR) ผ่านที่ Dev ไม่การันตีว่า prod สะอาด

เป้าหมาย: **ตรวจ DQ ก่อน deploy ไป workspace ถัดไปทุกครั้ง** — Dev gate → staging → staging gate → prod

## ลำดับ job

```
test → dq-gate-dev → deploy-staging ─┬─ dq-gate-staging ──────────┬─ deploy-prod → dq-gate-poc
                                     ├─ deploy-endpoints-staging ─┤
                                     └─ verify-staging-guids      └─ deploy-endpoints (prod/dev)
                                        (รายงาน ไม่บล็อก)
```

| job | รันเมื่อ | บทบาท |
|---|---|---|
| `dq-gate-dev` | `pull_request` → `main`/`staging` | gate ที่ Dev ก่อน deploy ไป staging (ตั้งเป็น required check ได้) |
| `deploy-staging` | PR → `main`/`staging` **และ** push เข้า `main` | deploy ไป staging (`workspace-config.yml` → `staging`) |
| `dq-gate-staging` | หลัง `deploy-staging` สำเร็จ (PR และ push) | gate ที่ staging ก่อน deploy ไป prod |
| `deploy-endpoints-staging` | หลัง `deploy-staging` สำเร็จ | deploy endpoint item เข้า endpoint workspace ของ staging (`endpoint-targets.yml` → `targets.staging`) |
| `verify-staging-guids` | หลัง `deploy-staging` สำเร็จ | ตรวจ GUID ของ Dev ตกค้าง (รายงานอย่างเดียว `continue-on-error`) |
| `deploy-prod` / `deploy-endpoints` (prod) | push เข้า `main` | **ไม่รันถ้า staging job ใดล้มเหลว** |
| `dq-gate-poc` | หลัง `deploy-prod` | ยืนยันหลัง deploy (ไม่ใช่ gate) |

สองชั้นกัน: (1) บน PR gate ที่ staging เป็น required check ก่อน merge (2) บน push เข้า `main` run เดียวกันรัน
staging ซ้ำก่อน `deploy-prod` — ชั้นนี้กันของเสียขึ้น prod แม้ไม่ได้ตั้ง required check (แลกกับ deploy staging 2 ครั้งต่อ release)

บน push เข้า `dev` job gate พวกนี้ `skipped` ตามปกติ และ `deploy-endpoints` ไป dev endpoint ได้เหมือนเดิม
ใช้ `always()` + เช็ค `result` เอง เพราะ `dq-gate-dev` เป็น `skipped` เสมอบน push และ GitHub จะ skip job ถัดไปตามโดย default

## ขั้นตอนตั้งค่า (ทำตามลำดับ)

1. **สร้าง staging workspace** — แยก Fabric Capacity จาก prod (ต้องขอ IT/ผู้ดูแล capacity) แล้วกรอก GUID ใน `workspace-config.yml` → `staging`
2. **ให้ Service Principal เข้าถึงได้** — SP ที่ใช้ใน `FABRIC_CLIENT_ID` ต้องเป็น Member/Contributor ของ staging
   และ (สำหรับ `verify-staging-guids`) อ่าน Dev workspace ได้ด้วย
3. **เพิ่ม live DQ gate** ใน `dq-gates.yml` ใส่ `stages: [dev, staging, prod]` — ยังไม่มี gate = job ผ่านพร้อม notice
   (staging ต้องมีข้อมูลให้ตรวจ หรือ pipeline สร้างเอง — ผ่านที่ staging ตรวจได้เท่าข้อมูลใน staging เท่านั้น)
4. **ทดลองด้วย PR ทดลอง** ชี้ `main` (หรือ `staging`) แล้วดูว่า `dq-gate-dev` → `deploy-staging` → `dq-gate-staging`
   รันตามลำดับ และทดลอง push เข้า `main` ครั้งแรกโดยดูว่า `deploy-prod` รอผล gate (ทำให้ gate แดงหนึ่งครั้งเพื่อเช็คกรณีล้มเหลว)
5. **ตั้ง required status check** บน `main`: `test`, `dq-gate-dev`, `dq-gate-staging`
   (Settings → Branches → branch protection rule ของ `main` → Require status checks)
   - ถ้าไม่ตั้ง job แดงแล้วก็ยัง merge ได้ — แต่ `deploy-prod` ยังถูกบล็อกตอน push (ชั้นที่สอง)
   - job ที่ถูก skip เพราะเงื่อนไข (`if`) GitHub รายงานเป็นผ่านสำหรับ required check
6. หลัง `verify-staging-guids` รันผ่านเสถียรสองสามครั้ง ให้ลบ `continue-on-error: true` เพื่อให้เป็น gate

## Endpoint item (deploy ข้าม workspace)

item ที่ต้อง deploy ไปคนละ workspace จาก item หลัก (authored ใน `fabric_items_endpoint/` ผ่าน Git Integration ของ
dev-endpoint workspace) ตั้งค่าใน `endpoint-targets.yml` — `scripts/deploy_endpoints.py` วน deploy ทุก entry ที่มี target ตรงกับ environment

ต่อ endpoint item หนึ่งตัวต้องทำ:
1. สร้าง endpoint workspace ของ staging และ prod (staging แยก capacity จาก prod) ให้ SP เข้าถึง
2. เพิ่ม entry ใน `endpoint-targets.yml` พร้อม `targets.staging` และ `targets.prod`
   (entry ที่ไม่มี target staging ถูกข้ามเงียบๆ — ถ้า Notebook/Pipeline หลักพึ่ง endpoint ต้องใส่ให้ครบ)
3. `fabric_items/parameter.yml`: เพิ่ม rule ของ notebook ที่อ้าง endpoint ด้วย key `staging` และ `prod` แยกกัน (ไม่ใช้ `_ALL_`)
   — ตาม fabric-cicd ถ้า environment ไม่มี key นั้น rule จะถูกข้ามพร้อม warning staging จึงไม่ถูก remap ไปชี้ prod endpoint
   ⚠️ id ที่ hardcode พังเมื่อ Lakehouse ถูกสร้างใหม่ ถ้าเลี่ยงได้ให้ notebook หา Lakehouse จากชื่อตอนรัน
4. `verify-staging-guids` ใน workflow: เพิ่ม `--allow <GUID ของ endpoint staging workspace>` ไม่ให้ขึ้น INFO ทุกครั้ง
5. รัน `python scripts/debug_parameterization.py --environment staging` เช็คโครงสร้าง แล้วทดสอบด้วย PR ทดลอง

## ข้อควรรู้

- `scripts/deploy.py` unpublish orphan items — ทำงานกับ staging ด้วย (Lakehouse/Warehouse ไม่ถูกลบโดย default)
- การ PASS ของ `verify-staging-guids` แปลว่าไม่ชี้กลับ Dev ไม่ได้พิสูจน์ว่าชี้ถูกที่ — ดู INFO ใน log ด้วยเสมอ
- ไม่มี `actionlint` ที่ใช้ตรวจ workflow นี้ — ตรวจได้แค่ YAML parse และ `needs` graph
