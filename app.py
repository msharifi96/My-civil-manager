import streamlit as st
import pandas as pd
import sqlite3
import time

# اتصال به دیتابیس
conn = sqlite3.connect('civil_pro_v19.db', check_same_thread=False)
c = conn.cursor()

# ایجاد جداول با ساختار دقیق تفکیک‌شده
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, p_type TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

def show_done():
    msg = st.empty()
    msg.success("✅ با موفقیت ثبت شد")
    time.sleep(1)
    msg.empty()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل RTL (راست‌چین)
st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #004a99; color: white; height: 3em; font-weight: bold; }
    .stExpander { border: 1px solid #004a99; border-radius: 5px; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# تعریف ۴ تب مجزا طبق درخواست شما
tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

# --- تابع نمایش داشبورد ---
def render_dash(p_type_label):
    col_tree, col_view = st.columns([1, 2])
    with col_tree:
        st.subheader(f"🗂️ آرشیو {p_type_label}")
        provs = pd.read_sql(f"SELECT * FROM locations WHERE level='استان' AND p_type='{p_type_label}'", conn)
        for _, prov in provs.iterrows():
            with st.expander(f"🔹 {prov['name']}"):
                cnts = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND parent_id={prov['id']}", conn)
                for _, cnt in cnts.iterrows():
                    with st.expander(f"🔸 {cnt['name']}"):
                        vls = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id={cnt['id']}", conn)
                        for _, vl in vls.iterrows():
                            with st.expander(f"📍 {vl['name']}"):
                                pjs = pd.read_sql(f"SELECT * FROM projects WHERE loc_id={vl['id']} AND p_type='{p_type_label}'", conn)
                                for _, pj in pjs.iterrows():
                                    if st.button(f"🏗️ {pj['name']}", key=f"d_{p_type_label}_{pj['id']}"):
                                        st.session_state[f'act_p_{p_type_label}'] = (pj['id'], pj['name'])
    with col_view:
        key_act = f'act_p_{p_type_label}'
        if key_act in st.session_state:
            pid, pname = st.session_state[key_act]
            st.header(f"پروژه: {pname}")
            flds = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={pid}", conn)
            for _, fld in flds.iterrows():
                files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
                with st.expander(f"📁 {fld['name']} ({len(files)} فایل)"):
                    for _, fl in files.iterrows():
                        c1, c2 = st.columns([4, 1])
                        c1.text(f"📄 {fl['file_name']}")
                        c2.download_button("📥", fl['file_blob'], fl['file_name'], key=f"f_{fl['id']}")
        else: st.info("لطفاً یک پروژه را از لیست سمت راست انتخاب کنید.")

# --- اجرای تب‌ها ---
with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

with tabs[2]: # آپلود فایل (اصلاح شده)
    st.subheader("📤 بارگذاری مدرک جدید")
    u_sec = st.radio("بخش مورد نظر:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="up_sec_choice")
    
    projs = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{u_sec}'", conn)
    if not projs.empty:
        c1, c2 = st.columns(2)
        with c1:
            sel_p = st.selectbox("۱. پروژه را انتخاب کنید:", projs['name'].tolist(), key="up_p_select")
            pid = projs[projs['name'] == sel_p]['id'].values[0]
            
            flds = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={pid}", conn)
            if not flds.empty:
                sel_f = st.selectbox("۲. پوشه را انتخاب کنید:", flds['name'].tolist(), key="up_f_select")
                fid = flds[flds['name'] == sel_f]['id'].values[0]
            else:
                st.warning("⚠️ برای این پروژه هنوز پوشه‌ای نساخته‌اید.")
                fid = None
        with c2:
            if fid:
                file = st.file_uploader("۳. فایل را انتخاب کنید", key="file_up_widget")
                if st.button("💾 ثبت در دیتابیس"):
                    if file:
                        c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_blob) VALUES (?,?,?,?)", 
                                  (pid, fid, file.name, file.read()))
                        conn.commit(); show_done()
    else: st.info(f"ابتدا در تب تنظیمات، برای بخش {u_sec} پروژه تعریف کنید.")

with tabs[3]: # تنظیمات سیستم
    st.subheader("⚙️ تنظیمات و تعریف پایه")
    m_sec = st.radio("تنظیمات برای بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="m_set_sec")
    st.divider()
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("📍 مدیریت مناطق")
        lvl = st.radio("سطح تعریف:", ["استان", "شهرستان", "محل"], horizontal=True)
        if lvl == "استان":
            n = st.text_input("نام استان جدید")
            if st.button("ثبت استان"):
                c.execute("INSERT INTO locations (name, level, p_type, parent_id) VALUES (?,?,?,0)", (n, "استان", m_sec))
                conn.commit(); show_done(); st.rerun()
        elif lvl == "شهرستان":
            ps = pd.read_sql(f"SELECT * FROM locations WHERE level='استان' AND p_type='{m_sec}'", conn)
            if not ps.empty:
                sp = st.selectbox("استان مادر:", ps['name'].tolist())
                pi = ps[ps['name'] == sp]['id'].values[0]
                n = st.text_input("نام شهرستان جدید")
                if st.button("ثبت شهرستان"):
                    c.execute("INSERT INTO locations (name, level, p_type, parent_id) VALUES (?,?,?,?)", (n, "شهرستان", m_sec, int(pi)))
                    conn.commit(); show_done(); st.rerun()
        else:
            cs = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND p_type='{m_sec}'", conn)
            if not cs.empty:
                sc = st.selectbox("شهرستان مادر:", cs['name'].tolist())
                pi = cs[cs['name'] == sc]['id'].values[0]
                tp = st.selectbox("نوع محل:", ["شهر 🏙️", "روستا 🏡"])
                n = st.text_input("نام محل (شهر/روستا)")
                if st.button("ثبت محل نهایی"):
                    fn = f"{tp} {n}"
                    c.execute("INSERT INTO locations (name, level, p_type, parent_id) VALUES (?,?,?,?)", (fn, "شهر یا روستا", m_sec, int(pi)))
                    conn.commit(); show_done(); st.rerun()

    with col_b:
        st.subheader("🏗️ مدیریت پروژه‌ها")
        vills = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type='{m_sec}'", conn)
        if not vills.empty:
            sv = st.selectbox("محل پروژه:", vills['name'].tolist(), key="p_v_s")
            vi = vills[vills['name'] == sv]['id'].values[0]
            pn = st.text_input("نام پروژه:")
            if st.button("ثبت پروژه جدید"):
                c.execute("INSERT INTO projects (loc_id, name, p_type) VALUES (?,?,?)", (int(vi), pn, m_sec))
                conn.commit(); show_done(); st.rerun()
        
        st.divider()
        st.subheader("📁 ساخت پوشه")
        pjs = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{m_sec}'", conn)
        if not pjs.empty:
            spj = st.selectbox("انتخاب پروژه:", pjs['name'].tolist(), key="f_p_s")
            pji = pjs[pjs['name'] == spj]['id'].values[0]
            fn = st.text_input("نام پوشه جدید (مثلاً: عکس‌های روزانه)")
            if st.button("ایجاد پوشه"):
                c.execute("INSERT INTO project_folders (proj_id, name, p_type) VALUES (?,?,?)", (pji, fn, m_sec))
                conn.commit(); show_done()
