## สรุปการเปลี่ยนแปลง
<!-- อธิบายสั้นๆ ว่า PR นี้ทำอะไร และทำไมถึงต้องแก้ -->

## ประเภทของการเปลี่ยนแปลง
- [ ] Ingestion / source connection ใหม่หรือแก้ไข
- [ ] Transformation logic (notebook / dbt model / SQL)
- [ ] Schema change (เพิ่ม/ลบ/แก้ column, type, table ใหม่)
- [ ] Orchestration / pipeline schedule
- [ ] Data quality rule / test
- [ ] Infra / config (Deployment rules, connection, secret)
- [ ] อื่นๆ: _______

## Impact — กระทบอะไรบ้าง
**Table/Pipeline/Notebook ที่ถูกแก้โดยตรง:**
- `<item ที่แก้>`

**Downstream ที่อาจได้รับผลกระทบ** (dashboard, model, pipeline อื่นที่ query ต่อจาก item นี้):
- `<ระบุ หรือเขียนว่า "ไม่มี"​>`

**เป็น breaking change ไหม** (เปลี่ยน schema/ชื่อ column ที่ของเดิม query อยู่)?
- [ ] ใช่ — ได้แจ้ง owner ของ downstream แล้ว: `<ชื่อคน/ทีม>`
- [ ] ไม่ใช่

## Data Backfill
- [ ] ต้อง backfill ข้อมูลย้อนหลัง — ระบุช่วงวันที่/วิธี: `<รายละเอียด>`
- [ ] ไม่ต้อง backfill

## Testing
- [ ] Unit test ผ่านแล้ว (`pytest tests/unit`)
- [ ] Data quality check ผ่านแล้ว (Great Expectations / dbt test)
- [ ] ทดสอบบน personal/dev workspace แล้ว เห็นผลลัพธ์ตรงตามที่คาด
- [ ] ไม่สามารถทดสอบอัตโนมัติได้ — เหตุผล: `<ระบุ>`

## Checklist ก่อนขอ Review
- [ ] ตั้งชื่อ item ตาม naming convention ของทีม (`nb_<owner>_<domain>`, `pl_<owner>_<domain>`)
- [ ] ไม่มี hardcode secret/connection string ในโค้ด
- [ ] Branch นี้ rebase/merge จาก `dev` ล่าสุดแล้ว ไม่ conflict
- [ ] อัปเดต schema registry / changelog (ถ้ามีการเปลี่ยน schema)
- [ ] เพิ่ม/แก้ `ci-config.yml` ถ้ามี item ใหม่หรือเปลี่ยน required check

## Reviewer ที่ควรตรวจสอบเป็นพิเศษ
<!-- แท็ก owner ของ downstream ถ้า PR นี้กระทบ table ที่เขาดูแล -->
@
