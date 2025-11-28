import json
import time
import re
from datetime import datetime, timedelta
from openpyxl import Workbook
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ------------------ CÀI DRIVER ------------------
def init_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(service=Service(), options=options)
    return driver

# ------------------ LẤY LINK JOB TRONG 1 TRANG ------------------
def get_job_links_from_page(driver, page):
    base_url = "https://www.topcv.vn/tim-viec-lam-cong-nghe-thong-tin-cr257?type_keyword=1&sba=1&category_family=r257&page={}"
    url = base_url.format(page)
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "h3.title a")))
        elems = driver.find_elements(By.CSS_SELECTOR, "h3.title a")
        links = [e.get_attribute("href") for e in elems if e.get_attribute("href")]
        print(f"Trang {page}: tìm được {len(links)} job")
        return links
    except Exception as e:
        print(f"Lỗi load trang {page}: {e}, retry sau 5s...")
        time.sleep(5)
        return get_job_links_from_page(driver, page)

# ------------------ CHUYỂN MỨC LƯƠNG SANG VND ------------------
def normalize_salary(salary_str):
    if not salary_str:
        return 0
    salary_str = salary_str.lower().replace(" ", "")
    if "thoảthuận" in salary_str or "thoathuan" in salary_str:
        return 0
    nums = re.findall(r"[\d,.]+", salary_str)
    if not nums:
        return 0
    factor = 26354.98 if "usd" in salary_str else 1
    nums_vnd = [int(float(n.replace(",", "")) * factor) for n in nums]
    if len(nums_vnd) == 1:
        return nums_vnd[0]
    return sum(nums_vnd) // len(nums_vnd)

# ------------------ CHUẨN HÓA ĐỊA ĐIỂM (LẤY TẤT CẢ) ------------------
def normalize_location(loc):
    if not loc:
        return ""
    loc = loc.strip()
    loc = " ".join([w.capitalize() for w in loc.split()])
    return loc

# ------------------ PARSE NGÀY ĐĂNG TUYỂN ------------------
def parse_date_posted(text):
    text = text.strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%d/%m/%Y")
    except:
        pass
    match = re.search(r"(\d+)", text)
    if match:
        days_left = int(match.group(1))
        return datetime.today() - timedelta(days=days_left)
    return None

# ------------------ CRAWL CHI TIẾT JOB ------------------
def crawl_job(driver, link, start_date=None, end_date=None):
    try:
        driver.get(link)
        time.sleep(3)
        data = {}

        # Tên công việc
        try:
            data["Tên công việc"] = driver.find_element(By.CSS_SELECTOR, "h1.job-detail__info--title").text.strip()
        except:
            data["Tên công việc"] = ""

        # Sections: Mức lương, Địa điểm, Kinh nghiệm
        data["Mức lương"] = data["Địa điểm làm việc"] = data["Kinh nghiệm"] = ""
        try:
            sections = driver.find_elements(By.CSS_SELECTOR, "div.job-detail__info--section")
            for s in sections:
                title = s.find_element(By.CSS_SELECTOR, "div.job-detail__info--section-content-title").text.strip()
                val = s.find_element(By.CSS_SELECTOR, "div.job-detail__info--section-content-value").text.strip()
                if "Mức lương" in title: data["Mức lương"] = normalize_salary(val)
                elif "Địa điểm" in title: data["Địa điểm làm việc"] = normalize_location(val)
                elif "Kinh nghiệm" in title: data["Kinh nghiệm"] = val
        except: pass

        # Ngày đăng tuyển
        date_text = ""
        try:
            date_text = driver.find_element(By.CSS_SELECTOR, "span.job-posted-date").text.strip()
        except:
            try:
                days_left_elem = driver.find_element(By.CSS_SELECTOR, "span.deadline strong")
                days_left = int(days_left_elem.text.strip())
                date_text = f"Còn {days_left} ngày"
            except:
                pass
        parsed_date = parse_date_posted(date_text)
        if parsed_date:
            if start_date and parsed_date < start_date:
                return None
            if end_date and parsed_date > end_date:
                return None
            data["Ngày đăng tuyển"] = parsed_date.strftime("%d/%m/%Y")
        else:
            data["Ngày đăng tuyển"] = ""

        # Trình độ học vấn
        try:
            edu_tags = driver.find_elements(By.CSS_SELECTOR, "div.job-tags__group-list-tag-scroll a.item.search-from-tag")
            data["Trình độ học vấn"] = [t.text.strip() for t in edu_tags if "Đại Học" in t.text or "Cao Đẳng" in t.text]
        except:
            data["Trình độ học vấn"] = []

        # Chuyên môn
        try:
            spec_tags = driver.find_elements(By.CSS_SELECTOR, "div.job-tags__group-list-tag-scroll a.item.search-from-tag.link")
            data["Chuyên môn"] = [t.text.strip() for t in spec_tags if t.text.strip() not in ["Nghỉ thứ 7", "Topik", "Tiếng Anh"]]
        except:
            data["Chuyên môn"] = []

        return data
    except Exception as e:
        print(f"Lỗi crawl job {link}: {e}, retry sau 5s...")
        time.sleep(5)
        return crawl_job(driver, link, start_date, end_date)

