from django.db import migrations

FORWARD_SQL = """
PRAGMA foreign_keys=OFF;

-- storeseatsetting: 再構築（レガシー seat_type 列を捨てる）
CREATE TABLE IF NOT EXISTS "new_billing_storeseatsetting" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "service_rate" decimal NULL,
    "charge_per_person" integer,
    "extension_30_price" integer,
    "free_time_price" integer,
    "private_price" integer,
    "memo" varchar(100) NOT NULL DEFAULT '',
    "store_id" bigint NOT NULL REFERENCES billing_store(id) DEFERRABLE INITIALLY DEFERRED,
    "seat_type_id" bigint NULL REFERENCES billing_seattype(id) DEFERRABLE INITIALLY DEFERRED
);
INSERT INTO "new_billing_storeseatsetting"
    ("id","service_rate","charge_per_person","extension_30_price","free_time_price","private_price","memo","store_id","seat_type_id")
SELECT
    "id","service_rate","charge_per_person","extension_30_price","free_time_price","private_price",COALESCE("memo",""),"store_id","seat_type_id"
FROM "billing_storeseatsetting";
DROP TABLE "billing_storeseatsetting";
ALTER TABLE "new_billing_storeseatsetting" RENAME TO "billing_storeseatsetting";
-- unique_together (store, seat_type)
CREATE UNIQUE INDEX IF NOT EXISTS "billing_storeseatsetting_store_id_seat_type_id_uniq"
ON "billing_storeseatsetting" ("store_id","seat_type_id");

-- table: 再構築（レガシー seat_type 列を捨てる）
CREATE TABLE IF NOT EXISTS "new_billing_table" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "store_id" bigint NOT NULL REFERENCES billing_store(id) DEFERRABLE INITIALLY DEFERRED,
    "code" varchar(16),
    "seat_type_id" bigint NULL REFERENCES billing_seattype(id) DEFERRABLE INITIALLY DEFERRED
);
INSERT INTO "new_billing_table"
    ("id","store_id","code","seat_type_id")
SELECT "id","store_id","code","seat_type_id"
FROM "billing_table";
DROP TABLE "billing_table";
ALTER TABLE "new_billing_table" RENAME TO "billing_table";
-- unique_together (store, code)
CREATE UNIQUE INDEX IF NOT EXISTS "billing_table_store_id_code_uniq"
ON "billing_table" ("store_id","code");

PRAGMA foreign_keys=ON;
"""

class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0079_seattype_fix_db_columns'),  # 直前の番号に合わせて
    ]
    operations = [
        migrations.RunSQL(FORWARD_SQL, reverse_sql=migrations.RunSQL.noop),
    ]