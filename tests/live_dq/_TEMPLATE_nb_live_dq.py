# TEMPLATE — Notebook สำหรับ Live Data Quality Check (GX รันบนข้อมูลจริงใน Fabric/Spark)
# ไม่ใช่ test ของ pytest และไม่ถูก deploy เอง — ไฟล์นี้อยู่นอก fabric_items/ ตั้งใจ เพราะ deploy.py
# จะ publish ทุกอย่างใน fabric_items/ ขึ้น workspace จริง (ดู tests/live_dq/README.md)
# ชื่อขึ้นต้น _TEMPLATE ไม่ตรง pattern ที่ pytest เก็บ (test_*.py / *_test.py) จึงไม่ถูกรันใน CI
#
# ขั้นตอนใช้งาน (รายละเอียดเต็มที่ tests/live_dq/README.md และ docs/check-patterns-guide.md ส่วนที่ 1):
#   1. สร้าง Notebook ผ่าน Fabric UI ก่อนเสมอ (ห้าม hand-write ไฟล์ item เข้า fabric_items/)
#   2. copy โค้ดด้านล่างไปวางทีละ cell ใน Notebook แล้วแก้ TABLE_NAME / column / expectation
#      — บรรทัด "# MAGIC %pip ..." ให้ลบ "# MAGIC " ออกเหลือ "%pip ..." ตอนวางใน cell จริง
#      (ใส่ # MAGIC ไว้เพื่อให้ไฟล์นี้ยังเป็น Python ที่ parse ผ่าน)
#   3. Attach Lakehouse เป็น default lakehouse ของ Notebook (ถ้าใช้ตัวเลือก A)
#   4. เพิ่ม entry skip_check ใน ci-config.yml + เพิ่ม entry ใน dq-gates.yml
#
# ตัดมิติ DQ ที่ไม่เกี่ยวกับตารางจริงออก — อย่า copy ทั้งดุ้น และ threshold/regex/value_set ต้องมาจาก
# คนที่รู้ business rule ของตารางนั้น เดาเองไม่ได้
#
# สถานะ: เทมเพลตนี้เรียบเรียงจากตัวอย่างใน docs/check-patterns-guide.md (กลไกแบบเดียวกับที่พิสูจน์แล้วใน
# dataops-fabric-pilot, แบบ A + Lakehouse) — ไฟล์นี้เองยังไม่เคยรันบน Fabric จริง

# ── Cell 1: ตั้งค่า ──────────────────────────────────────────────────────
TABLE_NAME = "<ชื่อตาราง เช่น dqgate_sample>"

# ── Cell 2: ติดตั้ง GX (จำเป็นเสมอ — ไม่ preinstall มากับ Fabric runtime) ──
# ถ้ารันผ่าน Pipeline (แบบ A) ต้องตั้ง Base parameter _inlineInstallationEnabled=true (Boolean)
# ที่ Notebook Activity ไม่งั้นเจอ MagicUsageError: %pip magic command is disabled
# MAGIC %pip install "great_expectations>=1.0,<2.0"

# ── Cell 3: โหลดข้อมูลจริง — เลือก 1 อันตามชนิด item ที่เช็ค ──────────────
import great_expectations as gx

# ตัวเลือก A: Lakehouse (Spark) — attach lakehouse เป็น default lakehouse ของ notebook ก่อน
df = spark.table(TABLE_NAME).toPandas()  # noqa: F821  (spark มีให้ใน Fabric Notebook)

# ตัวเลือก B: Warehouse (SQL) — ใช้แทนบรรทัดบนถ้า item เป็น Warehouse
# df = spark.read.option("url", "<connection string ของ Warehouse>") \
#     .option("dbtable", TABLE_NAME).format("com.microsoft.sqlserver.jdbc.spark") \
#     .load().toPandas()

# ── Cell 4: เตรียม batch + ประกาศ expectation ────────────────────────────
_ge_context = gx.get_context(mode="ephemeral")
_ge_batch_definition = (
    _ge_context.data_sources.add_pandas("pandas")
    .add_dataframe_asset(name="dq_check")
    .add_batch_definition_whole_dataframe("batch")
)
_batch = _ge_batch_definition.get_batch(batch_parameters={"dataframe": df})

expectations = [
    # 1. Completeness — ห้าม column สำคัญว่าง
    gx.expectations.ExpectColumnValuesToNotBeNull(column="<ชื่อ column>"),

    # 2. Uniqueness — ห้าม key ซ้ำ
    # gx.expectations.ExpectColumnValuesToBeUnique(column="<ชื่อ column key>"),

    # 3. Validity — ค่าต้องอยู่ในช่วง/รูปแบบที่กำหนด
    # gx.expectations.ExpectColumnValuesToBeBetween(column="<column>", min_value=0, max_value=100),
    # gx.expectations.ExpectColumnValuesToMatchRegex(column="<column>", regex="^0[0-9]{9}$"),

    # 4. Accuracy — ค่า 2 column ต้องสอดคล้องกัน
    # gx.expectations.ExpectColumnPairValuesAToBeGreaterThanB(column_A="<a>", column_B="<b>", or_equal=True),

    # 5. Consistency — ค่าต้องอยู่ในชุดที่ตกลงกันไว้
    # gx.expectations.ExpectColumnValuesToBeInSet(column="<column>", value_set=["new", "qualified"]),

    # 6. Timeliness — ค่า max ของ column วันที่ต้องอยู่ในช่วงที่ยอมรับได้
    # gx.expectations.ExpectColumnMaxToBeBetween(column="<column>", min_value="2026-01-01", max_value="2026-12-31"),

    # 7. Integrity — referential integrity ข้ามตาราง GX เช็คแบบ live ตรงๆ ไม่ได้ในเทมเพลตนี้
    #    ต้อง query ตารางแม่มาเทียบเองด้วย custom check function (ดูด้านล่าง)
]

# ── Cell 5: รันทุกกฎ + สรุปผล ────────────────────────────────────────────
results = [_batch.validate(e) for e in expectations]
all_passed = all(r.success for r in results)

for expectation, result in zip(expectations, results):
    status = "PASS" if result.success else "FAIL"
    print(f"[{status}] {expectation}")

# (ทางเลือก) custom rule ที่ GX ไม่มี built-in — เขียนเป็น pandas ธรรมดาแล้วรวมเข้า all_passed
# def check_<ชื่อกฎ>(pdf):
#     violations = pdf[<เงื่อนไข pandas ที่กรองเอาเฉพาะแถวที่ "ผิดกฎ">]
#     return len(violations) == 0, violations
#
# custom_passed, violation_rows = check_<ชื่อกฎ>(df)
# print(f"[{'PASS' if custom_passed else 'FAIL'}] check_<ชื่อกฎ> ({len(violation_rows)} แถวผิดกฎ)")
# all_passed = all_passed and custom_passed

# ⚠️ ห้ามลบ raise นี้ — คือจุดเดียวที่ทำให้ job instance Failed จริง แล้ว run_live_dq_item.py
# กับ CI เห็น ถ้าแค่ print ผลเฉยๆ กลไก gate จะไม่ทำงาน
if not all_passed:
    raise AssertionError("Data quality check failed — ดูรายละเอียดที่ log ด้านบน")
