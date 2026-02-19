import streamlit as st
import pandas as pd
import sqlite3
import base64

# ۱. اتصال به دیتابیس
DB_NAME = 'civil_pro_final_v26.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل CSS برای حذف مربع‌ها و چسباندن آیکون‌ها به هم
st.markdown("""
    <style>
    /* تنظیمات کلی راست‌چین */
    .main, .stTabs, .stSelectbox, .stTextInput, .stMarkdown, p, h1, h2, h3 { 
        direction: rtl; 
        text-align: right; 
    }
    
    /* حذف مربع، سایه و پس‌زمینه از دکمه‌های آیکونی */
    .file-ops-container button, 
    .file-ops-container div[data-testid="stDownloadButton"] > button {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
        width: 28px !important;
        height: 28px !important;
        min-height: unset !important;
    }

    /* نزدیک کردن آیکون‌ها به هم */
    .file-ops-container div[data-testid="column"] {
        width: fit-content !important;
        flex: unset !important;
        min-width: 32px !important;
        gap: 0px !important;
    }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

def render_dash(label):
    col_tree, col_view = st.columns([1, 2.5])
    
    with col_tree:
        st.subheader(f"آرشیو {label}")
        # لود کردن لیست‌ها (مشابه نسخه ۲۶)
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
                        # ایجاد دو ستون: نام در راست و آیکون‌ها در چپ
                        c_icons, c_name = st.columns([1, 4])
                        
                        with c_name:
                            st.markdown(f"<div style='padding-top:8px;'>📄 {fl['file_name']}</div>", unsafe_allow_html=True)
                        
                        with c_icons:
                            # اعمال کلاس برای حذف کادرها و کم کردن فاصله
                            st.markdown('<div class="file-ops-container">', unsafe_allow_html=True)
                            i1, i2, i3 = st.columns(3)
                            # حذف
                            if i1.button("🗑️", key=f"del_{fl['id']}"):
                                c.execute(f"DELETE FROM project_files WHERE id={fl['id']}")
                                conn.commit(); st.rerun()
                            # لینک
                            if i2.button("🔗", key=f"lnk_{fl['id']}"):
                                b64 = base64.b64encode(fl['file_blob']).decode()
                                st.toast("لینک ساخته شد")
                                st.code(f"data:file;base64,{b64[:10]}...")
                            # دانلود
                            i3.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dw_{fl['id']}")
                            st.markdown('</div>', unsafe_allow_html=True)

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# بقیه کدهای آپلود و تنظیمات از نسخه ۲۶ بدون تغییر باقی بماند...
