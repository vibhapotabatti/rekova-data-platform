"""
Rekova Consumer Care — synthetic source generator for the data platform.

Standalone, dependency-free (standard library only) and seeded, so CI can rebuild
the exact same landing zone on every run. Produces 24 months (Oct-2024 → Sep-2026)
of FMCG sell-out, sell-in, retail-audit and target data with six deliberate feed
defects for the quality gate to detect and the dbt staging layer to fix.

Run:  python scripts/generate_data.py
Override the output location with REKOVA_RAW_DIR.
"""
import csv
import os
import random
from datetime import date

random.seed(42)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("REKOVA_RAW_DIR", os.path.join(ROOT, "data", "raw"))
os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ calendar
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS = []
_y, _m = 2024, 10
for _ in range(24):
    MONTHS.append(date(_y, _m, 1))
    _m += 1
    if _m > 12:
        _y, _m = _y + 1, 1

def idx_of_month(y, m):
    for i, d in enumerate(MONTHS):
        if d.year == y and d.month == m:
            return i
    raise KeyError(f"{y}-{m:02d}")

# ------------------------------------------------------------------ products
PRODUCTS = [
    {"sku": "P01", "name": "Shieldon Antiseptic Liquid 550 ml", "brand": "Shieldon",
     "cat": "Antiseptics", "pack": "550 ml", "mrp": 265.0,
     "base": {"GT": 4500, "MT": 6500, "EC": 14000, "PH": 2200}},
    {"sku": "P02", "name": "Shieldon Antiseptic Liquid 110 ml", "brand": "Shieldon",
     "cat": "Antiseptics", "pack": "110 ml", "mrp": 92.0,
     "base": {"GT": 12000, "MT": 20000, "EC": 30000, "PH": 15000}},
    {"sku": "P03", "name": "Shieldon Hand Sanitizer 500 ml", "brand": "Shieldon",
     "cat": "Antiseptics", "pack": "500 ml", "mrp": 180.0,
     "base": {"GT": 2500, "MT": 4000, "EC": 6000, "PH": 1200}},
    {"sku": "P04", "name": "PureGerm Surface Disinfectant Spray 400 ml", "brand": "PureGerm",
     "cat": "Disinfectants", "pack": "400 ml", "mrp": 320.0,
     "base": {"GT": 900, "MT": 2000, "EC": 5000, "PH": 500}},
    {"sku": "P05", "name": "PureGerm Disinfectant Floor Cleaner 975 ml", "brand": "PureGerm",
     "cat": "Disinfectants", "pack": "975 ml", "mrp": 199.0,
     "base": {"GT": 2500, "MT": 3000, "EC": 8000, "PH": 200}},
    {"sku": "P06", "name": "FloKleen Toilet Cleaner Pro 1 L", "brand": "FloKleen",
     "cat": "Toilet Care", "pack": "1 L", "mrp": 185.0,
     "base": {"GT": 2000, "MT": 2500, "EC": 7000, "PH": 0}},
    {"sku": "P07", "name": "FloKleen Toilet Cleaner Blue Blocks 4x40 g", "brand": "FloKleen",
     "cat": "Toilet Care", "pack": "4x40 g", "mrp": 95.0,
     "base": {"GT": 1500, "MT": 2000, "EC": 5000, "PH": 0}},
    {"sku": "P08", "name": "Stainex Stain Remover Powder 500 g", "brand": "Stainex",
     "cat": "Fabric Care", "pack": "500 g", "mrp": 120.0,
     "base": {"GT": 1800, "MT": 1500, "EC": 4000, "PH": 0}},
    {"sku": "P09", "name": "Stainex Fabric Whitener 500 ml", "brand": "Stainex",
     "cat": "Fabric Care", "pack": "500 ml", "mrp": 99.0,
     "base": {"GT": 1200, "MT": 900, "EC": 2500, "PH": 0}},
    {"sku": "P10", "name": "AirPure Air Freshener Spray 250 ml", "brand": "AirPure",
     "cat": "Air Care", "pack": "250 ml", "mrp": 299.0,
     "base": {"GT": 700, "MT": 1200, "EC": 3500, "PH": 0}},
    {"sku": "P11", "name": "ThroatEase Lozenges Honey-Lemon 20s", "brand": "ThroatEase",
     "cat": "Cough & Throat", "pack": "20 loz", "mrp": 65.0,
     "base": {"GT": 3000, "MT": 2000, "EC": 9000, "PH": 5000}},
    {"sku": "P12", "name": "ThroatEase Lozenges Sugar-Free 30s", "brand": "ThroatEase",
     "cat": "Cough & Throat", "pack": "30 loz", "mrp": 95.0,
     "base": {"GT": 1500, "MT": 800, "EC": 4000, "PH": 2000}},
]
SKU = {p["sku"]: p for p in PRODUCTS}
CAT_OF_BRAND = {"Shieldon": "Antiseptics", "PureGerm": "Disinfectants",
                "FloKleen": "Toilet Care", "Stainex": "Fabric Care",
                "AirPure": "Air Care", "ThroatEase": "Cough & Throat"}

