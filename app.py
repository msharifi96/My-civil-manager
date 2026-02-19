import streamlit as st
import pandas as pd
import sqlite3
import time

# اتصال به دیتابیس
conn = sqlite3.connect('civil_pro_v18.db', check_same_thread=False)
c = conn.cursor()

# ایجاد جداول
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, p_type TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

def show_done():
    msg = st.empty()
    msg.success("انجام شد")
    time.sleep(1)
    msg.empty()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #004a99; color: white; }
    </style>
    """, unsafe_allow_html=True)

# تفکیک تب‌ها طبق درخواست شما
tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات"])

# --- تابع کمکی برای نمایش داشبوردها ---
def render_dashboard(p_type_filter):
    c_tree, c_view = st.columns([1, 2])
    with c_tree:
        st.subheader(f"بایگانی {p_type_filter}")
        provs = pd.read_sql(f"SELECT * FROM locations WHERE level='استان' AND p_type='{p_type_filter}'", conn)
        if provs.empty: st.info("هنوز منطقه‌ای تعریف نشده است.")
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
            if folders.empty: st.warning("پوشه‌ای یافت نشد.")
            for _, fld in folders.iterrows():
                files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
                with st.expander(f"📁 {fld['name']} ({len(files)} فایل)"):
                    for _, fl in files.iterrows():
                        c1, c2 = st.columns([4, 1])
                        c1.text(fl['file_name'])
                        c2.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dl_{fl['id']}_{p_type_filter}")
        else: st.info("یک پروژه را انتخاب کنید.")

# --- اجرای تب‌ها ---
with tabs[0]: render_dashboard("نظارتی 🛡️")
with tabs[1]: render_dashboard("شخصی 👷")

with tabs[2]: # آپلود فایل
    st.subheader("📤 بارگذاری مدارک")
    u_sec = st.radio("بارگذاری در کدام بخش؟", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="up_radio")
    up_projs = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{u_sec}'", conn)
    if not up_projs.empty:
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            s_up_p = st.selectbox("۱. انتخاب پروژه:", up_projs['name'].tolist(), key="up_p_s")
            u_pid = up_projs[up_projs['name'] == s_up_p]['id'].values[0]
            up_flds = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={u_pid}", conn)
            if not up_flds.empty:
                s_up_f = st.selectbox("۲. انتخاب پوشه:", up_flds['name'].tolist(), key="up_f_s")
                u_fid = up_flds[up_flds['name'] == s_up_f]['id'].values[0]
            else: st.warning("ابتدا پوشه بسازید."); u_fid = None
        with col_u2:
            if u_fid:
                up_file = st.file_uploader("۳. انتخاب فایل", key="up_file_widget")
                if st.button("🚀 ثبت نهایی در بایگانی"):
                    if up_file:
                        c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_blob) VALUES (?,?,?,?)", 
                                  (u_pid, u_fid, up_file.name, up_file.read()))
                        conn.commit(); show_done()
    else: st.info(f"پروژه‌ای در بخش {u_sec} تعریف نشده است.")

with tabs[3]: # تنظیمات
    st.subheader("📍 تنظیمات پایه")
    m_sec = st.radio("تنظیمات برای:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="m_sec_set")
    st.divider()
    cl1, cl2 = st.columns(2)
    with cl1:
        st.subheader("🛠️ مناطق")
        lvl = st.radio("سطح:", ["استان", "شهرستان", "محل"], horizontal=True, key="l_v_r")
        if lvl == "استان":
            ln = st.text_input("نام استان", key="p_i")
            if st.button("ثبت استان"):
                c.execute("INSERT INTO locations (name, level, p_type, parent_id) VALUES (?,?,?,0)", (ln, "استان", m_sec))
                conn.commit(); show_done(); st.rerun()
        elif lvl == "شهرستان":
            ps = pd.read_sql(f"SELECT * FROM locations WHERE level='استان' AND p_type='{m_sec}'", conn)
            if not ps.empty:
                sp = st.selectbox("استان مادر", ps['name'].tolist())
                pi = ps[ps['name'] == sp]['id'].values[0]
                ln = st.text_input("نام شهرستان", key="c_i")
                if st.button("ثبت شهرستان"):
                    c.execute("INSERT INTO locations (name, level, p_type, parent_id) VALUES (?,?,?,?)", (ln, "شهرستان", m_sec, int(pi)))
                    conn.commit(); show_done(); st.rerun()
        else:
            cs = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND p_type='{m_sec}'", conn)
            if not cs.empty:
                sc = st.selectbox("شهرستان مادر", cs['name'].tolist())
                pi = cs[cs['name'] == sc]['id'].values[0]
                lt = st.selectbox("نوع:", ["شهر 🏙️", "روستا 🏡"], key="t_s")
                ln_r = st.text_input("نام محل", key="v_i")
                if st.button("ثبت محل"):
                    fn = f"{lt} {ln_r}"
                    c.execute("INSERT INTO locations (name, level, p_type, parent_id) VALUES (?,?,?,?)", (fn, "شهر یا روستا", m_sec, int(pi)))
                    conn.commit(); show_done(); st.rerun()
    with cl2:
        st.subheader("🏗️ پروژه‌ها")
        vills = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type='{m_sec}'", conn)
        if not vills.empty:
            sv = st.selectbox("محل پروژه", vills['name'].tolist(), key="v_s_p")
            vi = vills[vills['name'] == sv]['id'].values[0]
            pn = st.text_input("نام پروژه", key="p_n_i")
            if st.button("ثبت پروژه"):
                c.execute("INSERT INTO projects (loc_id, name, p_type) VALUES (?,?,?)", (int(vi), pn, m_sec))
                conn.commit(); show_done(); st.rerun()
        st.divider()
        all_p = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{m_sec}'", conn)
        if not all_p.empty:
            spf = st.selectbox("انتخاب پروژه برای پوشه", all_p['name'].tolist())
            pif = all_p[all_p['name'] == spf]['id'].values[0]
            fn = st.text_input("نام پوشه", key="f_n_i")
            if st.button("ایجاد پوشه"):
                c.execute("INSERT INTO project_folders (proj_id, name, p_type) VALUES (?,?,?)", (pif, fn, m_sec))
                conn.commit(); show_done()
