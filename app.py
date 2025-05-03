import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread

# Google Sheet URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1_kFGRDDfELt4zDwgABBRh3X6hh_mHzBxnKErnNqDZEE/edit#gid=0"

def connect_sheet():
    # Connect to Google Sheet
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    try:
        # Always use secrets for service account
        if 'gcp_service_account' not in st.secrets:
            st.error("Missing gcp_service_account in Streamlit secrets")
            st.stop()

        service_account_info = st.secrets['gcp_service_account']
        st.write("Service Account Info Keys:", list(service_account_info.keys()))
        
        # Format and validate private key
        private_key = service_account_info.get('private_key', '')
        
        # Clean up the private key
        private_key = private_key.strip()
        if not private_key.startswith('-----BEGIN PRIVATE KEY-----'):
            private_key = '-----BEGIN PRIVATE KEY-----\n' + private_key
        if not private_key.endswith('-----END PRIVATE KEY-----'):
            private_key = private_key + '\n-----END PRIVATE KEY-----'
        if not private_key.endswith('\n'):
            private_key = private_key + '\n'
            
        # Update the service account info with cleaned private key
        service_account_info['private_key'] = private_key
        
        st.write("Private key starts with:", private_key[:50] if private_key else 'No private key found')
        st.write("Private key ends with:", private_key[-50:] if private_key else 'No private key found')
            
        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=scope
        )
        
        client = gspread.authorize(creds)
        return client.open_by_url(SHEET_URL).sheet1
    except Exception as e:
        st.error(f"Error connecting to Google Sheet: {str(e)}")
        st.error(f"Error type: {type(e).__name__}")
        st.error(f"Full error details: {repr(e)}")
        raise

def get_class_info(filename):
    # Extract class info from filename
    if 'ม.6 ปี 2568 - ม.6.' in filename:
        class_num = 'ม.6'
    else:
        class_num = filename.split(' ')[1].replace('csv', '')
    return class_num

def clean_csv_content(df, filename):
    # Drop empty columns (columns with all NaN values)
    df = df.dropna(axis=1, how='all')
    
    # Get the column names
    columns = df.columns.tolist()
    
    # Find the index of student ID column
    id_col_idx = columns.index('เลขประจำตัว')
    
    # The next three columns should be prefix, first name, and last name
    df.columns = ['เลขที่', 'เลขประจำตัว', 'คำนำหน้า', 'ชื่อ', 'นามสกุล'] + [''] * (len(columns) - 5)
    
    # Keep the columns we need and rename them
    df = df[['เลขที่', 'เลขประจำตัว', 'คำนำหน้า', 'ชื่อ', 'นามสกุล']]
    df.columns = ['number', 'student_id', 'prefix', 'first_name', 'last_name']
    
    # Add class information
    class_num = get_class_info(filename)
    df['class'] = class_num
    
    # Clean up any whitespace
    for col in df.columns:
        df[col] = df[col].str.strip()
    
    return df

def get_room_from_header(csv_file):
    try:
        # Read the file content
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        
        # Split content into sections by student lists
        sections = content.split('โรงเรียนเขมราฐพิทยาคม')
        
        # Store student ID to room mapping
        student_rooms = {}
        current_room = None
        
        for section in sections:
            if not section.strip():
                continue
                
            lines = section.split('\n')
            student_ids = []
            
            # Find room number in this section
            for line in lines:
                if 'ห้องเรียนที่' in line:
                    try:
                        current_room = line.split('ห้องเรียนที่')[1].split()[0].strip()
                    except:
                        continue
                        
                # If this is a student line
                elif line.strip() and ',' in line:
                    parts = line.split(',')
                    if len(parts) >= 2 and parts[1].strip():
                        student_id = parts[1].strip()
                        if student_id.isdigit() and current_room:
                            student_rooms[student_id] = current_room
        
        return student_rooms
    except Exception as e:
        print(f"Error reading room from header: {e}")
        return {}