# ------------------------------------------------------------------ business rules
REGIONS = ["North", "South", "East", "West"]
REGION_SALES_FACTOR = {"North": 0.90, "South": 1.15, "East": 0.75, "West": 1.00,
                       "National": 1.10}
REGION_TARGET_FACTOR = {"North": 1.05, "South": 1.08, "East": 1.14, "West": 1.10,
                        "National": 1.02}   # East gets the stretch target -> misses
CHANNEL_DISCOUNT = {"General Trade": 0.12, "Modern Trade": 0.10, "Pharmacy": 0.06,
                    "E-commerce": 0.16}
CH_CODE = {"General Trade": "GT", "Modern Trade": "MT", "Pharmacy": "PH",
           "E-commerce": "EC"}
SEASON = {
    "Antiseptics":    {6: 1.22, 7: 1.30, 8: 1.32, 9: 1.28, 10: 1.18, 11: 1.05, 12: 1.10, 1: 1.15, 2: 1.08},
    "Disinfectants":  {6: 1.28, 7: 1.36, 8: 1.36, 9: 1.30, 10: 1.12, 11: 1.04, 12: 1.05},
    "Toilet Care":    {6: 1.18, 7: 1.24, 8: 1.22, 9: 1.14, 10: 1.05},
    "Fabric Care":    {10: 1.22, 11: 1.18, 9: 1.06, 3: 0.98, 4: 0.96},
    "Air Care":       {3: 1.18, 4: 1.22, 5: 1.20, 6: 1.05},
    "Cough & Throat": {1: 1.65, 2: 1.55, 11: 1.50, 12: 1.70, 10: 1.15, 3: 1.25},
}
BRAND_GROWTH = {"Shieldon": 0.12, "PureGerm": 0.14, "FloKleen": 0.09,
                "Stainex": 0.05, "AirPure": 0.10, "ThroatEase": 0.04}
PH_VALID_CATS = {"Antiseptics", "Disinfectants", "Cough & Throat"}

# ------------------------------------------------------------------ distributors
CITY_BANK = {
    "North": [("Gurgaon", 1), ("Lucknow", 2), ("Kanpur", 2), ("Chandigarh", 2), ("Agra", 3), ("Jalandhar", 3)],
    "South": [("Chennai", 1), ("Bengaluru", 1), ("Coimbatore", 2), ("Kochi", 2), ("Vijayawada", 3), ("Madurai", 3)],
    "East":  [("Kolkata", 1), ("Patna", 2), ("Bhubaneswar", 2), ("Siliguri", 3), ("Guwahati", 3), ("Ranchi", 3)],
    "West":  [("Mumbai", 1), ("Pune", 1), ("Ahmedabad", 1), ("Indore", 2), ("Nagpur", 2), ("Surat", 3)],
}
GT_SUFFIX = ["Agencies", "Traders", "Enterprises", "Distributors", "Sales Org", "Marketing Co"]
MT_SUFFIX = ["Mart", "Retail", "Super Store", "Bazaar"]
PH_SUFFIX = ["Chemists", "Medicos", "Pharmacy"]

