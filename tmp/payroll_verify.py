from billing.models import Bill
from billing.payroll.snapshot import build_payroll_snapshot

BILL_ID = 136

bill = Bill.objects.select_related("table__store").get(id=BILL_ID)
snap = build_payroll_snapshot(bill)

totals = snap["totals"]
by_cast = snap["by_cast"]
items = snap["items"]

def sum_item_effects():
    s = 0
    for it in items:
        for ef in it.get("payroll_effects", []):
            s += int(ef.get("amount", 0) or 0)
    return s

def sum_by_cast_amount():
    return sum(int(c.get("amount", 0) or 0) for c in by_cast)

def sum_breakdown(t):
    s = 0
    for c in by_cast:
        for b in c.get("breakdown", []):
            if b.get("type") == t:
                s += int(b.get("amount", 0) or 0)
    return s

print("[INFO] bill:", bill.id)
print("[INFO] store:", getattr(getattr(bill, "table", None), "store", None))

print("\n=== totals ===")
print(totals)

print("\n=== checks ===")
print("A: sum(items.payroll_effects) == totals.item_total :", sum_item_effects(), "==", totals["item_total"])
print("B: sum(by_cast.amount) == totals.labor_total       :", sum_by_cast_amount(), "==", totals["labor_total"])
print("C: sum(by_cast.breakdown.item_back) == item_total  :", sum_breakdown("item_back"), "==", totals["item_total"])
print("D: sum(by_cast.breakdown.nomination_pool) == nom_total :", sum_breakdown("nomination_pool"), "==", totals["nomination_total"])
print("E: sum(by_cast.breakdown.adjustment) == 0          :", sum_breakdown("adjustment"), "== 0")

ng = []
if sum_item_effects() != totals["item_total"]: ng.append("A")
if sum_by_cast_amount() != totals["labor_total"]: ng.append("B")
if sum_breakdown("item_back") != totals["item_total"]: ng.append("C")
if sum_breakdown("nomination_pool") != totals["nomination_total"]: ng.append("D")
if sum_breakdown("adjustment") != 0: ng.append("E")

print("\n[RESULT]", "OK" if not ng else f"NG: {ng}")

print("\n=== by_cast ===")
for c in by_cast:
    print({"cast_id": c.get("cast_id"), "stay_type": c.get("stay_type"), "amount": c.get("amount")})