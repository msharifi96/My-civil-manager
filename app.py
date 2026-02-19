import streamlit as st
import pandas as pd
import sqlite3
import time
import base64

# ۱. استفاده از یک دیتابیس کاملاً جدید برای شروع صفر مطلق
DB_NAME = 'civil_pro_final_v25.db'
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
c = conn.cursor()

# ایجاد جداول خام
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, p_type TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, company TEXT, contract_no TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل برای حذف مربع دور آیکون‌ها و راست‌چین کردن
st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { direction: rtl; text-align: right; }
    
    /* حذف کادر و پس‌زمینه دکمه‌های آیکونی */
    div[data-testid="column"] button {
        border: none !important;
        background-color: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
        width: 30px !important;
    }
    div[data-testid="stDownloadButton"] button {
        border: none !important;
        background-color: transparent !important;
        padding: 0 !important;
    }
    .file-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

# --- بخش نمایش (داشبورد) ---
def render_dash(label):
    col_tree, col_view = st.columns([1, 2.5])
    
    with col_tree:
        st.subheader(f"آرشیو {label}")
        # خواندن مستقیم از دیتابیس - هیچ نامی اینجا دستی نوشته نشده است
        provs = pd.read_sql(f"SELECT * FROM locations WHERE level='استان' AND p_type='{label}'", conn)
        
        if provs.empty:
            st.info("هنوز هیچ استانی ثبت نشده است.")
        
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
                                    if st.button(f"🏗️ {pj['name']}", key=f"btn_{label}_{pj['id']}", use_container_width=True):
                                        st.session_state[f'act_{label}'] = pj.to_dict()

    with col_view:
        if f'act_{label}' in st.session_state:
            pj = st.session_state[f'act_{label}']
            st.header(f"پروژه: {pj['name']}")
            st.write(f"🏢 شرکت: {pj['company']} | 📄 قرارداد: {pj['contract_no']}")
            
            flds = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={pj['id']}", conn)
            for _, fld in flds.iterrows():
                with st.expander(f"📁 {fld['name']}", expanded=True):
                    files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
                    for _, fl in files.iterrows():
                        # چیدمان: آیکون‌ها سمت چپ، نام سمت راست
                        c_actions, c_name = st.columns([0.6, 3])
                        with c_actions:
                            a1, a2, a3 = st.columns(3)
                            if a1.button("🗑️", key=f"d_{fl['id']}"):
                                c.execute(f"DELETE FROM project_files WHERE id={fl['id']}")
                                conn.commit(); st.rerun()
                            if a2.button("🔗", key=f"l_{fl['id']}"):
                                b64 = base64.b64encode(fl['file_blob']).decode()
                                st.toast("لینک آماده شد"); st.code(f"data:file;{b64[:10]}...")
                            a3.download_button("📥", fl['file_blob'], fl['file_name'], key=f"s_{fl['id']}")
                        
                        c_name.markdown(f"<div style='text-align:right;'>📄 {fl['file_name']}</div>", unsafe_allow_html=True)

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# --- بخش آپلود ---
with tabs[2]:
    st.subheader("📤 آپلود مدارک")
    u_sec = st.radio("بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True)
    all_p = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{u_sec}'", conn)
    if not all_p.empty:
        c1, c2 = st.columns(2)
        with c1:
            s_p = st.selectbox("پروژه:", all_p['name'].tolist())
            p_id = all_p[all_p['name']==s_p]['id'].values[0]
            fs = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={p_id}", conn)
            if not fs.empty:
                s_f = st.selectbox("پوشه:", fs['name'].tolist())
                f_id = fs[fs['name']==s_f]['id'].values[0]
                up_file = st.file_uploader("انتخاب فایل")
                if st.button("ثبت فایل") and up_file:
                    c.execute("INSERT INTO project_files (proj_id,folder_id,file_name,file_blob) VALUES (?,?,?,?)",
                              (int(p_id), int(f_id), up_file.name, up_file.read()))
                    conn.commit(); st.success("انجام شد")
            else: st.warning("ابتدا پوشه بسازید.")

# --- بخش تنظیمات (بدون نام پیش‌فرض) ---
with tabs[3]:
    st.subheader("⚙️ تنظیمات سیستم")
    m_sec = st.radio("بخش کاری:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="m_s")
    st.divider()
    cl, cr = st.columns(2)
    with cl:
        st.subheader("📍 مدیریت محل")
        ps = pd.read_sql(f"SELECT * FROM locations WHERE level='استان' AND p_type='{m_sec}'", conn)
        # انتخاب استان (فقط اگر قبلاً چیزی ثبت شده باشد نشان می‌دهد)
        s_p = st.selectbox("استان:", ["--- جدید ---"] + ps['name'].tolist())
        if s_p == "--- جدید ---":
            np = st.text_input("نام استان جدید:")
            if st.button("ثبت استان"):
                c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,0)", (np,"استان",m_sec))
                conn.commit(); st.rerun()
        else:
            p_id = ps[ps['name']==s_p]['id'].values[0]
            cs = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND parent_id={p_id}", conn)
            s_c = st.selectbox("شهرستان:", ["--- جدید ---"] + cs['name'].tolist())
            if s_c == "--- جدید ---":
                nc = st.text_input("نام شهرستان:")
                if st.button("ثبت شهرستان"):
                    c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(nc,"شهرستان",m_sec,int(p_id)))
                    conn.commit(); st.rerun()
            else:
                c_id = cs[cs['name']==s_c]['id'].values[0]
                vs = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id={c_id}", conn)
                s_v = st.selectbox("شهر/روستا:", ["--- جدید ---"] + vs['name'].tolist())
                if s_v == "--- جدید ---":
                    nv = st.text_input("نام محل:"); t = st.selectbox("نوع:",["شهر","روستا"])
                    if st.button("ثبت محل"):
                        c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(f"{t} {nv}","شهر یا روستا",m_sec,int(c_id)))
                        conn.commit(); st.rerun()

    with cr:
        st.subheader("🏗️ پروژه و پوشه")
        # همه چیز بر اساس ورودی‌های شما لود می‌شود
        v_l = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type='{m_sec}'", conn)
        if not v_l.empty:
            sv = st.selectbox("انتخاب محل:", v_l['name'].tolist())
            pn = st.text_input("نام پروژه:"); cp = st.text_input("شرکت:"); cn = st.text_input("قرارداد:")
            if st.button("ثبت پروژه"):
                v_id = v_l[v_l['name']==sv]['id'].values[0]
                c.execute("INSERT INTO projects (loc_id,name,company,contract_no,p_type) VALUES (?,?,?,?,?)",(int(v_id),pn,cp,cn,m_sec))
                conn.commit(); st.rerun()
        
        st.divider()
        all_p = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{m_sec}'", conn)
        if not all_p.empty:
            spj = st.selectbox("پروژه برای پوشه:", all_p['name'].tolist())
            nf = st.text_input("نام پوشه:")
            if st.button("ایجاد پوشه"):
                pid = all_p[all_p['name']==spj]['id'].values[0]
                c.execute("INSERT INTO project_folders (proj_id,name,p_type) VALUES (?,?,?)",(int(pid),nf,m_sec))
                conn.commit(); st.rerun()
