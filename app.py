import streamlit as st
import pandas as pd
import sqlite3
import time

# اتصال به دیتابیس
conn = sqlite3.connect('civil_pro_v14.db', check_same_thread=False)
c = conn.cursor()

# ایجاد جداول
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

# تابع پیغام موقت
def show_success_and_clear():
    msg = st.empty()
    msg.success("انجام شد")
    time.sleep(1.5)
    msg.empty()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل RTL
st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #004a99; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

tab_dash, tab_proj, tab_loc = st.tabs(["📊 داشبورد", "🏗️ پروژه‌ها", "📍 تنظیمات مناطق"])

# --- تب تنظیمات مناطق ---
with tab_loc:
    st.subheader("مدیریت مناطق")
    col1, col2 = st.columns(2)
    with col1:
        lvl = st.radio("سطح جدید:", ["استان", "شهرستان", "شهر یا روستا"], horizontal=True, key="reg_lvl")
        pid = 0
        if lvl != "استان":
            t_lvl = "استان" if lvl == "شهرستان" else "شهرستان"
            parents = pd.read_sql(f"SELECT * FROM locations WHERE level='{t_lvl}'", conn)
            if not parents.empty:
                sel_p = st.selectbox(f"انتخاب {t_lvl}", parents['name'].tolist(), key="reg_parent")
                pid = parents[parents['name'] == sel_p]['id'].values[0]
        l_name = st.text_input(f"نام {lvl}", key="reg_name")
        if st.button("ثبت منطقه", key="reg_btn"):
            c.execute("INSERT INTO locations (name, level, parent_id) VALUES (?,?,?)", (l_name, lvl, int(pid)))
            conn.commit()
            show_success_and_clear()
            st.rerun()

    with col2:
        all_l = pd.read_sql("SELECT * FROM locations", conn)
        if not all_l.empty:
            del_n = st.selectbox("حذف منطقه", all_l['name'].tolist(), key="del_loc_sel")
            if st.button("حذف نهایی منطقه", key="del_loc_btn"):
                c.execute("DELETE FROM locations WHERE name=?", (del_n,))
                conn.commit()
                show_success_and_clear()
                st.rerun()

# --- تب پروژه‌ها ---
with tab_proj:
    st.subheader("مدیریت پروژه‌ها و فایل‌ها")
    p_sec = st.radio("بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="proj_sec")
    cp1, cp2 = st.columns(2)
    with cp1:
        vills = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا'", conn)
        if not vills.empty:
            sv = st.selectbox("انتخاب شهر یا روستا", vills['name'].tolist(), key="proj_vill_sel")
            vid = vills[vills['name'] == sv]['id'].values[0]
            pn = st.text_input("نام پروژه", key="proj_name_input")
            if st.button("ثبت پروژه", key="proj_save_btn"):
                c.execute("INSERT INTO projects (loc_id, name, p_type) VALUES (?,?,?)", (int(vid), pn, p_sec))
                conn.commit()
                show_success_and_clear()
    
    with cp2:
        prjs = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{p_sec}'", conn)
        if not prjs.empty:
            spn = st.selectbox("انتخاب پروژه", prjs['name'].tolist(), key="file_proj_sel")
            pid = prjs[prjs['name'] == spn]['id'].values[0]
            fn = st.text_input("نام پوشه جدید", key="folder_name_input")
            if st.button("ساخت پوشه", key="folder_save_btn"):
                c.execute("INSERT INTO project_folders (proj_id, name) VALUES (?,?)", (pid, fn))
                conn.commit()
                show_success_and_clear()
            
            flds = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={pid}", conn)
            if not flds.empty:
                sfn = st.selectbox("انتخاب پوشه مقصد", flds['name'].tolist(), key="file_fld_sel")
                fid = flds[flds['name'] == sfn]['id'].values[0]
                up = st.file_uploader("انتخاب فایل", key="file_up_widget")
                if st.button("بارگذاری فایل", key="file_save_btn"):
                    if up:
                        c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_blob) VALUES (?,?,?,?)", (pid, fid, up.name, up.read()))
                        conn.commit()
                        show_success_and_clear()

# --- تب داشبورد ---
with tab_dash:
    col_tree, col_view = st.columns([1, 2])
    with col_tree:
        st.subheader("بایگانی")
        ds = st.radio("بخش نمایش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="dash_sec_radio")
        provs = pd.read_sql("SELECT * FROM locations WHERE level='استان'", conn)
        for _, prov in provs.iterrows():
            with st.expander(f"📁 {prov['name']}"):
                cnts = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND parent_id={prov['id']}", conn)
                for _, cnt in cnts.iterrows():
                    with st.expander(f"📂 {cnt['name']}"):
                        vls = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id={cnt['id']}", conn)
                        for _, vl in vls.iterrows():
                            with st.expander(f"📍 {vl['name']}"):
                                pjs = pd.read_sql(f"SELECT * FROM projects WHERE loc_id={vl['id']} AND p_type='{ds}'", conn)
                                for _, pj in pjs.iterrows():
                                    if st.button(f"🏗️ {pj['name']}", key=f"btn_pj_{pj['id']}"):
                                        st.session_state.active_pj = pj['id']
                                        st.session_state.active_pj_name = pj['name']

    with col_view:
        if 'active_pj' in st.session_state:
            st.header(f"پروژه: {st.session_state.active_pj_name}")
            folders = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={st.session_state.active_pj}", conn)
            for _, fld in folders.iterrows():
                files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
                with st.expander(f"📁 {fld['name']} ({len(files)} فایل)"):
                    for _, fl in files.iterrows():
                        c1, c2 = st.columns([4, 1])
                        c1.text(fl['file_name'])
                        c2.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dl_btn_{fl['id']}")
            
            if st.button("🗑️ حذف کامل این پروژه", key="del_pj_final"):
                c.execute("DELETE FROM projects WHERE id=?", (st.session_state.active_pj,))
                conn.commit()
                del st.session_state.active_pj
                show_success_and_clear()
                st.rerun()
        else:
            st.info("یک پروژه را از منوی سمت راست انتخاب کنید.")
