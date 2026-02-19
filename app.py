import streamlit as st
import pandas as pd
import sqlite3

# اتصال به دیتابیس (نام فایل ثابت ماند تا اطلاعات نپرد)
conn = sqlite3.connect('civil_final_v1.db', check_same_thread=False)
c = conn.cursor()

# ایجاد جداول ضروری در صورت عدم وجود
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #004a99; color: white; font-weight: bold; }
    .sidebar-tree { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 3px solid #004a99; min-height: 80vh; }
    .content-view { background-color: #ffffff; padding: 20px; border: 1px solid #dee2e6; border-radius: 10px; min-height: 80vh; }
    .stat-box { background-color: #f1f3f5; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-right: 5px solid #28a745; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["📊 داشبورد", "🏗️ پروژه‌ها", "📍 تنظیمات مناطق"])

# --- تب تنظیمات مناطق ---
with tabs[2]:
    st.subheader("مدیریت مناطق")
    col1, col2 = st.columns(2)
    with col1:
        lvl = st.radio("سطح جدید:", ["استان", "شهرستان", "شهر یا روستا"], horizontal=True)
        pid = 0
        if lvl != "استان":
            t_lvl = "استان" if lvl == "شهرستان" else "شهرستان"
            parents = pd.read_sql(f"SELECT * FROM locations WHERE level='{t_lvl}'", conn)
            if not parents.empty:
                sel_p = st.selectbox(f"انتخاب {t_lvl}", parents['name'].tolist())
                pid = parents[parents['name'] == sel_p]['id'].values[0]
        l_name = st.text_input(f"نام {lvl}")
        if st.button(f"ثبت {lvl}"):
            c.execute("INSERT INTO locations (name, level, parent_id) VALUES (?,?,?)", (l_name, lvl, int(pid)))
            conn.commit(); st.success("انجام شد")
    with col2:
        all_l = pd.read_sql("SELECT * FROM locations", conn)
        if not all_l.empty:
            del_n = st.selectbox("حذف منطقه", all_l['name'].tolist())
            if st.button("حذف نهایی"):
                c.execute("DELETE FROM locations WHERE name=?", (del_n,))
                conn.commit(); st.success("انجام شد"); st.rerun()

# --- تب پروژه‌ها ---
with tabs[1]:
    st.subheader("مدیریت پروژه‌ها و فایل‌ها")
    p_sec = st.radio("بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True)
    cp1, cp2 = st.columns(2)
    with cp1:
        vills = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا'", conn)
        if not vills.empty:
            sv = st.selectbox("انتخاب شهر یا روستا", vills['name'].tolist())
            vid = vills[vills['name'] == sv]['id'].values[0]
            pn = st.text_input("نام پروژه")
            if st.button("ثبت"):
                c.execute("INSERT INTO projects (loc_id, name, p_type) VALUES (?,?,?)", (int(vid), pn, p_sec))
                conn.commit(); st.success("انجام شد")
    with cp2:
        prjs = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{p_sec}'", conn)
        if not prjs.empty:
            spn = st.selectbox("پروژه", prjs['name'].tolist())
            pid = prjs[prjs['name'] == spn]['id'].values[0]
            fn = st.text_input("پوشه جدید")
            if st.button("ساخت پوشه"):
                c.execute("INSERT INTO project_folders (proj_id, name) VALUES (?,?)", (pid, fn))
                conn.commit(); st.success("انجام شد")
            flds = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={pid}", conn)
            if not flds.empty:
                sfn = st.selectbox("پوشه مقصد", flds['name'].tolist())
                fid = flds[flds['name'] == sfn]['id'].values[0]
                up = st.file_uploader("فایل")
                if st.button("بارگذاری"):
                    if up:
                        c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_blob) VALUES (?,?,?,?)", (pid, fid, up.name, up.read()))
                        conn.commit(); st.success("انجام شد")

# --- تب داشبورد (نمایش خودکار و بدون خطا) ---
with tabs[0]:
    col_tree, col_view = st.columns([1, 2])
    active = None
    with col_tree:
        st.markdown('<div class="sidebar-tree">', unsafe_allow_html=True)
        ds = st.radio("بخش نمایش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True)
        provs = pd.read_sql("SELECT * FROM locations WHERE level='استان'", conn)
        for _, prov in provs.iterrows():
            with st.expander(f"📁 {prov['name']}"):
                active = {'level': 'prov', 'id': prov['id'], 'name': prov['name']}
                cnts = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND parent_id={prov['id']}", conn)
                for _, cnt in cnts.iterrows():
                    with st.expander(f"📂 {cnt['name']}"):
                        active = {'level': 'count', 'id': cnt['id'], 'name': cnt['name']}
                        vls = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id={cnt['id']}", conn)
                        for _, vl in vls.iterrows():
                            with st.expander(f"📍 {vl['name']}"):
                                active = {'level': 'vill', 'id': vl['id'], 'name': vl['name']}
                                pjs = pd.read_sql(f"SELECT * FROM projects WHERE loc_id={vl['id']} AND p_type='{ds}'", conn)
                                for _, pj in pjs.iterrows():
                                    if st.button(f"🏗️ {pj['name']}", key=f"btn_{pj['id']}"):
                                        st.session_state.last_pj = pj['id']
                                        st.session_state.last_pj_name = pj['name']
        st.markdown('</div>', unsafe_allow_html=True)

    with col_view:
        st.markdown('<div class="content-view">', unsafe_allow_html=True)
        if 'last_pj' in st.session_state:
            st.header(f"پروژه: {st.session_state.last_pj_name}")
            folders = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={st.session_state.last_pj}", conn)
            for _, fld in folders.iterrows():
                files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
                with st.expander(f"📁 {fld['name']} ({len(files)} فایل)"):
                    for _, fl in files.iterrows():
                        c1, c2 = st.columns([4, 1])
                        c1.text(fl['file_name'])
                        c2.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dl_{fl['id']}")
        elif active:
            st.header(active['name'])
            st.info("برای دیدن فایل‌ها، یک پروژه (🏗️) را از منو انتخاب کنید.")
        else:
            st.info("ابتدا مناطق و پروژه‌ها را تعریف کنید.")
        st.markdown('</div>', unsafe_allow_html=True)