def load_student_data():
    try:
        # Get all CSV files from data folder
        csv_files = [
            'data/รายชื่อ ม.1 ปี 2568.csv',
            'data/รายชื่อ ม.2 ปี 2568.csv',
            'data/รายชื่อ ม.3 ปี 2568.csv',
            'data/รายชื่อ ม.4 ปี 2568.csv',
            'data/รายชื่อ ม.5 ปี 2568.csv',
            'data/รายชื่อ ม.6 ปี 2568 - ม.6.1.csv',
            'data/รายชื่อ ม.6 ปี 2568 - ม.6.2.csv',
            'data/รายชื่อ ม.6 ปี 2568 - ม.6.3.csv',
            'data/รายชื่อ ม.6 ปี 2568 - ม.6.4.csv',
            'data/รายชื่อ ม.6 ปี 2568 - ม.6.5.csv',
            'data/รายชื่อ ม.6 ปี 2568 - ม.6.6.csv',
            'data/รายชื่อ ม.6 ปี 2568 - ม.6.7.csv',
            'data/รายชื่อ ม.6 ปี 2568 - ม.6.8.csv'
        ]
        
        all_students = []
        
        # Read each CSV file
        for csv_file in csv_files:
            try:
                # Skip header rows and read the data, ignore trailing commas
                df = pd.read_csv(csv_file, dtype=str, skiprows=3, encoding='utf-8-sig', on_bad_lines='skip')
                df = clean_csv_content(df, csv_file)
                
                # Add room number from mapping
                student_rooms = get_room_from_header(csv_file)
                if student_rooms:
                    df['room'] = df['student_id'].apply(lambda x: student_rooms.get(x))
                    
                all_students.append(df)
            except Exception as e:
                st.warning(f"ไม่สามารถอ่านไฟล์ {csv_file}: {e}")
                continue
        
        if not all_students:
            raise Exception("ไม่สามารถอ่านข้อมูลนักเรียนได้")
            
        # Combine all dataframes
        df = pd.concat(all_students, ignore_index=True)
        
        # Create full name
        df['full_name'] = df['prefix'].fillna('') + df['first_name'].fillna('') + ' ' + df['last_name'].fillna('')
        
        # Sort by student_id for consistent ordering
        df = df.sort_values('student_id')
        
        # Get account data from Google Sheet
        try:
            worksheet = connect_sheet()
            records = worksheet.get_all_records()
            df_account = pd.DataFrame(records)
            df_account['student_id'] = df_account['student_id'].astype(str)
            df['student_id'] = df['student_id'].astype(str)
            df = pd.merge(df, df_account, on='student_id', how='left')
        except Exception as e:
            print(f"Error connecting to Google Sheet: {e}")
            df['account_name'] = ''
            
        return df
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
        return pd.DataFrame()

def save_student_account(student_id, account_name):
    if not account_name or not account_name.strip():
        st.error("กรุณากรอกชื่อแอคเค้า")
        return False
        
    try:
        st.info("กำลังเชื่อมต่อกับ Google Sheet...")
        # Connect to Google Sheet
        worksheet = connect_sheet()
        records = worksheet.get_all_records()
        
        # Convert to DataFrame
        df = pd.DataFrame(records)
        st.info("กำลังบันทึกข้อมูล...")
        
        # Check if student_id exists
        if 'student_id' in df.columns:
            df['student_id'] = df['student_id'].astype(str)
            existing_record = df[df['student_id'] == str(student_id)]
            
            if not existing_record.empty:
                # Update existing record
                row_idx = df[df['student_id'] == str(student_id)].index[0] + 2  # Add 2 for header and 1-based index
                worksheet.update_cell(row_idx, 2, account_name)
                st.success(f"อัพเดทข้อมูลสำเร็จ: รหัส {student_id} -> {account_name}")
            else:
                # Add new record
                worksheet.append_row([student_id, account_name])
                st.success(f"เพิ่มข้อมูลใหม่สำเร็จ: รหัส {student_id} -> {account_name}")
        else:
            # First record
            worksheet.append_row(['student_id', 'account_name'])  # Headers
            worksheet.append_row([student_id, account_name])
            st.success(f"สร้างชีทและเพิ่มข้อมูลสำเร็จ: รหัส {student_id} -> {account_name}")
        return True
            
    except Exception as e:
        st.error(f"ไม่สามารถบันทึกข้อมูล: {str(e)}")
        return False

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
            # Display student info
            class_info = f"{student['class'].iloc[0]}/{student['room'].iloc[0]}" if not pd.isna(student['room'].iloc[0]) else student['class'].iloc[0]
            class_info = f"{class_info} เลขที่ {student['number'].iloc[0]}"
            st.success(f"พบ: {student['full_name'].iloc[0]} ({class_info})")
            
            # Display/edit account name
            account = student.get("account_name", "").iloc[0]
            if account and str(account).strip() and str(account).lower() != 'nan':
                st.info(f"📌 ชื่อแอคเค้า: {account}")
            
            if st.checkbox("✅ เพิ่มชื่อแอคเค้า"):
                acc_input = st.text_input("กรอกชื่อแอคเค้าใหม่")
                if st.button("💾 บันทึก"):
                    if save_student_account(student_id, acc_input):
                        st.rerun()
        else:
            st.error("❌ ไม่พบรหัสนี้ในระบบ")

if __name__ == "__main__":
    main()
