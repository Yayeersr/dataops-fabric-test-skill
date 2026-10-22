# tests/live_dq — เทมเพลต Live Data Quality Check

Live DQ = GX รันใน Notebook บนข้อมูลจริง (Lakehouse/Warehouse) ใน Fabric — **ไม่ใช่ 1 ใน 5 check pattern**
(`unit_test`/`data_quality`/`structure`/`schema`/`none`) เพราะต้อง deploy item ก่อนถึงจะเช็คได้ จึงรันเป็น CI job
แยกหลัง deploy ไม่ใช่ใน job `test` ดูเหตุผลเต็มและขั้นตอนละเอียดที่ `docs/check-patterns-guide.md` ส่วนที่ 1

| ไฟล์ | หน้าที่ |
|---|---|
| `_TEMPLATE_nb_live_dq.py` | โค้ด Notebook ที่ copy ไปวางทีละ cell ใน Notebook จริง (แก้ table/column/expectation) |
| `README.md` (ไฟล์นี้) | ขั้นตอน + snippet ของ `ci-config.yml` และ CI job |

> **ไฟล์ในโฟลเดอร์นี้ไม่ถูก deploy และไม่ถูก pytest เก็บ** — ตั้งใจวางนอก `fabric_items/` เพราะ `deploy.py`
> publish ทุกอย่างในนั้นขึ้น workspace จริง ตัว Notebook จริงต้องสร้างผ่าน Fabric UI แล้ว sync เข้า `fabric_items/` เอง

## ขั้นตอน

1. สร้าง Notebook ผ่าน Fabric UI (ห้าม hand-write ไฟล์ item เข้า `fabric_items/`)
2. วางโค้ดจาก `_TEMPLATE_nb_live_dq.py` ทีละ cell → แก้ `TABLE_NAME`, column, expectation (ตัดมิติที่ไม่เกี่ยวออก)
   - บรรทัด `# MAGIC %pip ...` ให้ลบ `# MAGIC ` ออกตอนวาง
   - Attach Lakehouse เป็น default lakehouse ถ้าใช้ Lakehouse
3. เลือกตัวเรียกรัน
   - **แบบ A** Pipeline ห่อ Notebook Activity — ต้องตั้ง Base parameter `_inlineInstallationEnabled` = `true` (Boolean)
   - **แบบ B** รัน Notebook ตรงๆ (`--item-type notebook`) — ยังไม่เคย verify ว่าไม่ติดข้อจำกัด `%pip`
4. Commit ผ่าน Fabric Studio → Source Control ให้ sync เข้า `fabric_items/`
5. เพิ่ม entry ท้าย `ci-config.yml` (ไม่งั้น CI จะบังคับ pattern default ของ type กับ item นี้):

   ```yaml
   <ชื่อ_notebook_item>:
     skip_check: true
     skip_reason: >-
       Live DQ check item (<วันที่ตั้งค่า>) — เช็คผ่าน live gate (scripts/run_live_dq_item.py)
       แทน ไม่ใช่ static definition check ดู docs/check-patterns-guide.md

   <ชื่อ_pipeline_item>:   # ตัดออกถ้าใช้แบบ B
     skip_check: true
     skip_reason: >-
       Live DQ check item (<วันที่ตั้งค่า>) คู่กับ <ชื่อ_notebook_item> — เหตุผลเดียวกัน
   ```

6. เพิ่ม entry ใน `dq-gates.yml` (`item_type` + `stages: [dev, staging, prod]`) — ไม่ต้องแก้ `fabric-ci.yml`
   job `dq-gate-dev` / `dq-gate-staging` / `dq-gate-poc` อ่านไฟล์นี้เอง (ดู `docs/staging-gate.md`)

## ทดสอบก่อนถือว่าพร้อมใช้ (ต้องครบทั้ง 2 เคส)

- ข้อมูลดี → run ต้อง `Succeeded`
- ทำข้อมูลเสีย 1 แถวชั่วคราว (เช่น `UPDATE <table> SET <col> = NULL WHERE <id> = X`) → รันซ้ำ → ต้อง `Failed` จริง
  แล้วคืนค่าข้อมูลกลับ

ถ้าเคสข้อมูลเสียยังผ่าน แปลว่า `raise AssertionError` หายหรือ expectation ไม่ได้ผูกกับ column ที่เสียจริง
