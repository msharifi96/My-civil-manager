import streamlit as st
import pandas as pd
import sqlite3
import base64

# ۱. اتصال به دیتابیس
DB_NAME = 'civil_pro_final_v26.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

# ایجاد جداول
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, p_type TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, company TEXT, contract_no TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل CSS برای حذف کامل مربع‌ها و تنظیم جهت‌ها
st.markdown("""
    <style>
    /* راست‌چین کردن متون عمومی */
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { 
        direction: rtl !important; 
        text-align: right !important; 
    }
    
    /* حذف کادر، مربع و پس‌زمینه دکمه‌های عملیاتی */
    div[data-testid="column"] button, 
    div[data-testid="stDownloadButton"] button {
        border: none !important;
        background: transparent !important;
        background-color: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
        width: 35px !important;
        height: 35px !important;
        display: flex;
        justify-content: center;
        align-items: center;
    }

    /* حذف افکت مربع هنگام نگه داشتن موس (Hover) */
    button:hover, button:active, button:focus {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }

    /* تنظیم چیدمان ستون‌ها: ستون اول (راست) و ستون دوم (چپ) */
    [data-testid="column"]:nth-child(2) {
        display: flex;
        justify-content: flex-end !important;
        order: 1; /* نام فایل در سمت راست */
    }
    [data-testid="column"]:nth-child(1) {
        display: flex;
        justify-content: flex-start !important;
        order: -1; /* آیکون‌ها در سمت چپ */
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
                        # اینجا جای ستون‌ها را برای رسیدن به خواسته شما تنظیم کردم:
                        # ستون اول برای آیکون‌ها (سمت چپ) و ستون دوم برای نام فایل (سمت راست)
                        col_icons, col_name = st.columns([1, 4])
                        
                        with col_name:
                            st.markdown(f"<div style='padding-top:8px;'>📄 {fl['file_name']}</div>", unsafe_allow_html=True)
                        
                        with col_icons:
                            i1, i2, i3 = st.columns(3)
                            # حذف
                            if i1.button("🗑️", key=f"del_{fl['id']}"):
                                c.execute(f"DELETE FROM project_files WHERE id={fl['id']}")
                                conn.commit()
                                st.rerun()
                            # لینک
                            if i2.button("🔗", key=f"lnk_{fl['id']}"):
                                b64 = base64.b64encode(fl['file_blob']).decode()
                                st.toast("لینک تولید شد")
                                st.code(f"data:file;base64,{b64[:15]}...")
                            # دانلود
                            i3.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dw_{fl['id']}")

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# بقیه کدهای مربوط به آپلود و تنظیمات مشابه قبل ادامه می‌یابد...