def build_distributors():
    rows, ptr = [], {r: 0 for r in REGIONS}
    gt_plan = ["North", "South", "East", "West", "North", "South", "West", "East", "North", "South", "West", "East"]
    for k, reg in enumerate(gt_plan):
        city, tier = CITY_BANK[reg][ptr[reg] % len(CITY_BANK[reg])]; ptr[reg] += 1
        rows.append([f"GT{k+1:02d}", f"{city} {GT_SUFFIX[k % len(GT_SUFFIX)]}",
                     "General Trade", reg, tier])
    mt_plan = ["North", "South", "East", "West", "North", "South"]
    for k, reg in enumerate(mt_plan):
        city, tier = CITY_BANK[reg][ptr[reg] % len(CITY_BANK[reg])]; ptr[reg] += 1
        rows.append([f"MT{k+1:02d}", f"{city} {MT_SUFFIX[k % len(MT_SUFFIX)]}",
                     "Modern Trade", reg, tier])
    ph_plan = ["North", "South", "East", "West", "North", "South"]
    for k, reg in enumerate(ph_plan):
        city, tier = CITY_BANK[reg][ptr[reg] % len(CITY_BANK[reg])]; ptr[reg] += 1
        rows.append([f"PH{k+1:02d}", f"{city} {PH_SUFFIX[k % len(PH_SUFFIX)]}",
                     "Pharmacy", reg, tier])
    rows += [
        ["EC01", "Rekova E-comm Ops - Pan-India", "E-commerce", "National", 1],
        ["EC02", "Rekova Quick-Commerce Ops - Pan-India", "E-commerce", "National", 1],
        ["EC03", "Rekova Marketplace Partners - Pan-India", "E-commerce", "National", 1],
    ]
    return rows

DIMS_DIST = build_distributors()          # written to CSV (may carry defects)
DIST = [row[:] for row in DIMS_DIST]      # clean copy used by the generator

# --- defect 4: trailing-space region names on 3 distributors
WS_IDS = {"GT03", "GT07", "MT05"}
for row in DIMS_DIST:
    if row[0] in WS_IDS:
        row[3] = row[3] + " "

SIZE = {}
for row in DIST:
    SIZE[row[0]] = random.uniform(0.75, 1.35)
SIZE["GT01"] = 1.60
SIZE["EC01"] = 1.80

CH_OF  = {row[0]: row[2] for row in DIST}
REG_OF = {row[0]: row[3] for row in DIST}

dist_mult = {}
for p in PRODUCTS:
    for row in DIST:
        dist_mult[(p["sku"], row[0])] = random.uniform(0.75, 1.30)

# ------------------------------------------------------------------ promo calendar
promo_pct = {}
BRANDS = list(BRAND_GROWTH.keys())
for b in BRANDS:
    for ch in ("General Trade", "Modern Trade", "E-commerce"):
        for mi in random.sample(range(24), random.choice([2, 2, 3])):
            promo_pct[(mi, b, ch)] = round(random.uniform(5.0, 10.0), 1)
        if ch in ("Modern Trade", "E-commerce"):
            for y in (2024, 2025):
                for mmn in (10, 11):
                    if random.random() < 0.8:
                        promo_pct[(idx_of_month(y, mmn), b, ch)] = round(random.uniform(10.0, 15.0), 1)

