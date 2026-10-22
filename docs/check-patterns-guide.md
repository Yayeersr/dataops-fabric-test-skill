# Check Patterns — Usage Guide & Templates

คู่มือนี้รวมวิธีใช้งาน + เทมเพลตของกลไกเช็คทุกแบบที่มีในรีโปนี้ (`ci-config.yml`'s 5 pattern —
`unit_test`/`data_quality`/`structure`/`schema`/`none` — บวกกลไก live DQ ที่แยกนอกระบบ pattern)
สรุปสถานะรวมก่อน:

| Pattern | มีเทมเพลต/คู่มือไหม | สถานะ |
|---|---|---|
| **Live DQ Gate** (แยกนอก 5 pattern) | ✅ [ส่วนที่ 1](#ส่วนที่-1--live-data-quality-check-gx) | ✅ กลไกพิสูจน์แล้วจริงใน `dataops-fabric-pilot` (repo แยก) — เทมเพลตในไฟล์นี้ยังไม่เคยผูกกับ item จริงใน repo นี้ |
| `schema` | ✅ [ส่วนที่ 2](#ส่วนที่-2--schema-contract-check) | ✅ พร้อมใช้ — เทมเพลตที่ `tests/schema/_TEMPLATE.yml` |
| `unit_test` | ✅ [ส่วนที่ 3](#ส่วนที่-3--unit_test-pattern) | ✅ พร้อมใช้ — เทมเพลตที่ `tests/unit/_TEMPLATE_unit_test.py` (ทั่วไป) และ `tests/unit/_TEMPLATE_dq_rule_check.py` (เฉพาะ DQ-rule function) |
| `structure` | ✅ [ส่วนที่ 4](#ส่วนที่-4--structure-pattern) | ✅ ใช้ได้ทันที ไม่ต้องทำอะไรต่อ item (script กลางที่ทำงานอัตโนมัติ) |
| `data_quality` (CSV แบบเดิม) | ✅ [ส่วนที่ 5](#ส่วนที่-5--data_quality-csv-pattern-เดิม) | ⚠️ ใช้ได้ แต่**ยังไม่ฟันธง** — รอเช็คก่อนว่ามี workspace/ทีมอื่นใช้ไฟล์แบบนี้อยู่ไหม |
| `none` | ✅ [ส่วนที่ 6](#ส่วนที่-6--none-pattern) | ✅ (ไม่มีอะไรให้ทำ ตามชื่อ) |

ดูภาพรวมของทั้งระบบ pattern-based CI (เหตุผลเชิงดีไซน์) ได้ใน `DataOps-CICD-Workflow.md` ของ repo เอกสารแยก

## เลือก pattern ไหนกับ item แบบไหน

| ถ้า item ของคุณ... | ใช้ pattern นี้ |
|---|---|
| เป็น Lakehouse/Warehouse มีตารางข้อมูล | `schema` |
| เป็น Notebook ที่เขียน transform logic | `unit_test` (ทั่วไป — ส่วนที่ 3) |
| เป็น Notebook ที่มีฟังก์ชันเช็คกฎ DQ โดยเฉพาะ (ไม่ใช่ transform) | `unit_test` (DQ-rule — `tests/unit/_TEMPLATE_dq_rule_check.py`) |
| เป็น DataPipeline | `structure` (auto อยู่แล้ว ไม่ต้องทำอะไร) |
| ต้องการเช็คค่าข้อมูลกับตัวอย่างแช่แข็งก่อน deploy | `data_quality` (CSV) — คุยกับทีมก่อนใช้จริง (ดูสถานะในส่วนที่ 5) |
| อยากเช็คข้อมูลจริงที่เพิ่ง deploy ขึ้น prod/staging | **Live DQ Gate** (ส่วนที่ 1) |
| ไม่มีอะไรให้เช็คจริงๆ โดยตั้งใจ | `none` |

---

# ส่วนที่ 1 — Live Data Quality Check (GX)

เช็ค data quality แบบ **live** (เช็คข้อมูลสดตรงบน Fabric ผ่าน Spark) ด้วย
[Great Expectations](https://greatexpectations.io/) (GX) — เป็นผลจากการทำ POC จริงใน section 14
Phase 7 ของ `DataOps-CICD-Workflow.md` (repo เอกสารแยก) พิสูจน์แล้วว่า GX check ที่ raise error
ใน Notebook Activity ทำให้ pipeline job report เป็น `Failed` จริง ใช้เป็น automated DQ gate ได้

## เมื่อไหร่ควรใช้ live check เทียบกับ CSV/snapshot

| | Live check (ส่วนนี้) | CSV/snapshot (`data_quality` pattern เดิม) |
|---|---|---|
| ข้อมูลที่เช็ค | ข้อมูลจริงบน Lakehouse/Warehouse ผ่าน Spark ตรงๆ | ไฟล์ CSV ที่ commit ไว้ใน repo |
| เหมาะกับ | ตาราง production จริง ไม่ว่าขนาดเท่าไหร่ | ตารางเล็กมากๆ (lookup/config) หรือทดสอบ mechanism เฉยๆ |
| ข้อมูลออกจาก Fabric ไหม | ไม่เลย | ต้องดึงออกมาเป็นไฟล์ก่อน |
| **ใช้ได้ในรีโปนี้ไหม** | ✅ ใช้ทางนี้เป็นค่า default สำหรับข้อมูลจริง | ⚠️ ใช้ได้ แต่**สถานะยังไม่ฟันธง** — ดูหมายเหตุด้านล่าง |

> ⚠️ **สถานะไฟล์ CSV ใน repo นี้ (แก้ไข 2026-09-28): ยังไม่ตัดสินใจ ไม่ใช่ห้ามเด็ดขาด**
> เคยพูดถึงว่าจะห้ามไฟล์ CSV เด็ดขาด แต่ทีมยังไม่ได้เช็คว่ามี workspace/ทีมอื่นใช้ไฟล์ประเภทนี้
> อยู่แล้วหรือเปล่า — จนกว่าจะเช็คแน่ชัด **อย่าเพิ่งถือว่า CSV ถูกแบนหรือถูกอนุมัติ** กลไก
> CSV/snapshot ทั้งชุด (`scripts/run_data_quality_checkpoint.py`,
> `tests/data_quality/checkpoints/dq_TEMPLATE.yml`, self-test pair พร้อมไฟล์
> `dq_selftest_good_data.csv`/`dq_selftest_bad_data.csv`) อยู่แค่ใน branch
> `test/data-quality-selftest` ยังไม่ได้ merge เข้า `dev`/`main` — ยังใช้ได้ตามปกติถ้าต้องการ
> แค่คุยกับทีมยืนยันก่อน merge บน `dev`/`main` จริงตอนนี้ `tests/data_quality/checkpoints/`
> ยังว่างเปล่า (มีแค่ `.gitkeep`) แม้ `README.md` จะยังพูดถึง `dq_<name>.yml` เป็นไฟล์ "ขาดไม่ได้" อยู่
> ก็ตาม — ไม่ว่าผลจะออกมายังไง **live check ยังเป็นทางเลือกที่แนะนำสำหรับข้อมูล production จริง** อยู่ดี

## Architecture

เทมเพลตนี้ใช้ได้กับ **item ประเภทไหนก็ได้** ที่ Fabric รันเป็น "job" ได้ (Notebook, Data Pipeline)
และดึงข้อมูลได้ยังไงก็ได้ (Lakehouse ผ่าน Spark, Warehouse ผ่าน SQL) — เลือกเองได้ 2 จุด ตามตาราง
ด้านล่าง "จุดที่ต้องเลือกเอง"

```
ข้อมูลจริง (Lakehouse หรือ Warehouse)
        ↓
Notebook: โหลดข้อมูล → เช็คด้วย GX → raise ถ้า fail          ← เทมเพลตด้านล่าง ใช้ตัวเดียวกันเสมอ
        ↓ ถูกเรียกจาก (เลือกได้ 2 แบบ)
  แบบ A: Pipeline ห่อด้วย Notebook Activity                   ← ต้องมี parameter _inlineInstallationEnabled: true
  แบบ B: รัน Notebook ตรงๆ ไม่ผ่าน Pipeline
        ↑ สั่งรัน + รอผลโดย
scripts/run_live_dq_item.py --item-type pipeline|notebook (เรียก Fabric REST API)
        ↑ ถูกเรียกโดย
CI job (`dq-gate-dev` / `dq-gate-staging` / `dq-gate-poc` ใน `fabric-ci.yml` — อ่านรายชื่อ gate จาก `dq-gates.yml`)
```

**จุดที่ต้องเลือกเอง (user กำหนดตาม item จริง):**

| จุดที่เลือก | ตัวเลือก | เลือกยังไง |
|---|---|---|
| แหล่งข้อมูล | Lakehouse (Spark) / Warehouse (SQL) | ดูหัวข้อ "โหลดข้อมูลจากแหล่งไหน" ในเทมเพลตด้านล่าง |
| ตัวเรียกรัน | Pipeline ห่อ Notebook / Notebook ตรงๆ | ถ้าไม่มี activity อื่นต้องต่อ ใช้ Notebook ตรงๆ ง่ายกว่า (ข้าม parameter `_inlineInstallationEnabled` ได้ด้วย เพราะข้อจำกัดนั้นเกิดเฉพาะตอนถูกเรียกผ่าน pipeline — ยังไม่เคย verify จริง ลองแล้วบันทึกผลกลับมาด้วย) |
| `--item-type` ใน `run_live_dq_item.py` | `pipeline` (default) / `notebook` | ให้ตรงกับตัวเรียกรันที่เลือกไว้แถวบน |

กลไกนี้พิสูจน์แล้วว่าใช้งานได้จริง (แบบ A, Lakehouse) ระหว่างทำ POC ใน `dataops-fabric-pilot`
(repo แยก — ไม่ได้อยู่ใน repo นี้) ดูตัวอย่าง item จริงที่นั่นถ้าต้องการอ้างอิง ส่วน `scripts/run_live_dq_item.py`
ใน repo นี้เป็นสคริปต์ตัวเดียวกัน ใช้ได้ทันทีไม่ต้องแก้ไข

## แยกโน้ตบุ๊คใหม่ทำ DQ โดยเฉพาะ หรือฝังเข้าโน้ตบุ๊ค transform เดิม?

ต้องมี "โน้ตบุ๊ค" (หรือ item ที่รัน Python/Spark ได้) เสมอ เพราะ GX ต้องมีที่รันโค้ด — แต่**ไม่จำเป็น
ต้องเป็นโน้ตบุ๊คใหม่แยกต่างหากเสมอไป** เลือกได้ 2 แบบ:

| | แยกโน้ตบุ๊คใหม่ (แบบที่ POC ทำ) | ฝังเข้าโน้ตบุ๊ค transform เดิม |
|---|---|---|
| เหมาะกับ | ตารางที่ไม่มี transform notebook เป็นเจ้าของชัดเจน (หลาย process เขียนเข้าตารางเดียวกัน) หรืออยากเรียกเช็คแยกได้เองโดยไม่ต้องรัน transform ใหม่ | มี transform notebook อยู่แล้ว อยากให้ "transform แล้วเช็คทันที" เป็น step เดียวกัน |
| Item ที่ต้องสร้างเพิ่ม | Notebook ใหม่ (+ Pipeline ใหม่ถ้าเลือกแบบ A) | ไม่ต้องสร้างอะไรเพิ่มเลย |
| การต่อสาย Pipeline | ต้องเพิ่ม Notebook Activity ใหม่ | ใช้ Notebook Activity เดิมที่เรียก transform notebook อยู่แล้ว (แค่เพิ่ม `_inlineInstallationEnabled` ถ้ายังไม่มี) |

### ตัวอย่างแบบฝังเข้าโน้ตบุ๊คเดิม

ตัวอย่างสมมติ — ถ้า Notebook transform เดิมของคุณท้ายไฟล์เขียนตารางแล้วจบแค่นี้:

```python
df = df.withColumn("region", when(col("product_id").isin("P001"), "BKK").otherwise("CNX"))

(df.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .save(table_path))

print(f"Done. Wrote to '{table_path}'.")
```

เพิ่ม cell ต่อท้ายตรงนี้เข้าไปในโน้ตบุ๊คเดียวกันเลย ไม่ต้องสร้างไฟล์ใหม่:

```python
# ── DQ check — เพิ่มต่อท้าย transform เดิม (ใช้ table_path ตัวแปรเดียวกับด้านบน) ──
%pip install "great_expectations>=1.0,<2.0"

import great_expectations as gx

df_check = spark.read.format("delta").load(table_path).toPandas()

_ge_context = gx.get_context(mode="ephemeral")
_ge_batch_definition = (
    _ge_context.data_sources.add_pandas("pandas")
    .add_dataframe_asset(name="sales_dq")
    .add_batch_definition_whole_dataframe("batch")
)
_batch = _ge_batch_definition.get_batch(batch_parameters={"dataframe": df_check})

expectations = [
    gx.expectations.ExpectColumnValuesToNotBeNull(column="product_id"),
    gx.expectations.ExpectColumnValuesToBeInSet(column="region", value_set=["BKK", "CNX"]),
]

results = [_batch.validate(e) for e in expectations]
all_passed = all(r.success for r in results)

for expectation, result in zip(expectations, results):
    status = "PASS" if result.success else "FAIL"
    print(f"[{status}] {expectation}")

if not all_passed:
    raise AssertionError("Data quality check failed after transform — ดูรายละเอียดที่ log ด้านบน")
```

จุดสำคัญที่ต่างจากแบบแยกโน้ตบุ๊ค:
- ใช้ตัวแปร `table_path` ที่ transform ประกาศไว้แล้ว ไม่ต้อง hardcode path ใหม่
- อ่านข้อมูล**กลับจากตารางที่เพิ่งเขียนเสร็จ** (`spark.read...load(table_path)`) ไม่ใช่ `df` ที่ยัง
  อยู่ใน memory ตรงๆ — ยืนยันว่าสิ่งที่ persist ลง Delta table จริงถูกต้อง (กันเคส write fail บางส่วน)
- ถ้า Notebook Activity เดิมยังไม่มี parameter `_inlineInstallationEnabled: true` ต้องเพิ่มด้วย
  (กฎเดียวกับหัวข้อ "ขั้นตอนตั้งค่าให้ item ใหม่" ด้านล่าง)

## ขั้นตอนตั้งค่าให้ item ใหม่

1. **สร้าง item ผ่าน Fabric UI ก่อนเสมอ** (Notebook เสมอ + Pipeline ถ้าเลือกแบบ A) — ห้าม
   hand-write ไฟล์ item ตรงเข้า `fabric_items/` (Fabric จะสร้าง `logicalId` เองตอน commit ผ่าน UI
   ถ้า hand-write เอง จะไม่ตรงกัน ทำให้ Git sync conflict — กฎนี้ verify มาแล้วจริงจาก section 14
   findings)

2. **copy เทมเพลตด้านล่างไปวางในโน้ตบุ๊ค** แล้วแก้ให้ตรงกับแหล่งข้อมูล/table/column/กฎของ item จริง

3. **ถ้าใช้ Lakehouse**: Attach Lakehouse เป็น default lakehouse ของโน้ตบุ๊ค (เมนู lakehouse ใน
   notebook UI) — **ถ้าใช้ Warehouse**: ตั้งค่า SQL connection ตามที่เทมเพลตต้องการแทน

4. **เลือกตัวเรียกรัน — แบบ A (ผ่าน Pipeline) หรือ แบบ B (Notebook ตรงๆ)**:

   **แบบ A** — เพิ่ม Notebook Activity ใน Pipeline ให้เรียกโน้ตบุ๊คนี้ → เปิด **Settings** ของ
   activity → **Base parameters** → เพิ่ม:
   - Name: `_inlineInstallationEnabled`, Type: `Boolean`, Value: `true`

   ⚠️ ขาดไม่ได้สำหรับแบบ A — Fabric ปิด `%pip install` ไว้โดย default สำหรับ notebook ที่ถูกเรียก
   ผ่าน pipeline (ป้องกัน dependency tree ไม่คงที่ระหว่าง run) ยืนยันจริงจากการเจอ
   `MagicUsageError: %pip magic command is disabled` ตอนทำ POC — parameter นี้คือ escape hatch
   ที่ Microsoft ให้มาอย่างเป็นทางการ ([อ้างอิง](https://learn.microsoft.com/en-us/fabric/data-engineering/library-management#inline-installation))

   **แบบ B** — ไม่ต้องสร้าง Pipeline เลย เหมาะกับ item ที่ไม่มี activity อื่นต้องต่อ (เช่น ไม่ต้อง
   trigger งานอื่นก่อน/หลังเช็ค) ข้อจำกัดเรื่อง `%pip` ข้างบนระบุไว้เฉพาะ **"pipeline runs"**
   เท่านั้น — เป็นไปได้ว่าแบบ B จะไม่ติดปัญหานี้เลย แต่ **ยังไม่เคย verify จริง** ในรีโปนี้ ถ้าลองแล้ว
   ช่วยบันทึกผลกลับมาไว้ในคู่มือนี้ด้วย

5. **Commit ผ่าน Fabric Studio → Source Control** ให้ sync เข้า `fabric_items/` ในรีโปนี้

6. **เพิ่ม entry ใน `ci-config.yml`** ให้ item ใหม่เป็น `skip_check: true` พร้อม `skip_reason`
   ที่ระบุว่าเช็คผ่าน live gate แทน ไม่ใช่ static definition check (ดูตัวอย่าง entry ที่ comment
   ไว้ท้าย `ci-config.yml` ของ repo นี้)

7. **สั่งให้ CI รัน** โดยเพิ่ม entry ใน `dq-gates.yml` (`item_type: pipeline|notebook` + `stages`) — ให้ `item_type` ตรงกับที่เลือกไว้ในข้อ 4
   CI job `dq-gate-dev` / `dq-gate-staging` / `dq-gate-poc` อ่านไฟล์นี้ผ่าน `scripts/run_live_dq_stage.py` ซึ่งวนเรียก `run_live_dq_item.py`
   ทีละ gate แล้วสะสม error ท้ายสุด — ไม่ต้องแก้โค้ดหรือ workflow (รายละเอียดดูหัวข้อ 4 ด้านล่าง)
   สั่งรันมือเดี่ยวๆ ได้ด้วย `scripts/run_live_dq_item.py --workspace <GUID> --item-type <pipeline|notebook> --item-name <ชื่อ item>`

## มิติของ Data Quality (7 มิติ) — ใช้คัดเลือกว่าตารางของคุณต้องเช็คอะไรบ้าง

ไม่ต้องใช้ครบทุกมิติเสมอไป — **เลือกเฉพาะมิติที่มีความหมายกับตารางจริงของคุณ** ตัดมิติที่ไม่เกี่ยวออก
เทมเพลตโน้ตบุ๊คด้านล่างจัดกลุ่ม expectation ตามมิติพวกนี้ (เลขในคอมเมนต์ของโค้ด = เลขในตารางนี้):

| # | มิติ | คำถามที่ตอบ | GX expectation ตัวอย่าง |
|---|---|---|---|
| 1 | **Completeness** | Column สำคัญห้ามว่างใช่ไหม | `ExpectColumnValuesToNotBeNull` |
| 2 | **Uniqueness** | Key ห้ามซ้ำใช่ไหม | `ExpectColumnValuesToBeUnique` |
| 3 | **Validity** | ค่าต้องอยู่ในรูปแบบ/ช่วงที่กำหนดใช่ไหม | `ExpectColumnValuesToMatchRegex`, `ExpectColumnValuesToBeBetween` |
| 4 | **Accuracy** | ค่า 2 column ต้องสอดคล้องกันใช่ไหม | `ExpectColumnPairValuesAToBeGreaterThanB` (หรือเขียนเองถ้าซับซ้อนกว่านี้) |
| 5 | **Consistency** | ค่าต้องอยู่ในชุดที่ทีมตกลงกันไว้ใช่ไหม | `ExpectColumnValuesToBeInSet` |
| 6 | **Timeliness** | ข้อมูลต้องไม่เก่า/ไม่เป็นอนาคตเกินไปใช่ไหม | ไม่มี built-in ตรงๆ — เขียน custom function (ดู "เขียนกฎเอง" ด้านล่าง) |
| 7 | **Integrity** | ต้องมีอยู่จริงในตารางแม่ใช่ไหม (referential integrity ข้ามตาราง) | ไม่รองรับแบบ live ตรงๆ ในเทมเพลตนี้ — ต้อง query ตารางแม่มาเทียบเอง |

## เทมเพลตทั้งหมด (copy ไปแก้ต่อได้เลย)

รวมเทมเพลตของทุกไฟล์ที่ต้องแตะเวลาตั้งค่า item ใหม่ 1 ตัว — เรียงตามลำดับที่ใช้จริงในขั้นตอนด้านบน

### 1. Notebook (`notebook-content.py`) — โค้ดหลักที่ต้องเขียน

โครงสร้างอิงตาม 7 มิติมาตรฐานเดียวกับ `tests/data_quality/checkpoints/dq_TEMPLATE.yml`
(Completeness / Uniqueness / Validity / Accuracy / Consistency / Timeliness / Integrity) —
**อย่า copy ทั้งดุ้น** ตัดเหลือแค่มิติที่ item จริงต้องเช็ค แล้วเติมค่าจาก business rule จริง

```python
# ── ตั้งค่า ────────────────────────────────────────────────────────────
TABLE_NAME = "<ชื่อตาราง เช่น dqgate_sample>"

# ── ติดตั้ง GX (จำเป็นเสมอ — ไม่ preinstall มากับ Fabric runtime) ──────
%pip install "great_expectations>=1.0,<2.0"

# ── โหลดข้อมูลจากแหล่งไหน — เลือก 1 อันตามชนิด item ที่เช็ค ────────────
import great_expectations as gx

# ตัวเลือก A: Lakehouse (Spark) — attach lakehouse เป็น default lakehouse ของ notebook ก่อน
df = spark.table(TABLE_NAME).toPandas()

# ตัวเลือก B: Warehouse (SQL) — ใช้แทนบรรทัดบนถ้า item เป็น Warehouse ไม่ใช่ Lakehouse
# df = spark.read.option("url", "<connection string ของ Warehouse>") \
#     .option("dbtable", TABLE_NAME).format("com.microsoft.sqlserver.jdbc.spark") \
#     .load().toPandas()
# (หรือรัน T-SQL cell แยกแล้วส่ง DataFrame ที่ได้เข้าตัวแปร df แทนก็ได้ ขึ้นกับรูปแบบที่ทีมถนัด)

# ── เตรียม batch สำหรับ validate ──────────────────────────────────────
_ge_context = gx.get_context(mode="ephemeral")
_ge_batch_definition = (
    _ge_context.data_sources.add_pandas("pandas")
    .add_dataframe_asset(name="dq_check")
    .add_batch_definition_whole_dataframe("batch")
)
_batch = _ge_batch_definition.get_batch(batch_parameters={"dataframe": df})

# ── ประกาศ expectation ที่ต้องเช็ค (ตัดมิติที่ไม่เกี่ยวออก) ────────────
expectations = [
    # 1. Completeness — ห้าม column สำคัญว่าง
    gx.expectations.ExpectColumnValuesToNotBeNull(column="<ชื่อ column>"),

    # 2. Uniqueness — ห้าม key ซ้ำ
    # gx.expectations.ExpectColumnValuesToBeUnique(column="<ชื่อ column key>"),

    # 3. Validity — ค่าต้องอยู่ในช่วง/รูปแบบที่กำหนด
    # gx.expectations.ExpectColumnValuesToBeBetween(column="<column>", min_value=0, max_value=100),
    # gx.expectations.ExpectColumnValuesToMatchRegex(column="<column>", regex="^0[0-9]{9}$"),

    # 4. Accuracy — ค่า 2 column ต้องสอดคล้องกัน (GX เช็คตรงๆ ให้ไม่ได้ ทำได้แค่ประมาณแบบนี้)
    # gx.expectations.ExpectColumnPairValuesAToBeGreaterThanB(column_A="<a>", column_B="<b>", or_equal=True),

    # 5. Consistency — ค่าต้องอยู่ในชุดที่ตกลงกันไว้
    # gx.expectations.ExpectColumnValuesToBeInSet(column="<column>", value_set=["new", "qualified"]),

    # 6. Timeliness — เช็คว่าค่า max ของ column วันที่อยู่ในช่วงที่ยอมรับได้
    # gx.expectations.ExpectColumnMaxToBeBetween(column="<column>", min_value="2026-01-01", max_value="2026-12-31"),

    # 7. Integrity — referential integrity ข้ามตาราง GX เช็คแบบ live ตรงๆ ยังไม่รองรับในเทมเพลตนี้
    # ต้อง query ตารางแม่มาก่อนแล้วเทียบเอง
]

# ── รันเช็คทุกกฎ + สรุปผล ──────────────────────────────────────────────
results = [_batch.validate(e) for e in expectations]
all_passed = all(r.success for r in results)

for expectation, result in zip(expectations, results):
    status = "PASS" if result.success else "FAIL"
    print(f"[{status}] {expectation}")

if not all_passed:
    raise AssertionError("Data quality check failed — ดูรายละเอียดที่ log ด้านบน")
```

**สิ่งที่ต้องแก้เสมอ**:
- `TABLE_NAME` และ column ทุกตัวใน `expectations`
- ลบ comment กฎที่ไม่เกี่ยวออก แล้ว uncomment กฎที่ต้องใช้จริง (threshold/regex/value_set ต้องมาจาก
  คนที่รู้ business rule ของ item นั้น เดาเองไม่ได้)
- **`raise AssertionError` ต้องอยู่** — นี่คือจุดที่ทำให้ pipeline job fail จริง ถ้าตัดออกกลไก gate
  จะไม่ทำงาน (เช็คแล้ว print ผลเฉยๆ ไม่พอ)

### 2. Pipeline Activity (`pipeline-content.json`) — ใช้เฉพาะแบบ A

⚠️ **ห้าม copy JSON นี้ไปวางไฟล์ตรงๆ** — สร้าง Notebook Activity ผ่าน Fabric UI เสมอ (กฎ UI-first
ข้อ 1 ด้านบน) ใช้ตรงนี้แค่เป็น**ตัวอ้างอิงเทียบผล** ว่าไฟล์ที่ sync เข้ามาหลัง commit ผ่าน UI แล้ว
ควรมีหน้าตาประมาณนี้ (โดยเฉพาะ parameter `_inlineInstallationEnabled` ที่ต้องมี):

```json
{
  "properties": {
    "activities": [
      {
        "type": "TridentNotebook",
        "typeProperties": {
          "notebookId": "<GUID ของ notebook ที่สร้างไว้ในข้อ 1 — Fabric ใส่ให้เองหลัง sync>",
          "workspaceId": "00000000-0000-0000-0000-000000000000",
          "parameters": {
            "_inlineInstallationEnabled": {
              "value": true,
              "type": "bool"
            }
          }
        },
        "policy": {
          "timeout": "0.12:00:00",
          "retry": 0,
          "retryIntervalInSeconds": 30,
          "secureInput": false,
          "secureOutput": false
        },
        "name": "<ชื่อ activity ที่ตั้งใน UI>",
        "dependsOn": []
      }
    ]
  }
}
```

ถ้า sync เข้ามาแล้วไม่มี key `parameters`/`_inlineInstallationEnabled` แปลว่าลืมตั้งค่า Base
parameter ในข้อ 4 (แบบ A) — กลับไปเพิ่มผ่าน UI แล้ว commit ใหม่

### 3. `ci-config.yml` — entry ให้ item ใหม่

เพิ่มต่อท้ายไฟล์ (1 entry ต่อ item ที่ sync เข้ามา — Notebook + Pipeline ถ้าใช้แบบ A, Lakehouse
ถ้ามี table ทดสอบที่ไม่มี schema contract จริงให้เช็ค — ดูส่วนที่ 2 ถ้าอยากทำ schema contract จริง
แทนที่จะ skip):

```yaml
<ชื่อ_notebook_item>:
  skip_check: true
  skip_reason: >-
    Live DQ check item (<วันที่ตั้งค่า>) — เช็คผ่าน live gate (scripts/run_live_dq_item.py)
    แทน ไม่ใช่ static definition check ดู docs/check-patterns-guide.md

<ชื่อ_pipeline_item>:   # ตัดออกถ้าใช้แบบ B (ไม่มี pipeline)
  skip_check: true
  skip_reason: >-
    Live DQ check item (<วันที่ตั้งค่า>) คู่กับ <ชื่อ_notebook_item> — ดูเหตุผลเดียวกัน

<ชื่อ_lakehouse_item>:   # ตัดออกถ้าไม่มี table ทดสอบใหม่ หรือมี schema contract จริงให้เช็คแล้ว
  skip_check: true
  skip_reason: >-
    Live DQ check item (<วันที่ตั้งค่า>) — ไม่มี schema contract จริงให้เช็คตอนนี้
```

### 4. `dq-gates.yml` — ลงทะเบียน gate ให้ CI สั่งรัน (ไม่ต้องแก้ `fabric-ci.yml`)

workflow มี job live gate ครบแล้ว 3 ตัว (`dq-gate-dev`, `dq-gate-staging`, `dq-gate-poc`) แต่ละตัวเรียก
`scripts/run_live_dq_stage.py --stage <dev|staging|prod>` ซึ่งอ่านรายชื่อ gate จาก `dq-gates.yml` —
**เพิ่ม gate ใหม่ = เพิ่ม entry ใน `dq-gates.yml` เท่านั้น**:

```yaml
<ชื่อ_item>:            # ต้องตรงชื่อ item ใน Fabric เป๊ะ
  item_type: pipeline   # หรือ notebook (แบบ B รัน notebook ตรงๆ ไม่ผ่าน pipeline)
  stages: [dev, staging, prod]
```

- `stages` เลือกได้ว่า gate นี้รันที่ไหน — `dev` = ก่อน deploy ไป staging (ตอนเปิด PR), `staging` = ก่อน deploy ไป prod,
  `prod` = ยืนยันหลัง deploy (`dq-gate-poc`) ปกติใส่ครบทั้งสามถ้า item อ่านข้อมูลที่มีในทุก environment
- workspace ID ของแต่ละ stage อ่านจาก `workspace-config.yml` — ถ้ามี gate แต่ GUID ยังเป็น `<placeholder>` สคริปต์ **fail** ไม่ปล่อยผ่านเงียบๆ
- item ต้องถูก deploy/sync ไปอยู่ใน workspace ของ stage นั้นก่อนถึงรันได้ (ลำดับ job ดู `docs/staging-gate.md`)
- ตั้ง required status check `dq-gate-dev` และ `dq-gate-staging` บน `main` ถึงจะบล็อก merge ได้จริง (ดู `docs/staging-gate.md`)

ทดสอบก่อนใช้จริงทั้งเคสข้อมูลดี/เสีย (ดูหัวข้อทดสอบด้านล่าง) — หรือรันมือด้วย `workflow_dispatch` (รันเฉพาะ `dq-gate-poc` ที่ prod)

## เลือก GX expectation ได้จากไหนบ้าง

ไม่ได้จำกัดแค่ตัวอย่างในเทมเพลตด้านบน — GX มี built-in expectation ให้เลือกเป็นร้อยตัว ดูรายชื่อ
เต็มได้ที่ https://greatexpectations.io/expectations/ ชื่อใน Python ใช้ PascalCase (เช่น
`ExpectColumnValuesToBeOfType`) ตรงกับ class ใน `gx.expectations`

## ถ้ากฎที่ต้องการไม่มี built-in ให้เลย — เขียนกฎเอง

มี 2 ทาง เลือกตามความซับซ้อนของกฎ:

### ทางที่ 1 (แนะนำ) — เขียน check function ธรรมดา ไม่ต้องพึ่ง GX framework

เหมาะกับ**เกือบทุกกรณีที่เจอจริง** — เขียนฟังก์ชัน Python/pandas เช็คเงื่อนไขเอง แล้วเอาผลไป
เข้า flow เดียวกับ GX expectation (print `[PASS]`/`[FAIL]` + นับรวมกับ `all_passed`) ไม่ต้องแตะ
internal API ของ GX เลย ความเสี่ยง syntax ผิดเกือบเป็นศูนย์เพราะเป็นแค่ pandas ธรรมดา:

```python
# ตัวอย่าง custom rule: "ยอดขายต่อวันห้ามเกิน 3 เท่าของค่าเฉลี่ย 7 วันย้อนหลัง" (ไม่มี built-in ตรงๆ)
def check_no_sales_spike(pdf, column="sales_amount", window=7, max_multiplier=3):
    rolling_avg = pdf[column].rolling(window=window, min_periods=1).mean()
    violations = pdf[pdf[column] > rolling_avg * max_multiplier]
    return len(violations) == 0, violations

custom_passed, violation_rows = check_no_sales_spike(df)
print(f"[{'PASS' if custom_passed else 'FAIL'}] check_no_sales_spike ({len(violation_rows)} แถวผิดปกติ)")
all_passed = all_passed and custom_passed   # รวมเข้ากับผลของ GX expectations ด้านบน
```

วางต่อท้าย loop `for expectation, result in zip(...)` ในเทมเพลตได้เลย แล้วให้ `all_passed` ตัวเดียว
คุม `raise AssertionError` ทั้งหมด (ทั้งจาก GX expectation และจาก custom check)

### Syntax ที่ต้องระวังตอนเขียน custom check function

Pattern ทั่วไป:

```python
def check_<ชื่อกฎ>(pdf, <parameter เพิ่มเติมถ้ามี>):
    violations = pdf[<เงื่อนไข pandas ที่กรองเอาเฉพาะแถวที่ "ผิดกฎ">]
    return len(violations) == 0, violations
```

- `pdf[condition]` = กรองเอาเฉพาะแถวที่ `condition` เป็น `True`
- ถ้าเงื่อนไขหลายอัน ต้องใส่วงเล็บแต่ละอันแล้วเชื่อมด้วย `&` (and) หรือ `|` (or) — **ห้ามใช้ `and`/`or`
  ธรรมดากับทั้ง column** (จะ error `ValueError: truth value of a Series is ambiguous`)
- ไม่มีแถวผิดกฎ → `violations` เป็น Empty DataFrame → `len(violations) == 0` → `True` → ผ่าน
- ตัวเลขหลักพัน/ล้าน ห้ามใช้ comma (`1,000,000` จะกลายเป็น tuple) ใช้ underscore แทน (`1_000_000`)

### ทางที่ 2 — เขียนเป็น GX Custom Expectation class จริงๆ

เหมาะถ้าอยากได้กฎที่ reuse ข้ามหลาย notebook/item ในรูปแบบเดียวกับ built-in (เรียกผ่าน
`gx.expectations.<ชื่อกฎ>(...)` เหมือนกฎอื่น) — รูปแบบที่ GX เอกสารไว้ (subclass
`ColumnMapExpectation` + `ColumnMapMetricProvider`):

```python
from great_expectations.expectations.expectation import ColumnMapExpectation
from great_expectations.expectations.metrics.map_metric_provider import (
    ColumnMapMetricProvider,
    column_condition_partial,
)
from great_expectations.execution_engine import PandasExecutionEngine

class ColumnValuesToBeEven(ColumnMapMetricProvider):
    condition_metric_name = "column_values.even"

    @column_condition_partial(engine=PandasExecutionEngine)
    def _pandas(cls, column, **kwargs):
        return column % 2 == 0

class ExpectColumnValuesToBeEven(ColumnMapExpectation):
    map_metric = "column_values.even"
    success_keys = ("mostly",)
```

⚠️ **ยังไม่เคย verify จริงกับ GX เวอร์ชันที่ pin ไว้ในรีโปนี้ (`great_expectations>=1.0,<2.0`)** —
import path พวกนี้เป็นรูปแบบที่ GX เอกสารไว้สาธารณะ แต่รีโปนี้เคยเจอมาแล้วว่า docs กับ source code
ของเวอร์ชันที่ติดตั้งจริงไม่ตรงกันได้ (เช่นเคสของ `fabric-cicd` parameter.yml ใน section 14
findings) — **ก่อนใช้จริงให้เช็ค `python -c "import great_expectations; help(great_expectations.expectations.expectation)"`
กับเวอร์ชันที่ติดตั้งจริงก่อนเสมอ** อย่าเชื่อ syntax นี้เปล่าๆ

โดยรวม **แนะนำทางที่ 1** สำหรับรีโปนี้ เพราะเรียบง่ายกว่า verify ง่ายกว่า และครอบคลุม use case ที่
เจอจริงได้หมดโดยไม่ต้องพึ่งความเข้าใจ internal ของ GX เลย

## ปัญหาที่เจอจริงระหว่างทำ POC (และวิธีแก้)

รายละเอียดเต็มอยู่ใน `DataOps-CICD-Workflow.md` section 14 Phase 7 สรุปสั้นๆ ที่ต้องรู้ก่อนเริ่ม:

| ปัญหา | วิธีแก้ |
|---|---|
| `ModuleNotFoundError: No module named 'great_expectations'` | ไม่ preinstall มากับ Fabric runtime — ต้อง `%pip install` เสมอ (มีอยู่ในเทมเพลตแล้ว) |
| `MagicUsageError: %pip magic command is disabled` ตอนรันผ่าน Pipeline | ต้องเพิ่ม parameter `_inlineInstallationEnabled: true` ที่ Notebook Activity (ดูขั้นตอนที่ 4 ด้านบน) — ห้ามลืม |
| อยากใช้ Fabric Environment แทน `%pip` (ให้ reproducible กว่า) | ลองแล้วในเทนแนนต์นี้ UI "Custom libraries" ของ Environment item มีแค่ upload .whl/.jar/.tar.gz ไม่มีช่องพิมพ์ชื่อ public package ตรงๆ ทั้ง All/Full mode — ยังไม่มีทางทำได้ง่ายๆ ในตอนนี้ ใช้ `_inlineInstallationEnabled` ไปก่อน |

## วิธีตรวจว่าเช็คผ่านไหม

- **ดูตรงจาก Fabric**: Monitoring Hub → run ของ pipeline → สถานะ `Succeeded`/`Failed` + เปิด log
  ของ Notebook Activity ดูบรรทัด `[PASS]`/`[FAIL]` ต่อกฎ
- **ดูผ่าน CI** (ถ้าต่อ `run_live_dq_item.py` ไว้): job status เขียว/แดงตรงกับผลจริง, log มี JSON
  เต็มของ job instance + บรรทัดสรุปว่า "live data_quality gate ผ่าน" หรือ `::error::...`

ทดสอบทั้ง 2 เคสเสมอก่อนถือว่า item พร้อมใช้จริง: ข้อมูลดี → ต้อง `Succeeded`, ทำข้อมูลเสีย 1 แถว
ชั่วคราว (เช่น `UPDATE table SET col = NULL WHERE id = X`) → รันซ้ำ → ต้อง `Failed` จริง ก่อนคืนค่า
ข้อมูลกลับ

## ไฟล์ที่เกี่ยวข้องทั้งหมด (ใน repo นี้)

| ไฟล์ | หน้าที่ |
|---|---|
| `scripts/run_live_dq_item.py` | สั่งรัน pipeline/notebook ผ่าน Fabric REST API + poll ผล + exit code |
| `ci-config.yml` | ที่ที่ต้องเพิ่ม entry `skip_check` ให้ item ที่เช็คผ่าน live gate (ดูตัวอย่าง comment ท้ายไฟล์) |
| `scripts/run_live_dq_stage.py` | อ่าน `dq-gates.yml` แล้ววน `run_live_dq_item.py` ให้ทุก gate ของ stage นั้น |
| `dq-gates.yml` | ลงทะเบียน gate (item + stages dev/staging/prod) — เพิ่ม gate แก้ไฟล์นี้ไฟล์เดียว |
| `.github/workflows/fabric-ci.yml` | job `dq-gate-dev` / `dq-gate-staging` / `dq-gate-poc` (ดู `docs/staging-gate.md`) |
| `workspace-config.yml` | workspace GUID ของ environment ที่ job นี้จะเช็ค |

ตัวอย่าง item จริงที่ proof กลไกนี้แล้ว (Notebook/Pipeline/Lakehouse คู่กัน + findings log เต็ม)
อยู่ใน `dataops-fabric-pilot` (repo แยก) และ `DataOps-CICD-Workflow.md` section 14 Phase 7 — ไม่ได้
อยู่ใน repo นี้ เพราะ repo นี้เป็น starting point เปล่าที่ยังไม่มี item จริง

---

# ส่วนที่ 2 — Schema Contract Check

เช็คว่า Lakehouse/Warehouse item มี **schema contract** (ประกาศ table/column/type ที่คาดหวังไว้)
ครบและ format ถูกต้องไหม — ตรงกับ check pattern `schema` (1 ใน 5 pattern เดิมของ `ci-config.yml`
ต่างจาก Live DQ ในส่วนที่ 1 ซึ่งเป็นกลไกแยกนอกระบบ pattern)

## ข้อจำกัดที่ต้องรู้ก่อนใช้

**เช็คได้แค่ "มี contract ประกาศไว้ไหม + format ถูกไหม" เท่านั้น — ไม่ได้เทียบกับ schema จริงบน
Fabric** เพราะ Fabric Git Integration ไม่ sync ข้อมูล table/column ของ Lakehouse/Warehouse มาให้
เลย (ตรวจสอบแล้ว — item ที่ sync ลงมามีแค่ `.platform`, `alm.settings.json`,
`lakehouse.metadata.json` ที่เป็นแค่ `{"defaultSchema": "dbo"}`/`{}`, กับ `shortcuts.metadata.json`
— ไม่มี column ไหนอยู่ในนั้นเลย) เหตุผลเดียวกับที่ pattern เดิม 5 ตัวต้องเป็น static check ทั้งหมด
(`test` job รันก่อน deploy เสมอ ไม่มี Fabric ให้เช็คสด — ดู `CLAUDE.md`)

ถ้าต้องการเช็คกับ schema จริงบน Fabric ต้องทำเป็น **live check** แยกต่างหาก (pattern เดียวกับ
ส่วนที่ 1 — Notebook อ่าน schema จริงมาเทียบ) ซึ่งไม่ใช่ scope ของ pattern `schema` นี้

## รูปแบบ contract (เทมเพลต — copy ไปแก้ต่อได้เลย)

ไฟล์: `tests/schema/<item_name>.yml` — ชื่อไฟล์ต้องตรงชื่อ item เป๊ะ (เหมือน pattern ของ
`tests/unit/test_<name>.py` และ `tests/data_quality/checkpoints/dq_<name>.yml`)

มี stub พร้อม copy ไปแก้ต่อแล้วที่ `tests/schema/_TEMPLATE.yml` — ไม่ต้องพิมพ์ตามจาก
markdown นี้เอง:

```yaml
tables:
  <table_name>:
    columns:
      - name: <column_name>
        type: <string|int|bigint|double|float|boolean|date|timestamp>
      - name: <column_name_2>
        type: <...>
  # เพิ่ม table อื่นในรูปแบบเดียวกันได้ ถ้า Lakehouse/Warehouse นั้นมีหลายตาราง
```

## ขั้นตอนตั้งค่าให้ item ใหม่

1. copy `tests/schema/_TEMPLATE.yml` ไปตั้งชื่อใหม่เป็น `tests/schema/<item_name>.yml`
   (ต้องตรงชื่อ item เป๊ะ) — เติม table/column/type ให้ตรงกับ business schema จริงของ item นั้น
   (ต้องรู้จริง เดาไม่ได้ — ถ้าไม่รู้ column จริง ให้คงไว้ที่ `skip_check: true` ใน `ci-config.yml` ก่อน)
2. เอา `skip_check: true` ออกจาก entry ของ item นั้นใน `ci-config.yml` (หรือถ้ายังไม่มี entry เลย
   ไม่ต้องเพิ่มอะไร — `schema` เป็น default ของ Lakehouse/Warehouse อยู่แล้วใน `_defaults`)
3. รันเช็คในเครื่องก่อน push: `python scripts/validate_schema_contract.py "fabric_items/<item folder>/"`
   (ต้องมี trailing slash เหมือนที่ `fabric-ci.yml` ส่งเข้าไปจริง)

## วิธีตรวจว่าเช็คผ่านไหม

รันตรงในเครื่อง (ไม่ต้องมี Fabric credential เลย เพราะเป็น static check ล้วนๆ):

```
python scripts/validate_schema_contract.py "fabric_items/<item_name>.Lakehouse/"
```

- **ผ่าน**: print `[validate_schema_contract] ... OK` ทุก column + `... ผ่าน (N table)` จบด้วย
  exit code 0
- **ไม่ผ่าน**: print รายการปัญหาที่เจอทั้งหมด (ไม่ใช่แค่จุดแรก) เช่น "ไม่พบ schema contract",
  "column ไม่มี name", "type ไม่รู้จัก" แล้ว exit code 1

## ไฟล์ที่เกี่ยวข้องทั้งหมด

| ไฟล์ | หน้าที่ |
|---|---|
| `tests/schema/_TEMPLATE.yml` | stub พร้อม copy ไปตั้งชื่อ `<item_name>.yml` |
| `scripts/validate_schema_contract.py` | ตัวเช็ค — validate ว่า contract มีอยู่จริงและ format ถูก |
| `ci-config.yml` | `_defaults.Lakehouse`/`_defaults.Warehouse: schema` — item ไหนยังไม่มี contract ให้คง `skip_check: true` ไว้ |
| `.github/workflows/fabric-ci.yml` | case `schema)` ใน job `test` เรียก `validate_schema_contract.py` |

---

# ส่วนที่ 3 — `unit_test` pattern

Pattern default ของ Notebook ทุกตัว (`_defaults.Notebook: unit_test` ใน `ci-config.yml`) — รัน
pytest เทียบ logic ของ Notebook กับ mock DataFrame ที่เขียนขึ้นเอง **ไม่แตะ Fabric จริงเลย**
(เป็น static check เหมือน `structure`/`schema` — รันก่อน deploy ได้ปกติ)

## แนวคิด

Notebook เขียนโค้ดเป็น**ฟังก์ชัน** (ไม่ใช่ script รันทื่อๆ ทั้งไฟล์) แล้ว test import ฟังก์ชันนั้น
มาทดสอบกับ input ปลอมที่ควบคุมเอง — วิธีนี้ทดสอบ **logic** ได้จริง (เช่น "ถ้า input แบบนี้ output
ต้องเป็นแบบนี้") แต่ทดสอบ**ข้อมูลจริง**ไม่ได้ (นั่นคือหน้าที่ของ Live DQ Gate ในส่วนที่ 1 แทน)

## เทมเพลต (copy ไปแก้ต่อได้เลย)

ไม่ต้องพิมพ์ตามจาก markdown — มี stub พร้อม copy ให้แล้วทั้ง 2 แบบ ใต้ `tests/unit/`:

| ใช้เมื่อ... | ไฟล์เทมเพลต |
|---|---|
| เทส transform logic ทั่วไปของ Notebook | `tests/unit/_TEMPLATE_unit_test.py` |
| เทส "DQ rule function" โดยเฉพาะ (1 ฟังก์ชัน = 1 กฎ เช็คข้อมูล ไม่ใช่ transform ทั่วไป) | `tests/unit/_TEMPLATE_dq_rule_check.py` (มีคำอธิบายทั้งฝั่ง notebook และฝั่ง test ในไฟล์เดียว) |

copy ไฟล์ที่ตรงกับ item ของคุณ ไปตั้งชื่อ **`tests/unit/test_<item_name>.py`** (ต้องตรงชื่อ Notebook
item เป๊ะ ไม่งั้น CI หาไม่เจอ error ทันที) แล้วแก้:
- `_NOTEBOOK_PATH` ให้ตรง path ของ Notebook item จริง
- `my_check_function` เป็นชื่อฟังก์ชันจริงที่ Notebook นั้นประกาศไว้ (ต้อง refactor โค้ด Notebook
  ให้เป็นฟังก์ชันก่อน ถ้ายังเป็น script เปลือยๆ ทั้งไฟล์อยู่ — import แบบนี้จะรันทั้งไฟล์ทันทีตอน
  `exec_module()` ซึ่งอาจ error ถ้ามีโค้ดที่พึ่ง `spark`/`notebookutils` อยู่นอกฟังก์ชัน)
- เขียน test case ให้ครอบคลุมทั้งเคสผ่านและเคส fail อย่างน้อยอย่างละ 1 เคส

## ข้อควรรู้

`ci-config.yml` มี fail-safe: ถ้า item ไหนไม่มี entry และไม่มี `_defaults` ตรงกับ type — fallback
เป็น `unit_test` เสมอ (เข้มสุด) แปลว่า **Notebook ใหม่ทุกตัวต้องมี `tests/unit/test_<name>.py`
ตั้งแต่วันแรก** ไม่งั้น CI fail ทันที (`::error::[$name] check=unit_test but no test found`)

---

# ส่วนที่ 4 — `structure` pattern

Pattern default ของ Data Pipeline ทุกตัว (`_defaults.DataPipeline: structure`) — **ไม่มีเทมเพลต
ให้ copy ต่อ item** เพราะเป็น script กลางตัวเดียว (`scripts/validate_pipeline_structure.py`) ที่
ทำงานอัตโนมัติกับทุก Data Pipeline โดยไม่ต้องเขียนอะไรเพิ่มเลย

## ทำงานยังไง

เช็คว่า activity ในไฟล์ `pipeline-content.json` ที่อ้างอิงถึง item อื่น (ผ่าน key เช่น
`notebookId`/`dataflowId`/`pipelineId` ใน `typeProperties`) ชี้ไปที่ `logicalId` ที่มี item จริง
ประกาศไว้ใน `fabric_items/` (สแกนจาก `.platform` ทุกไฟล์แบบ recursive) ไหม — ถ้า pipeline ชี้ไปหา
item ที่ไม่มีอยู่จริง (dangling reference) ถือว่า structure ผิด

## เมื่อไหร่ต้องทำอะไรเพิ่ม

**ปกติไม่ต้องทำอะไรเลย** — สร้าง Pipeline ผ่าน UI ตามปกติ (กฎ UI-first เหมือนเดิม) แล้ว sync เข้า
git ตัว validator จะเช็คให้เองอัตโนมัติ ต้องเข้าไปแก้ก็ต่อเมื่อ:
- เพิ่ม activity type ใหม่ที่มี reference key ไม่อยู่ในชุดที่รู้จัก (`REFERENCE_KEYS` ในไฟล์
  `validate_pipeline_structure.py`) — เพิ่ม key นั้นเข้าไปใน tuple ได้เลย
- Pipeline ไม่มี activity เลย (ตั้งใจทำ pipeline เปล่า) — จะ fail เพราะ validator ถือว่า pipeline
  ต้องมีอย่างน้อย 1 activity เสมอ ถ้าตั้งใจจริงต้องใช้ `skip_check: true` แทน

## ไฟล์ที่เกี่ยวข้อง

| ไฟล์ | หน้าที่ |
|---|---|
| `scripts/validate_pipeline_structure.py` | ตัวเช็คเดียว ใช้กับทุก Data Pipeline |
| `.github/workflows/fabric-ci.yml` | case `structure)` ใน job `test` |

---

# ส่วนที่ 5 — `data_quality` (CSV) pattern เดิม

## กลไก

อ่านไฟล์ CSV fixture ที่ commit ไว้ใน repo ผ่าน `scripts/run_data_quality_checkpoint.py` แล้ว
validate ด้วย GX — รูปแบบ config (`tests/data_quality/checkpoints/dq_<name>.yml`):

```yaml
data_file: tests/data_quality/fixtures/<ชื่อไฟล์>.csv
dtype:
  <column>: str
expectations:
  - expectation_type: expect_column_values_to_not_be_null
    kwargs:
      column: <column>
```

มี stub พร้อม copy ที่ `tests/data_quality/checkpoints/dq_TEMPLATE.yml` (ครบ 7 มิติ) และ worked
example PASS/FAIL ที่ `dq_selftest_good.yml`/`dq_selftest_bad.yml` คู่กับ fixture CSV ในโฟลเดอร์
`tests/data_quality/fixtures/` — รันทดสอบได้เลย:

```
python scripts/run_data_quality_checkpoint.py dq_selftest_good   # ต้อง PASS ทุกกฎ
python scripts/run_data_quality_checkpoint.py dq_selftest_bad    # ต้อง FAIL หลายกฎ (ดู comment ในไฟล์ว่า fail จุดไหนเพราะอะไร)
```

## ก่อนใช้เป็น default จริงบน item ที่สำคัญ

⚠️ **สถานะยังไม่ฟันธง** (ดู `DataOps/CLAUDE.md` 2026-09-28) — เช็คก่อนว่ามี workspace/ทีมอื่นใน
องค์กรใช้ไฟล์ CSV แบบนี้เป็นส่วนหนึ่งของ workflow อยู่แล้วไหม (เช่น pipeline อื่นที่อ่าน/เขียน CSV
เป็นปกติ) — ถ้ามี อาจกระทบ/ซ้อนทับกับของที่มีอยู่แล้ว ถ้าไม่มีก็ใช้ได้ตามปกติ ยังไม่มีข้อห้ามทาง
เทคนิคอะไรที่บังคับให้เปลี่ยนรูปแบบไฟล์ — ทุกไฟล์ในกลไกนี้มี banner เตือนสถานะนี้ไว้ที่ top comment
แล้ว ไม่ต้องรอ merge branch แยกต่างหากอีกต่อไป แค่คุยกับทีมยืนยันก่อนเอา `skip_check: true` ออกจาก
item จริงใน `ci-config.yml`

---

# ส่วนที่ 6 — `none` pattern

ตรงไปตรงมาที่สุด — ประกาศว่า item นี้**ไม่ต้องเช็คอะไรเลย โดยตั้งใจ** ไม่มีเทมเพลตเพราะไม่มีอะไรให้
เขียน

```yaml
<item_name>:
  check: none
```

## ต่างจาก `skip_check: true` ยังไง

| | `check: none` | `skip_check: true` |
|---|---|---|
| ความหมาย | ไม่มี check ที่ควรทำเลย (ตั้งใจแบบถาวร) | มี check pattern ที่ "ควรจะ" ทำอยู่ (ระบุไว้ใน `_defaults`/entry) แต่ตอนนี้ยังไม่ทำ |
| ต้องมี reason ไหม | ไม่ต้อง | **ต้องมี** `skip_reason` เสมอ (ไม่งั้น CI fail) |
| ใช้เมื่อไหร่ | item ที่ไม่มีทางมี check ที่มีความหมายเลย (เช่น item ทดลองที่จะลบทิ้งเร็วๆ นี้) | item ที่ "ควรมี" check แต่ยังไม่ได้เขียน (หนี้ทางเทคนิคที่ต้องกลับมาทำ) |

โดยทั่วไปแนะนำใช้ `skip_check: true` มากกว่า เพราะยังคง label ไว้ว่า item นี้ "เป็นหนี้" check
อะไรอยู่ (เห็นได้จาก Job Summary table) ต่างจาก `check: none` ที่ทำให้ดูเหมือนไม่มีอะไรต้องทำเลย