# ------------------ XUẤT EXCEL ------------------
def export_to_excel(list_data, filename):
    wb = Workbook()
    ws = wb.active
    ws.title = "Jobs"
    
    if not list_data:
        print("Không có dữ liệu để xuất Excel")
        return

    headers = list(list_data[0].keys())
    ws.append(headers)

    for d in list_data:
        row = []
        for h in headers:
            val = d.get(h, "")
            if isinstance(val, list):
                val = ", ".join(val)
            row.append(val)
        ws.append(row)

    wb.save(filename)
    print("Excel lưu tại:", filename)

# ------------------ MAIN ------------------
if __name__ == "__main__":
    import time
    import json
    from datetime import datetime

    total_pages = 45
    batch_size = 5
    START_PAGE = 31     # ❗ Chỉ chạy từ trang 31

    all_data = []

    # Khoảng thời gian lọc job
    start_date = datetime.strptime("01/06/2025", "%d/%m/%Y")
    end_date = datetime.strptime("01/11/2025", "%d/%m/%Y")

    # Vòng lặp batch – CHỈ bắt đầu từ trang 31
    for batch_start in range(START_PAGE, total_pages + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, total_pages)

        print(f"\n===== BATCH {batch_start} → {batch_end} =====")

        driver = init_driver(headless=False)
        batch_links = []

        # Lấy link job theo từng trang trong batch
        for page in range(batch_start, batch_end + 1):

            # ❗ BỎ QUA các trang < 31 (phòng trường hợp chạy lại)
            if page < START_PAGE:
                continue

            print(f"Lấy link trang {page}...")
            links = get_job_links_from_page(driver, page)
            batch_links.extend(links)
            time.sleep(2)

        # Crawl từng job trong batch
        batch_data = []
        for i, link in enumerate(batch_links):
            print(f"Crawl job {i+1}/{len(batch_links)}: {link}")

            job = crawl_job(
                driver, 
                link, 
                start_date=start_date,
                end_date=end_date
            )

            if job:
                batch_data.append(job)
                print(f"--> Lấy xong: {job.get('Tên công việc')}")

            time.sleep(1)

        driver.quit()

        all_data.extend(batch_data)

        # Lưu Excel
        export_to_excel(all_data, "demo.xlsx")

        # Lưu JSON
        with open("demo.json", "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)

        print(f"Batch {batch_start}-{batch_end} hoàn tất – Lưu dữ liệu thành công.")

    print("\n🎉 Hoàn tất crawl toàn bộ trang từ 31 → 45.")
