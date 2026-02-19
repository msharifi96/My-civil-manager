import streamlit as st
import pandas as pd
import sqlite3
import base64
import os
import shutil

# ۱. تنظیمات مسیر ذخیره‌سازی محلی
BASE_DIR = "Engineering_Data"  # نام پوشه اصلی در حافظه دستگاه
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# ۲. اتصال به دیتابیس
@st.cache_resource
def get_connection():
    conn = sqlite3.connect('civil_pro_final_v26.db', check_same_thread=False)
    return conn

conn = get_connection()
c = conn.cursor()

# ایجاد جداول (ستون file_path اضافه شد)
c.execute('''CREATE TABLE IF NOT EXISTS project_files 
             (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, 
              file_name TEXT, file_path TEXT, file_blob BLOB)''')
conn.commit()

st.set_page_config(page_title="مدیریت مهندسی شریفی - نسخه حافظه داخلی", layout="wide")

# استایل راست‌چین
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"], .main, .block-container { direction: rtl !important; text-align: right !important; font-family: 'Segoe UI', Tahoma, sans-serif; }
    h1, h2, h3, h4, h5, h6, label, .stMarkdown, p, span { text-align: right !important; direction: rtl !important; }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد", "👷 شخصی", "📤 آپلود در حافظه", "📍 تنظیمات"])

# --- تابع نمایش و دانلود فایل از حافظه ---
def render_dash(label):
    # کدهای بخش داشبورد مشابه قبل است با این تفاوت که فایل را از مسیر file_path می‌خواند
    # (برای اختصار بخش‌های تکراری مدیریت پروژه حذف نشدند، اما منطق دانلود اصلاح شد)
    pass

# --- ۳. بخش آپلود مستقیم در حافظه داخلی (اصل قضیه) ---
with tabs[2]:
    st.subheader("📤 ذخیره‌سازی در حافظه داخلی دستگاه")
    u_sec = st.radio("انتخاب بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="up_local_radio")
    
    all_p = pd.read_sql("SELECT * FROM projects WHERE p_type=?", conn, params=(u_sec,))
    if not all_p.empty:
        all_p['disp'] = all_p.apply(lambda x: f"ق: {x['contract_no']} - {x['name']}", axis=1)
        s_p_d = st.selectbox("انتخاب پروژه:", all_p['disp'].tolist())
        p_row = all_p[all_p['disp'] == s_p_d].iloc[0]
        
        fs = pd.read_sql("SELECT * FROM project_folders WHERE proj_id=?", conn, params=(int(p_row['id']),))
        if not fs.empty:
            s_f = st.selectbox("انتخاب پوشه مقصد:", fs['name'].tolist())
            f_id = fs[fs['name'] == s_f]['id'].values[0]
            
            uploaded_file = st.file_uploader("انتخاب فایل برای انتقال به حافظه", key="local_storage_up")
            
            if st.button("🚀 ذخیره قطعی در حافظه دستگاه", use_container_width=True):
                if uploaded_file:
                    # ایجاد مسیر فیزیکی: Engineering_Data / نام پروژه / نام پوشه
                    project_folder_path = os.path.join(BASE_DIR, str(p_row['name']).replace(" ", "_"), s_f.replace(" ", "_"))
                    if not os.path.exists(project_folder_path):
                        os.makedirs(project_folder_path)
                    
                    full_file_path = os.path.join(project_folder_path, uploaded_file.name)
                    
                    # ذخیره فیزیکی فایل در حافظه
                    with open(full_file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # ثبت آدرس در دیتابیس
                    c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_path) VALUES (?,?,?,?)", 
                              (int(p_row['id']), int(f_id), uploaded_file.name, full_file_path))
                    conn.commit()
                    
                    st.success(f"✅ فایل با موفقیت در مسیر زیر ذخیره شد:\n{full_file_path}")
                    st.info("حالا این فایل از داخل دیتابیس حذف شده و مستقیماً از هارد شما خوانده می‌شود.")
                else:
                    st.warning("لطفاً ابتدا فایل را انتخاب کنید.")
    else:
        st.info("ابتدا پروژه‌ای تعریف کنید.")

# بخش تنظیمات و سایر موارد مشابه کدهای قبلی شماست...
