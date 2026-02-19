import streamlit as st
import pandas as pd
import sqlite3
import base64

# ۱. اتصال به دیتابیس
DB_NAME = 'civil_pro_final_v26.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

# ایجاد جداول (بدون وارد کردن دیتای اضافه)
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, p_type TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, company TEXT, contract_no TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل اختصاصی برای راست‌چین کردن و حذف مربع آیکون‌ها
st.markdown("""
    <style>
    /* راست‌چین کردن متون بدون دستکاری تب‌ها */
    .stApp { direction: rtl; text-align: right; }
    
    /* حذف کادر دور آیکون‌های عملیاتی فایل */
    div[data-testid="column"] button, 
    div[data-testid="stDownloadButton"] button {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
    }
    
    /* تنظیم فونت و ظاهر تب‌ها برای جلوگیری از به هم ریختگی */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        direction: rtl;
    }
    </style>
    """, unsafe_allow_html=True)

# تب‌ها دقیقاً مثل نسخه پایدار قبلی
tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

def render_dash(label):
    col_tree, col_view = st.columns([1, 2.5])
    
    with col_tree:
        st.subheader(f"آرشیو {label}")
        # لود کردن لیست‌ها فقط از دیتابیس (بدون نام‌های پیش‌فرض)
        provs = pd.read_sql(f"SELECT * FROM locations WHERE level='استان' AND p_type='{label}'", conn)
        if provs.empty:
            st.info("هنوز استانی ثبت نشده است.")
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
                        # چیدمان: نام در راست، آیکون‌ها در چپ
                        c_icons, c_name = st.columns([1, 4])
                        with c_name:
                            st.markdown(f"<div style='padding-top:5px;'>📄 {fl['file_name']}</div>", unsafe_allow_html=True)
                        with c_icons:
                            i1, i2, i3 = st.columns(3)
                            # دکمه‌های آیکونی بدون کادر
                            if i1.button("🗑️", key=f"del_{fl['id']}"):
                                c.execute(f"DELETE FROM project_files WHERE id={fl['id']}")
                                conn.commit(); st.rerun()
                            if i2.button("🔗", key=f"lnk_{fl['id']}"):
                                b64 = base64.b64encode(fl['file_blob']).decode()
                                st.toast("لینک ساخته شد")
                                st.code(f"data:file;base64,{b64[:10]}...")
                            i3.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dw_{fl['id']}")

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# بخش آپلود مدارک
with tabs[2]:
    st.subheader("📤 آپلود مدارک")
    u_sec = st.radio("بخش مقصد:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True)
    all_p = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{u_sec}'", conn)
    if not all_p.empty:
        s_p = st.selectbox("انتخاب پروژه:", all_p['name'].tolist())
        p_id = all_p[all_p['name']==s_p]['id'].values[0]
        fs = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={p_id}", conn)
        if not fs.empty:
            s_f = st.selectbox("انتخاب پوشه:", fs['name'].tolist())
            f_id = fs[fs['name']==s_f]['id'].values[0]
            up_file = st.file_uploader("انتخاب فایل")
            if st.button("ثبت نهایی") and up_file:
                c.execute("INSERT INTO project_files (proj_id,folder_id,file_name,file_blob) VALUES (?,?,?,?)",
                          (int(p_id), int(f_id), up_file.name, up_file.read()))
                conn.commit(); st.success("فایل ذخیره شد")
        else: st.warning("ابتدا در بخش تنظیمات برای این پروژه پوشه بسازید.")

with tabs[3]:
    st.subheader("📍 تنظیمات سیستم")
    st.info("از این بخش برای تعریف استان، شهرستان، پروژه و پوشه‌ها استفاده کنید.")
    # کدهای مربوط به اضافه کردن استان و پروژه مشابه نسخه ۲۶...
