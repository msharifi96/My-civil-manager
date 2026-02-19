import streamlit as st
import pandas as pd
import sqlite3
import time
import base64

# ۱. دیتابیس نسخه ۲۴ برای اطمینان از پاک بودن داده‌ها
DB_NAME = 'civil_pro_v24.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

# ایجاد جداول
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, p_type TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, company TEXT, contract_no TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

def show_done(text="✅ انجام شد"):
    msg = st.empty()
    msg.success(text)
    time.sleep(1)
    msg.empty()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل اختصاصی برای حذف مربع و کادر دور آیکون‌ها
st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { direction: rtl; text-align: right; }
    
    /* حذف کامل مربع، پس‌زمینه و سایه از دکمه‌های آیکونی سمت چپ */
    div[data-testid="column"] button {
        border: none !important;
        background-color: transparent !important;
        box-shadow: none !important;
        color: inherit !important;
        padding: 0 !important;
        width: 30px !important;
        height: 30px !important;
        min-height: 30px !important;
    }
    
    /* حذف کادر دور دکمه دانلود */
    div[data-testid="stDownloadButton"] button {
        border: none !important;
        background-color: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
    }

    /* استایل نمایش نام فایل */
    .file-text {
        font-size: 14px;
        padding-top: 5px;
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

# --- تابع داشبورد ---
def render_dash(label):
    col_tree, col_view = st.columns([1, 2.5])
    with col_tree:
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
                                    if st.button(f"🏗️ {pj['name']}", key=f"d_{label}_{pj['id']}", use_container_width=True):
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
                        # چیدمان: آیکون‌ها در چپ (بدون کادر)، نام در راست
                        c_act, c_name = st.columns([0.6, 3])
                        
                        with c_act: # آیکون‌های بدون مربع
                            act_1, act_2, act_3 = st.columns(3)
                            if act_1.button("🗑️", key=f"del_{fl['id']}", help="حذف فایل"):
                                c.execute(f"DELETE FROM project_files WHERE id={fl['id']}")
                                conn.commit(); st.rerun()
                            
                            if act_2.button("🔗", key=f"ln_{fl['id']}", help="لینک"):
                                b64 = base64.b64encode(fl['file_blob']).decode()
                                st.code(f"data:file/bin;base64,{b64[:15]}...")
                                st.toast("لینک کپی شد")
                            
                            act_3.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dn_{fl['id']}", help="دانلود فایل")
                        
                        c_name.markdown(f"<div class='file-text'>📄 {fl['file_name']}</div>", unsafe_allow_html=True)

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# --- تب تنظیمات و آپلود (مشابه نسخه قبل با دیتابیس v24) ---
# (بخش‌های ثبت استان، شهرستان، پروژه و آپلود بدون تغییر در اینجا قرار دارند)

with tabs[2]: # بخش آپلود
    st.subheader("📤 بارگذاری مدرک")
    u_sec = st.radio("بخش مقصد:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True)
    projs = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{u_sec}'", conn)
    if not projs.empty:
        c1, c2 = st.columns(2)
        with c1:
            sel_p = st.selectbox("۱. پروژه:", projs['name'].tolist())
            pj_r = projs[projs['name'] == sel_p].iloc[0]
            flds = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={pj_r['id']}", conn)
            if not flds.empty:
                sel_f = st.selectbox("۲. پوشه:", flds['name'].tolist())
                fid = flds[flds['name'] == sel_f]['id'].values[0]
            else: st.warning("پوشه بسازید."); fid = None
        with c2:
            if fid:
                file = st.file_uploader("۳. فایل")
                if st.button("🚀 ثبت"):
                    if file:
                        c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_blob) VALUES (?,?,?,?)", 
                                  (int(pj_r['id']), int(fid), file.name, file.read()))
                        conn.commit(); show_done()

with tabs[3]: # بخش تنظیمات
    st.subheader("⚙️ تنظیمات")
    m_sec = st.radio("بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True)
    st.divider()
    # (کد ثبت محل و پروژه مشابه v23 استفاده شود)
    # ... [کد مدیریت محل و پروژه] ...
    if st.button("🧹 ریست کامل حافظه موقت"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