# ------------------------------------------------------------------ sell-out (clean master)
master = []          # clean rows (source of truth for shipments/audit/targets)
by_month = [[] for _ in MONTHS]
demand = {}          # (month_idx, sku, dist) -> units
for mi, ms in enumerate(MONTHS):
    m = ms.month
    for p in PRODUCTS:
        for row in DIST:
            did, ch, reg = row[0], row[2], row[3]
            buy = p["base"].get(CH_CODE[ch], 0)
            if not buy:
                continue
            if ch == "Pharmacy" and p["cat"] not in PH_VALID_CATS:
                continue
            v = (buy * SIZE[did] * dist_mult[(p["sku"], did)]
                 * REGION_SALES_FACTOR[reg]
                 * SEASON.get(p["cat"], {}).get(m, 1.0)
                 * (1 + BRAND_GROWTH[p["brand"]] * (mi / 12.0)))
            pp = promo_pct.get((mi, p["brand"], ch), 0.0)
            if pp:
                v *= (1 + 0.030 * pp)
            units = max(1, int(round(v * random.gauss(1.0, 0.12))))
            gross = round(units * p["mrp"], 2)
            net = round(gross * (1 - CHANNEL_DISCOUNT[ch] - (pp / 100.0 if pp else 0)), 2)
            rec = [ms.isoformat(), p["sku"], did, units, gross, net, 1 if pp else 0, pp]
            master.append(rec)
            by_month[mi].append(rec)
            demand[(mi, p["sku"], did)] = units

# ------------------------------------------------------------------ inject raw-feed defects
dq = {"duplicate_rows": 0, "null_net_sales": 0, "returns_rows": 0,
      "orphan_sku_rows": 0, "missing_month_extract": 0}
GAP = ("GT05", 14)   # one distributor-month extract missing
sellout_out = []
for mi, ms in enumerate(MONTHS):
    for r in by_month[mi]:
        if (r[2], mi) == GAP:
            dq["missing_month_extract"] += 1
            continue
        nr = r[:]
        if random.random() < 0.006:                 # defect 2: missing net_sales
            nr[5] = None
            dq["null_net_sales"] += 1
        if dq["orphan_sku_rows"] < 2 and random.random() < 0.003:   # defect 5: orphan SKU
            nr[1] = "P99"
            dq["orphan_sku_rows"] += 1
        sellout_out.append(nr)
        if random.random() < 0.004:                 # defect 1: duplicate row
            sellout_out.append(r[:])
            dq["duplicate_rows"] += 1
        if dq["returns_rows"] < 30 and random.random() < 0.004:    # defect 3: returns
            k = int(random.uniform(60, 400))
            gross = round(-k * SKU[r[1]]["mrp"], 2)
            sellout_out.append([r[0], r[1], r[2], -k, gross, round(gross * 0.88, 2), 0, 0.0])
            dq["returns_rows"] += 1

# ------------------------------------------------------------------ shipments (sell-in)
ship_out = []
for mi in range(24):
    ms = MONTHS[mi].isoformat()
    nxt = mi + 1
    for p in PRODUCTS:
        for row in DIST:
            did, ch = row[0], row[2]
            if not p["base"].get(CH_CODE[ch], 0):
                continue
            if ch == "Pharmacy" and p["cat"] not in PH_VALID_CATS:
                continue
            base = demand.get((nxt, p["sku"], did)) if nxt < 24 else None
            if base is None:
                base = demand.get((mi, p["sku"], did))
            if base is None:
                continue
            f = random.uniform(0.92, 1.22)
            if random.random() < 0.05:              # occasional bulk batch
                f *= random.uniform(1.6, 2.2)
            ship_out.append([ms, p["sku"], did, int(round(base * f))])

# ------------------------------------------------------------------ retail audit
# Category value is derived FROM our own sells and the assumed share -> internally consistent.
OUR_SHARE = {"Antiseptics": 0.68, "Disinfectants": 0.42, "Toilet Care": 0.55,
             "Fabric Care": 0.08, "Air Care": 0.18, "Cough & Throat": 0.05}
COMP = {"Antiseptics": (0.16, 0.11), "Disinfectants": (0.28, 0.24),
        "Toilet Care": (0.24, 0.18), "Fabric Care": (0.34, 0.10),
        "Air Care": (0.42, 0.30), "Cough & Throat": (0.55, 0.28)}
our_net = {}
for mi, rows_m in enumerate(by_month):
    for r in rows_m:
        brand = SKU[r[1]]["brand"]
        our_net[(mi, brand)] = our_net.get((mi, brand), 0.0) + r[5]

