import streamlit as st
import pandas as pd
import sqlite3
import io

# اتصال به دیتابیس
conn = sqlite3.connect('civil_system_v11.db', check_same_thread=False)
c = conn.cursor()

# ایجاد جداول
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل اختصاصی RTL و چیدمان دو ستونه
st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #004a99; color: white; font-weight: bold; }
    .sidebar-tree { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 2px solid #004a99; height: 80vh; overflow-y: auto; }
    .content-view { background-color: #ffffff; padding: 20px; border: 1px solid #dee2e6; border-radius: 10px; min-height: 80vh; }
    .stat-box { background-color: #f1f3f5; padding: 10px; border-radius: 8px; margin-bottom: 10px; border-right: 5px solid #28a745; }
    </style>
    """, unsafe_allow_html=True)

if 'active_node' not in st.session_state:
    st.session_state.active_node = {'level': None, 'id': None, 'name': ''}

tabs = st.tabs(["📊 داشبورد", "🏗️ پروژه‌ها", "📍 تنظیمات مناطق"])

# --- تب تنظیمات مناطق (حذف و اضافه) ---
with tabs[2]:
    st.subheader("مدیریت مناطق")
    col1, col2 = st.columns(2)
    with col1:
        lvl = st.radio("سطح:", ["استان", "شهرستان", "شهر یا روستا"], horizontal=True)
        pid = 0
        if lvl != "استان":
            target_lvl = "استان" if lvl == "شهرستان" else "شهرستان"
            parents = pd.read_sql(f"SELECT * FROM locations WHERE level='{target_lvl}'", conn)
            if not parents.empty:
                sel_p = st.selectbox(f"انتخاب {target_lvl}", parents['name'].tolist(), key="loc_p")
                pid = parents[parents['name'] == sel_p]['id'].values[0]
        
        loc_name = st.text_input(f"نام {lvl}")
        if st.button(f"ثبت {lvl}"):
            c.execute("INSERT INTO locations (name, level, parent_id) VALUES (?,?,?)", (loc_name, lvl, int(pid)))
            conn.commit(); st.success("انجام شد")
    
    with col2:
        st.write("حذف مناطق:")
        all_locs = pd.read_sql("SELECT * FROM locations", conn)
        if not all_locs.empty:
            del_target = st.selectbox("انتخاب منطقه برای حذف", all_locs['name'].tolist())
            if st.button("حذف منطقه"):
                c.execute("DELETE FROM locations WHERE name=?", (del_target,))
                conn.commit(); st.success("انجام شد"); st.rerun()

# --- تب پروژه‌ها (ثبت، پوشه و آپلود) ---
with tabs[1]:
    st.subheader("مدیریت پروژه‌ها و فایل‌ها")
    p_section = st.radio("انتخاب بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True)
    
    c_p1, c_p2 = st.columns(2)
    with c_p1:
        st.markdown("### ثبت پروژه جدید")
        vills = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا'", conn)
        if not vills.empty:
            sel_v = st.selectbox("انتخاب شهر یا روستا", vills['name'].tolist(), key="proj_v")
            v_id = vills[vills['name'] == sel_v]['id'].values[0]
            new_p_name = st.text_input("نام پروژه")
            if st.button("ثبت پروژه"):
                c.execute("INSERT INTO projects (loc_id, name, p_type) VALUES (?,?,?)", (int(v_id), new_p_name, p_section))
                conn.commit(); st.success("انجام شد")
        else: st.info("ابتدا شهر یا روستا را در تب تنظیمات تعریف کنید.")

    with c_p2:
        st.markdown("### مدیریت فایل‌ها")
        projs = pd.read_sql(f"SELECT * FROM projects WHERE p_type='{p_section}'", conn)
        if not projs.empty:
            sel_p_name = st.selectbox("انتخاب پروژه", projs['name'].tolist())
            p_id = projs[projs['name'] == sel_p_name]['id'].values[0]
            
            st.write("---")
            new_f_name = st.text_input("نام پوشه جدید")
            if st.button("ایجاد پوشه"):
                c.execute("INSERT INTO project_folders (proj_id, name) VALUES (?,?)", (p_id, new_f_name))
                conn.commit(); st.success("انجام شد")
            
            st.write("---")
            folders = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={p_id}", conn)
            if not folders.empty:
                sel_f_name = st.selectbox("انتخاب پوشه مقصد", folders['name'].tolist())
                f_id = folders[folders['name'] == sel_f_name]['id'].values[0]
                up_file = st.file_uploader("انتخاب فایل")
                if st.button("بارگذاری و ذخیره"):
                    if up_file:
                        c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_blob) VALUES (?,?,?,?)",
                                  (p_id, f_id, up_file.name, up_file.read()))
                        conn.commit(); st.success("انجام شد")

# --- تب داشبورد (Explorer دو قسمتی) ---
with tabs[0]:
    col_tree, col_viewer = st.columns([1, 2])
    
    with col_tree:
        st.markdown('<div class="sidebar-tree">', unsafe_allow_html=True)
        st.subheader("بایگانی درختی")
        d_section = st.radio("بخش نمایش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="d_sec")
        
        provs = pd.read_sql("SELECT * FROM locations WHERE level='استان'", conn)
        for _, prov in provs.iterrows():
            with st.expander(f"📁 استان {prov['name']}"):
                if st.button(f"👁️ مشاهده استان {prov['name']}", key=f"v_p_{prov['id']}"):
                    st.session_state.active_node = {'level': 'prov', 'id': prov['id'], 'name': prov['name']}
                
                counts = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND parent_id={prov['id']}", conn)
                for _, count in counts.iterrows():
                    with st.expander(f"📂 {count['name']}"):
                        if st.button(f"👁️ مشاهده {count['name']}", key=f"v_c_{count['id']}"):
                            st.session_state.active_node = {'level': 'count', 'id': count['id'], 'name': count['name']}
                        
                        vills = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id={count['id']}", conn)
                        for _, vill in vills.iterrows():
                            with st.expander(f"📍 {vill['name']}"):
                                if st.button(f"👁️ مشاهده {vill['name']}", key=f"v_v_{vill['id']}"):
                                    st.session_state.active_node = {'level': 'vill', 'id': vill['id'], 'name': vill['name']}
                                
                                projs = pd.read_sql(f"SELECT * FROM projects WHERE loc_id={vill['id']} AND p_type='{d_section}'", conn)
                                for _, proj in projs.iterrows():
                                    with st.expander(f"🏗️ {proj['name']}"):
                                        if st.button(f"📂 پوشه‌های {proj['name']}", key=f"v_proj_{proj['id']}"):
                                            st.session_state.active_node = {'level': 'proj', 'id': proj['id'], 'name': proj['name']}
        st.markdown('</div>', unsafe_allow_html=True)

    with col_viewer:
        st.markdown('<div class="content-view">', unsafe_allow_html=True)
        node = st.session_state.active_node
        if node['id']:
            st.header(node['name'])
            
            if node['level'] == 'prov':
                f_count = pd.read_sql(f"SELECT COUNT(pf.id) as total FROM project_files pf JOIN projects p ON pf.proj_id = p.id JOIN locations v ON p.loc_id = v.id JOIN locations c ON v.parent_id = c.id WHERE c.parent_id = {node['id']}", conn)['total'].values[0]
                st.markdown(f'<div class="stat-box">کل فایل‌های استان: {f_count}</div>', unsafe_allow_html=True)
            
            elif node['level'] == 'vill':
                f_count = pd.read_sql(f"SELECT COUNT(pf.id) as total FROM project_files pf JOIN projects p ON pf.proj_id = p.id WHERE p.loc_id = {node['id']}", conn)['total'].values[0]
                st.markdown(f'<div class="stat-box">کل فایل‌های شهر یا روستا: {f_count}</div>', unsafe_allow_html=True)

            elif node['level'] == 'proj':
                folders = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={node['id']}", conn)
                for _, fld in folders.iterrows():
                    files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
                    with st.expander(f"📁 {fld['name']} ({len(files)} فایل)"):
                        for _, fl in files.iterrows():
                            c_n, c_d = st.columns([4, 1])
                            c_n.text(fl['file_name'])
                            c_d.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dl_{fl['id']}")
                
                if st.button("🗑️ حذف این پروژه"):
                    c.execute("DELETE FROM projects WHERE id=?", (node['id'],))
                    conn.commit(); st.success("انجام شد"); st.rerun()
        else:
            st.info("یک مورد را از درختواره سمت راست انتخاب کنید.")
        st.markdown('</div>', unsafe_allow_html=True)
