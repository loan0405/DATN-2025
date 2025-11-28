import pandas as pd
import json
import re

# =============================
# 1. Đọc file JSON
# =============================
df = pd.read_json("it_job.json")
df = df.where(pd.notnull(df), None)  # Thay NaN bằng None

# =============================
# 2. Chuẩn hóa các cột
# =============================

# --- Tên công việc ---
df["Tên công việc"] = df["Tên công việc"].astype(str).str.strip()

# --- Mức lương → "X VND, Y VND" ---
def normalize_salary(val):
    if val is None:
        return None
    if isinstance(val, list):
        parts = val
    else:
        parts = re.split(r"[,|-]", str(val))
    clean = []
    for p in parts:
        p = p.strip()
        if p.isdigit():
            num = int(p)
            if 10 <= num < 100:
                num *= 1_000_000
            clean.append(f"{num} VND")
        else:
            clean.append(p)
    return ", ".join(clean) if clean else None

df["Mức lương"] = df["Mức lương"].apply(normalize_salary)

# --- Trình độ học vấn → CHUỖI ---
def normalize_education(edu):
    if edu is None:
        return None
    e = str(edu).lower()
    if "tiến sĩ" in e or "ph.d" in e:
        return "Tiến Sĩ"
    if "thạc sĩ" in e or "master" in e:
        return "Thạc Sĩ"
    if "đại học" in e or "cử nhân" in e:
        return "Đại Học"
    if "cao đẳng" in e:
        return "Cao Đẳng"
    if "trung học" in e or "high school" in e:
        return "Trung Học"
    return None

df["Trình độ học vấn"] = df["Trình độ học vấn"].apply(normalize_education)


df["Trình độ học vấn"] = df["Trình độ học vấn"].apply(normalize_education)

# --- Chuyên môn → LIST ---
def normalize_skill(val):
    if isinstance(val, list):
        return [v.strip() for v in val if v and v.strip() != ""]
    if isinstance(val, str):
        if "," in val:
            return [v.strip() for v in val.split(",") if v.strip() != ""]
        if val.strip() != "":
            return [val.strip()]
        return None
    return None

df["Chuyên môn"] = df["Chuyên môn"].apply(normalize_skill)

# --- Làm sạch các cột còn lại ---
for colname in ["Địa điểm làm việc", "Kinh nghiệm", "Ngày đăng tuyển"]:
    if colname in df.columns:
        df[colname] = df[colname].astype(str).str.strip()

# =============================
# 3. Xuất JSON sạch
# =============================
records = df.to_dict(orient="records")

# Xử lý loại bỏ escape ký tự \/ nếu có
clean_json = json.dumps(records, ensure_ascii=False, indent=2).replace('\\/', '/')

# In ra
print(clean_json)

# Lưu file
with open("job_cleaned.json", "w", encoding="utf-8") as f:
    f.write(clean_json)
