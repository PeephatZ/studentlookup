import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from io import StringIO
import os

# URL ของ Google Sheet ที่ใช้เก็บ account
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ucIs5buCGLhlnv0Q-pEQ7yN1FJImvEpVZeiOv41xw3I/edit?usp=sharing"

def connect_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    service_account_info = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
    client = gspread.authorize(creds)
    return client.open_by_url(SHEET_URL).sheet1

def load_student_data():
    try:
        with open("data/allstudent.csv", encoding="utf-8") as f:
            lines = f.readlines()

        data_lines = [line for line in lines if line.strip().split(',')[0].isdigit()]
        csv_content = "เลขที่,student_id,prefix,first_name,last_name\n" + "".join(data_lines)
        df = pd.read_csv(StringIO(csv_content), dtype=str)

        df['full_name'] = df['prefix'] + df['first_name'] + ' ' + df['last_name']

        try:
            worksheet = connect_sheet()
            records = worksheet.get_all_records()
            df_account = pd.DataFrame(records)
            df_account['student_id'] = df_account['student_id'].astype(str)
            df['student_id'] = df['student_id'].astype(str)
            df = pd.merge(df, df_account, on='student_id', how='left')
        except Exception as e:
            st.warning(f"เชื่อมต่อ Google Sheet ไม่สำเร็จ: {e}")
            df['account_name'] = ''

        return df
    except Exception as e:
        st.error(f"ไม่สามารถอ่าน data/allstudent.csv ได้: {e}")
        return pd.DataFrame()

def save_student_account(student_id, account_name):
    worksheet = connect_sheet()
    records = worksheet.get_all_records()
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
            st.success(f"พบ: {student['full_name'].iloc[0]}")
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
