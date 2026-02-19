import streamlit as st
import pandas as pd
import sqlite3
import time

# اتصال به دیتابیس (استفاده از نسخه ثابت برای حفظ داده‌ها)
conn = sqlite3.connect('civil_pro_v18.db', check_same_thread=False)
c = conn.cursor()

# اطمینان از وجود ستون p_type در همه جداول کلیدی
try:
    c.execute('ALTER TABLE project_folders ADD COLUMN p_type TEXT')
    conn.commit()
except:
    pass

def show_done():
    msg = st.empty()
    msg.success("انجام شد")
    time.sleep(1)
    msg.empty()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل RTL
st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #004a99; color: white; }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات"])

# --- توابع داشبورد (مشابه قبل) ---
def render_dashboard(p_type_filter):
    c_tree, c_view = st.columns([1, 2])
    with c_tree:
        st.subheader(f"بایگانی {p_type_filter}")
        provs = pd.read_sql(f"SELECT * FROM locations WHERE level='استان' AND p_type='{p_type_filter}'", conn)
        for _, prov in provs.iterrows():
            with st.expander(f"📁 {prov['name']}"):
                cnts = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND parent_id={prov['id']}", conn)
                for _, cnt in cnts.iterrows():
                    with st.expander(f"📂 {cnt['name']}"):
                        vls = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id={cnt['id']}", conn)
                        for _, vl in vls.iterrows():
                            with st.expander(f"📍 {vl['name']}"):
                                pjs = pd.read_sql(f"SELECT * FROM projects WHERE loc_id={vl['id']} AND p_type='{p_type_filter}'", conn)
                                for _, pj in pjs.iterrows():
                                    if st.button(f"🏗️ {pj['name']}", key=f"btn_{p_type_filter}_{pj['id']}"):
                                        st.session_state[f'act_id_{p_type_filter}'] = pj['id']
                                        st.session_state[f'act_n_{p_type_filter}'] = pj['name']
    with c_view:
        active_id_key = f'act_id_{p_type_filter}'
        if active_id_key in st.session_state:
            st.header(f"پروژه: {st.session_state[f'act_n_{p_type_filter}']}")
            folders = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={st.session_state[active_id_key]}", conn)
            for _, fld in folders.iterrows():
                files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
                with st.expander(f"📁 {fld['name']} ({len(files)} فایل)"):
                    for _, fl in files.iterrows():
                        c1, c2 = st.columns([4, 1])
                        c1.text(fl['file_name'])
                        c2.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dl_{fl['id']}_{p_type_filter}")

with tabs[0]: render_dashboard("نظارتی 🛡️")
with tabs[1]: render_dashboard("شخصی 👷")

# --- اصلاح بخش آپلود (رفع مشکل تصویر شما) ---
with tabs[2]:
    st.subheader("📤 بارگذاری مدارک")
    u_sec = st.radio("بارگذاری در کدام بخش؟", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="up_main_radio")
    
    # واکشی پروژه‌های بخش انتخاب شده
    up_projs = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{u_sec}'", conn)
    
    if not up_projs.empty:
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            s_up_p = st.selectbox("۱. انتخاب پروژه:", up_projs['name'].tolist(), key="up_p_selectbox")
            u_pid = up_projs[up_projs['name'] == s_up_p]['id'].values[0]
            
            # واکشی تمام پوشه‌های متعلق به این پروژه (بدون سخت‌گیری روی p_type پوشه)
            up_flds = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={u_pid}", conn)
            
            if not up_flds.empty:
                s_up_f = st.selectbox("۲. انتخاب پوشه مقصد:", up_flds['name'].tolist(), key="up_f_selectbox")
                u_fid = up_flds[up_flds['name'] == s_up_f]['id'].values[0]
            else:
                st.warning("⚠️ پوشه‌ای برای این پروژه یافت نشد. ابتدا در تب '📍 تنظیمات' برای این پروژه پوشه بسازید.")
                u_fid = None
        
        with col_u2:
            if u_fid:
                up_file = st.file_uploader("۳. انتخاب فایل برای بارگذاری", key="main_file_uploader")
                if st.button("🚀 شروع آپلود", key="start_upload_btn"):
                    if up_file:
                        c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_blob) VALUES (?,?,?,?)", 
                                  (u_pid, u_fid, up_file.name, up_file.read()))
                        conn.commit()
                        show_done()
    else:
        st.info(f"در بخش {u_sec} هنوز پروژه‌ای تعریف نکرده‌اید.")

# --- تب تنظیمات (مشابه قبل) ---
with tabs[3]:
    st.subheader("📍 تنظیمات سیستم")
    m_sec = st.radio("تنظیمات برای:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="m_setting_radio")
    cl1, cl2 = st.columns(2)
    with cl1:
        st.subheader("🛠️ مدیریت مناطق")
        # کدهای ثبت منطقه ...
        lvl = st.radio("سطح:", ["استان", "شهرستان", "محل"], horizontal=True, key="loc_lvl_radio")
        # (بقیه کد تنظیمات مناطق)
    with cl2:
        st.subheader("🏗️ مدیریت پروژه‌ها")
        # (بقیه کد تنظیمات پروژه‌ها و پوشه‌ها)
