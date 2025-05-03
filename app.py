import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import glob
import csv
import re

SHEET_URL = "https://docs.google.com/spreadsheets/d/1ucIs5buCGLhlnv0Q-pEQ7yN1FJImvEpVZeiOv41xw3I/edit?usp=sharing"

def connect_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    service_account_info = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
    client = gspread.authorize(creds)
    return client.open_by_url(SHEET_URL).sheet1

def extract_classroom_from_lines(lines):
    for line in lines:
        match = re.search(r"ชั้นมัธยมศึกษาปีที่\s*(\d+)\s*ห้องเรียนที่\s*(\d+)", line)
        if match:
            level = match.group(1)
            room = match.group(2)
            return f"{level}/{room}"
    return "ไม่ระบุ"

def load_student_data():
    try:
        all_rows = []

        for file_path in glob.glob("data/*.csv"):
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()
                classroom = extract_classroom_from_lines(lines)
                reader = csv.reader(lines)
                for row in reader:
                    if len(row) >= 5 and row[0].strip().isdigit():
                        all_rows.append({
                            "เลขที่": row[0].strip(),
                            "student_id": row[1].strip(),
                            "prefix": row[2].strip(),
                            "first_name": row[3].strip(),
                            "last_name": row[4].strip(),
                            "classroom": classroom
                        })

        if not all_rows:
            st.error("⚠️ ไม่พบข้อมูลนักเรียนที่มีรูปแบบถูกต้อง")
            return pd.DataFrame()

        df = pd.DataFrame(all_rows)
        df['full_name'] = df['prefix'] + df['first_name'] + ' ' + df['last_name']

        try:
            worksheet = connect_sheet()
            records = worksheet.get_all_records()
            if not records or 'student_id' not in records[0]:
                df['account_name'] = ''
                return df

            df_account = pd.DataFrame(records)
            df_account['student_id'] = df_account['student_id'].astype(str)
            df['student_id'] = df['student_id'].astype(str)
            df = pd.merge(df, df_account, on='student_id', how='left')
        except Exception as e:
            st.warning(f"เชื่อมต่อ Google Sheet ไม่สำเร็จ: {e}")
            df['account_name'] = ''

        return df

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดไฟล์: {e}")
        return pd.DataFrame()

def save_student_account(student_id, account_name):
    worksheet = connect_sheet()
    records = worksheet.get_all_records()

    if not records or 'student_id' not in records[0]:
        df = pd.DataFrame(columns=['student_id', 'account_name'])
    else:
        df = pd.DataFrame(records)

    df = df[df['student_id'].astype(str) != str(student_id)]
    df.loc[len(df)] = [student_id, account_name]

    worksheet.clear()
    worksheet.append_row(['student_id', 'account_name'])
    for row in df.itertuples(index=False):
        worksheet.append_row(list(row))

def main():
    st.set_page_config(page_title="ระบบค้นหานักเรียน", page_icon="📘")
    st.title("📘 ระบบค้นหานักเรียน ปี 2568")

    df = load_student_data()
    if df.empty:
        return

    student_id = st.text_input("🔍 กรอกรหัสประจำตัวนักเรียน")

    if student_id:
        student_id = student_id.strip()
        student = df[df['student_id'] == student_id]

        if not student.empty:
            name = student['full_name'].iloc[0]
            room = student.get("classroom", "ไม่ระบุ").iloc[0]
            number = student.get("เลขที่", "-").iloc[0]
            st.success(f"พบ: {name} ชั้น {room} เลขที่ {number}")

            account = student.get("account_name", "").iloc[0]
            if account and str(account).strip():
                st.info(f"📌 ชื่อแอคเค้า: {account}")
            else:
                if st.checkbox("✅ เพิ่มชื่อแอคเค้า"):
                    acc_input = st.text_input("กรอกชื่อแอคเค้าใหม่")
                    if st.button("💾 บันทึก"):
                        save_student_account(student_id, acc_input)
                        st.success("✅ บันทึกเรียบร้อยแล้ว")
                        st.experimental_rerun()
        else:
            st.error("❌ ไม่พบรหัสนี้ในระบบ")

if __name__ == '__main__':
    main()
