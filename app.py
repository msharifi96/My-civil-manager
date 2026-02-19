import streamlit as st
import pandas as pd
import sqlite3
import base64

# ۱. اتصال به دیتابیس
DB_NAME = 'civil_pro_final_v26.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل CSS نهایی و تهاجمی برای حذف مربع‌ها و تنظیم چیدمان
st.markdown("""
    <style>
    /* راست‌چین کردن کل محیط */
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { 
        direction: rtl !important; 
        text-align: right !important; 
    }
    
    /* حذف کادر، مربع و پس‌زمینه از تمام دکمه‌ها */
    button, div[data-testid="stDownloadButton"] > button {
        border: none !important;
        background: transparent !important;
        background-color: transparent !important;
        box-shadow: none !important;
        outline: none !important;
        padding: 0 !important;
        margin: 0 !important;
        min-height: unset !important;
        width: 32px !important;
        height: 32px !important;
    }

    /* حذف افکت مربع در حالت هوور */
    button:hover, button:active, button:focus {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }

    /* تنظیم ردیف فایل: نام در راست، آیکون‌ها در چپ */
    .file-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-direction: row-reverse; /* اجبار به قرارگیری نام در راست و آیکون در چپ */
        padding: 5px 0;
        border-bottom: 1px solid #eee;
    }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

def render_dash(label):
    col_tree, col_view = st.columns([1, 2.5])
    
    with col_tree:
        st.subheader(f"آرشیو {label}")
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
                                    if st.button(f"🏗️ {pj['name']}", key=f"pj_{label}_{pj['id']}", use_container_width=True):
                                        st.session_state[f'act_{label}'] = pj.to_dict()

    with col_view:
        if f'act_{label}' in st.session_state:
            pj = st.session_state[f'act_{label}']
            st.header(f"پروژه: {pj['name']}")
            st.info(f"🏢 شرکت: {pj['company']} | 📄 قرارداد: {pj['contract_no']}")
            
            flds = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={pj['id']}", conn)
            for _, fld in flds.iterrows():
                with st.expander(f"📁 {fld['name']}", expanded=True):
                    files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
                    for _, fl in files.iterrows():
                        # استفاده از ستون‌ها با ترتیب جدید
                        # ستون اول (آیکون‌ها) - ستون دوم (نام فایل)
                        col_icons, col_name = st.columns([1, 5])
                        
                        with col_name:
                            # نام فایل در سمت راست
                            st.markdown(f"<div style='text-align: right; direction: rtl; padding-top: 5px;'>📄 {fl['file_name']}</div>", unsafe_allow_html=True)
                        
                        with col_icons:
                            # آیکون‌ها در سمت چپ بدون هیچ کادری
                            ic1, ic2, ic3 = st.columns(3)
                            # دانلود
                            ic1.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dw_{fl['id']}")
                            # لینک
                            if ic2.button("🔗", key=f"ln_{fl['id']}"):
                                b64 = base64.b64encode(fl['file_blob']).decode()
                                st.toast("لینک تولید شد")
                                st.code(f"data:file;base64,{b64[:10]}...")
                            # حذف
                            if ic3.button("🗑️", key=f"dl_{fl['id']}"):
                                c.execute(f"DELETE FROM project_files WHERE id={fl['id']}")
                                conn.commit()
                                st.rerun()

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")
# ... بقیه کد (آپلود و تنظیمات) ...