audit_out = []
for mi, ms in enumerate(MONTHS):
    for cat, share0 in OUR_SHARE.items():
        brand = next(b for b, c in CAT_OF_BRAND.items() if c == cat)
        my_share = share0 * random.uniform(0.97, 1.03)
        my_net_mn = our_net.get((mi, brand), 0.0) / 1e6      # Rs million
        cat_v_mn = my_net_mn / my_share
        audit_out.append([ms.isoformat(), cat, brand, "Rekova",
                          round(my_share * 100, 2), round(cat_v_mn, 1)])
        g_share = COMP[cat][0] * random.uniform(0.95, 1.05)
        k_share = COMP[cat][1] * random.uniform(0.95, 1.05)
        audit_out.append([ms.isoformat(), cat, "GermX", "Competitor A",
                          round(g_share * 100, 2), round(cat_v_mn, 1)])
        audit_out.append([ms.isoformat(), cat, "Kleenova", "Competitor B",
                          round(k_share * 100, 2), round(cat_v_mn, 1)])
        rest = max(0.02, 1 - my_share - g_share - k_share)
        audit_out.append([ms.isoformat(), cat, "Rest of market", "Long tail",
                          round(rest * 100, 2), round(cat_v_mn, 1)])

# ------------------------------------------------------------------ targets
agg = {}
for mi, rows_m in enumerate(by_month):
    for r in rows_m:
        reg, ch = REG_OF[r[2]], CH_OF[r[2]]
        agg[(mi, reg, ch)] = agg.get((mi, reg, ch), 0.0) + r[5]
target_out = []
for (reg, ch) in sorted({(REG_OF[r[2]], CH_OF[r[2]]) for r in master}):
    for mi in range(24):
        actual = agg.get((mi, reg, ch))
        if actual is None:
            continue
        if mi >= 12:
            prev = agg.get((mi - 12, reg, ch))
            if prev is None:
                continue
            t = prev * REGION_TARGET_FACTOR[reg] * random.uniform(0.95, 1.06)
        else:
            t = actual * random.uniform(0.92, 1.10)
        target_out.append([MONTHS[mi].isoformat(), reg, ch, round(t, 0)])

# ------------------------------------------------------------------ dim_date
date_out = [[d.isoformat(), d.year, d.month, MONTH_NAMES[d.month - 1],
             f"Q{(d.month - 1) // 3 + 1}"] for d in MONTHS]

# ------------------------------------------------------------------ write CSVs
def write_csv(name, header, rows):
    path = os.path.join(OUT, name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {name:34s}{len(rows):8,d} rows")

print("Generating Rekova data into", os.path.normpath(OUT))
write_csv("dim_product.csv", ["sku_id", "sku_name", "brand", "category", "pack_size", "mrp"],
          [[p["sku"], p["name"], p["brand"], p["cat"], p["pack"], p["mrp"]] for p in PRODUCTS])
write_csv("dim_distributor.csv", ["distributor_id", "distributor_name", "channel_type", "region", "city_tier"],
          DIMS_DIST)
write_csv("dim_date.csv", ["month_start", "year", "month_num", "month_name", "quarter"], date_out)
write_csv("fact_sellout_monthly.csv",
          ["month_start", "sku_id", "distributor_id", "units", "gross_sales", "net_sales",
           "promo_flag", "promo_discount_pct"], sellout_out)
write_csv("fact_shipments_monthly.csv",
          ["month_start", "sku_id", "distributor_id", "units_shipped"], ship_out)
write_csv("fact_retail_audit.csv",
          ["month_start", "category", "brand", "manufacturer", "value_share_pct",
           "category_value_mn_inr"], audit_out)
write_csv("fact_targets.csv",
          ["month_start", "region", "channel_type", "target_net_sales"], target_out)

total_net_cr = sum(r[5] for r in master) / 1e7
print(f"\nClean portfolio: Rs {total_net_cr:,.0f} Cr over 24 months "
      f"(~Rs {total_net_cr/24:,.1f} Cr/month)")
print("Injected data-quality defects:")
for k, v in dq.items():
    print(f"  {k:28s}{v:5,d}")
print("Done.")
