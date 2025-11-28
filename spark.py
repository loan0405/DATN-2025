import pandas as pd
import json
import re
from datetime import datetime

# =============================
# 1. Đọc file JSON
# =============================
df = pd.read_json("job_cleaned.json")
df = df.where(pd.notnull(df), None)  # Thay NaN bằng None

# =============================
# 2. Loại bỏ dữ liệu trống, trùng lặp
# =============================
df = df[df["Tên công việc"].notna() & (df["Tên công việc"] != "")]
df = df.drop_duplicates(subset=["Tên công việc"])

# =============================
# 3. Chuẩn hóa mức lương
# =============================
def normalize_salary(val):
    if val is None:
        return None
    
    if isinstance(val, list):
        parts = val
    else:
        parts = re.split(r"[,|-]", str(val))

    numbers = []

    for p in parts:
        p = str(p).strip().lower()
        if p == "" or "thỏa thuận" in p:
            numbers.append(0)
            continue

        # Chuyển $ hoặc USD sang VND
        if "$" in p or "usd" in p:
            try:
                num = float(re.sub(r"[^\d.]", "", p)) * 25_000
            except:
                continue
            numbers.append(num)
            continue

        # Chuyển triệu sang VND
        if "triệu" in p:
            try:
                num = float(re.sub(r"[^\d.]", "", p)) * 1_000_000
            except:
                continue
            numbers.append(num)
            continue

        # Nếu là số và có 1 hoặc 2 chữ số -> nhân 1_000_000
        if p.isdigit():
            num = int(p)
            if 1 <= num <= 99:
                num *= 1_000_000
            numbers.append(num)
            continue

        # Nếu còn chữ số nào khác
        digits = re.findall(r"\d+", p)
        for d in digits:
            num = int(d)
            if 1 <= num <= 99:
                num *= 1_000_000
            numbers.append(num)

    if not numbers:
        return None

    avg_salary = sum(numbers) / len(numbers)
    return f"{int(avg_salary)} VND"

df["Mức lương"] = df["Mức lương"].apply(normalize_salary)

# =============================
# 4. Chuẩn hóa ngày đăng tuyển
# =============================
def normalize_date(date_str):
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except:
            continue
    return None

df["Ngày đăng tuyển"] = df["Ngày đăng tuyển"].apply(normalize_date)

# =============================
# 5. Chuẩn hóa trình độ học vấn
# =============================
def normalize_education(edu):
    if edu is None:
        return None
    e = str(edu).lower()
    if "đại học" in e:
        return "Đại học"
    if "cao đẳng" in e:
        return "Cao đẳng"
    return None

df["Trình độ học vấn"] = df["Trình độ học vấn"].apply(normalize_education)

def clean_skills(skills):
    if skills is None:
        return "", ""
    
    if isinstance(skills, list):
        skills_list = skills
    else:
        skills_list = [skills]

    cleaned = []
    languages = []

    foreign_languages = ["tiếng anh", "tiếng nhật", "tiếng hàn", "tiếng trung"]

    for s in skills_list:
        if not s:
            continue
        s_lower = str(s).strip().lower()
        
        # Kiểm tra ngoại ngữ trước
        if any(lang in s_lower for lang in foreign_languages):
            languages.append(str(s).strip())
            continue
        
        # Loại bỏ các cụm không cần thiết
        unwanted = [
            "có hỗ trợ data", "tiếng anh đọc hiểu", "tiếng anh giao tiếp", "nghỉ thứ 7",
            "trôi chảy", "giao tiếp cơ bản", "chuẩn", "toeic 550", "giao tiếp thành thạo", 
            "jlpt n1", "jlpt n2", "jlpt n3", "jlpt n4", "jlpt n5", 
            "topik 1", "topik 2", "topik 3", "topik 4", "topik 5"
        ]
        if any(x in s_lower for x in unwanted):
            continue
        
        cleaned.append(str(s).strip())

    cleaned_str = ", ".join(cleaned) if cleaned else ""
    languages_str = ", ".join(languages) if languages else ""
    return cleaned_str, languages_str

# =============================
# 7. Loại bỏ các dấu [] trong tất cả các cột list
# =============================
for col in ["Chuyên môn", "Ngoại ngữ"]:
    df[col] = df[col].astype(str)

# =============================
# 8. Xuất JSON và Excel
# =============================
# Xuất JSON
records = df.to_dict(orient="records")
with open("job_final.json", "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

# Xuất Excel
df.to_excel("job_final.xlsx", index=False)
print("Xuất JSON và Excel thành công!")
