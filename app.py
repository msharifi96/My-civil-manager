import streamlit as st
import pandas as pd
import sqlite3
import time
import base64

# اتصال به دیتابیس نسخه ۲۲
conn = sqlite3.connect('civil_pro_v22.db', check_same_thread=False)
c = conn.cursor()

def show_done(text="✅ انجام شد"):
    msg = st.empty()
    msg.success(text)
    time.sleep(1)
    msg.empty()

def get_shareable_link(file_name, file_blob):
    b64 = base64.b64encode(file_blob).decode()
    return f"data:application/octet-stream;base64,{b64}"

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل اختصاصی برای چیدمان آیکون‌ها در سمت چپ و نام در راست
st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { direction: rtl; text-align: right; }
    /* فشرده‌سازی دکمه‌ها */
    .stButton>button { width: 100%; border-radius: 6px; padding: 2px 5px; height: 2.2em; }
    /* استایل خاص برای ردیف فایل‌ها */
    .file-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee; padding: 5px 0; }
    .file-name { flex-grow: 1; text-align: right; font-size: 0.9em; }
    .file-actions { display: flex; gap: 4px; flex-shrink: 0; }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

def render_dash(label):
    col_t, col_v = st.columns([1, 2.5])
    with col_t:
        st.subheader(f"🗂️ آرشیو {label}")
        provs = pd.read_sql(f"SELECT * FROM locations WHERE level='استان' AND p_type='{label}'", conn)
        for _, prov in provs.iterrows():
            with st.expander(f"🔹 {prov['name']}"):
                cnts = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND parent_id={prov['id']}", conn)
                for _, cnt in cnts.iterrows():
                    with st.expander(f"📂 {cnt['name']}"):
                        vls = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id={cnt['id']}", conn)
                        for _, vl in vls.iterrows():
                            with st.expander(f"📍 {vl['name']}"):
                                pjs = pd.read_sql(f"SELECT * FROM projects WHERE loc_id={vl['id']} AND p_type='{label}'", conn)
                                for _, pj in pjs.iterrows():
                                    if st.button(f"🏗️ {pj['name']}", key=f"d_{label}_{pj['id']}"):
                                        st.session_state[f'act_{label}'] = pj.to_dict()

    with col_v:
        if f'act_{label}' in st.session_state:
            pj = st.session_state[f'act_{label}']
            st.header(f"پروژه: {pj['name']}")
            st.info(f"🏢 شرکت: {pj['company']} | 📄 قرارداد: {pj['contract_no']}")
            
            flds = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={pj['id']}", conn)
            for _, fld in flds.iterrows():
                with st.expander(f"📁 {fld['name']}", expanded=True):
                    files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
                    if files.empty:
                        st.caption("فایلی در این پوشه نیست.")
                    for _, fl in files.iterrows():
                        # استفاده از ستون‌های استریم‌لیت با نسبت‌بندی دقیق برای انتقال آیکون‌ها به چپ
                        c_actions, c_name = st.columns([1, 3])
                        
                        # نام فایل در سمت راست
                        c_name.markdown(f"<div style='padding-top:5px;'>📄 {fl['file_name']}</div>", unsafe_allow_html=True)
                        
                        # دکمه‌ها در سمت چپ (در یک ردیف فشرده)
                        with c_actions:
                            act_col1, act_col2, act_col3 = st.columns(3)
                            # حذف
                            if act_col1.button("🗑️", key=f"del_{fl['id']}", help="حذف"):
                                c.execute(f"DELETE FROM project_files WHERE id={fl['id']}")
                                conn.commit()
                                st.rerun()
                            # لینک
                            if act_col2.button("🔗", key=f"link_{fl['id']}", help="کپی لینک"):
                                link = get_shareable_link(fl['file_name'], fl['file_blob'])
                                st.toast("لینک آماده کپی است")
                                st.code(link[:50] + "...") # نمایش کوتاه لینک
                            # دانلود
                            act_col3.download_button("📥", fl['file_blob'], fl['file_name'], key=f"down_{fl['id']}", help="دانلود")

# ادامه تب‌ها (بخش آپلود و تنظیمات ثابت است...)
with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# بخش آپلود و تنظیمات (کد قبلی شما در اینجا قرار می‌گیرد)
# ... (بقیه کد v22 بدون تغییر)
