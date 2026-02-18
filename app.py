import streamlit as st
import pandas as pd
import sqlite3
import io

# اتصال به دیتابیس
conn = sqlite3.connect('civil_smart_v7.db', check_same_thread=False)
c = conn.cursor()

# ایجاد جداول
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS folders (id INTEGER PRIMARY KEY, name TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

# تنظیمات RTL و ظاهر مهندسی
st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")
st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #004a99; color: white; font-weight: bold; }
    .stExpander { border: 1px solid #004a99; border-radius: 8px; margin-bottom: 5px; background-color: #f8f9fa; }
    div[data-testid="stExpander"] p { font-size: 16px; }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["📊 داشبورد و بایگانی", "📤 ثبت پروژه و فایل", "📍 تنظیمات سیستم"])

# --- تب تنظیمات (تعریف مناطق و پوشه‌ها) ---
with tabs[2]:
    col_reg, col_fld = st.columns(2)
    with col_reg:
        st.subheader("📍 مدیریت مناطق")
        level = st.radio("سطح تعریف منطقه:", ["استان", "شهرستان", "شهر یا روستا"], horizontal=True)
        parent_id = 0
        if level != "استان":
            p_level = "استان" if level == "شهرستان" else "شهرستان"
            parents = pd.read_sql(f"SELECT * FROM locations WHERE level='{p_level}'", conn)
            if not parents.empty:
                sel_p = st.selectbox(f"انتخاب {p_level} مادر", parents['name'].tolist())
                parent_id = parents[parents['name'] == sel_p]['id'].values[0]
        
        loc_n = st.text_input(f"نام {level}")
        if st.button(f"✅ ثبت {level}"):
            if loc_n:
                c.execute("INSERT INTO locations (name, level, parent_id) VALUES (?,?,?)", (loc_n, level, int(parent_id)))
                conn.commit()
                st.rerun()

    with col_fld:
        st.subheader("📁 مدیریت پوشه‌های دلخواه")
        new_folder = st.text_input("نام پوشه جدید (مثلاً: ابلاغیه‌ها)")
        if st.button("➕ افزودن پوشه"):
            if new_folder:
                c.execute("INSERT INTO folders (name) VALUES (?)", (new_folder,))
                conn.commit()
                st.rerun()
        
        st.write("---")
        all_f = pd.read_sql("SELECT * FROM folders", conn)
        for _, f_row in all_f.iterrows():
            c1, c2 = st.columns([4, 1])
            c1.text(f"📂 {f_row['name']}")
            if c2.button("🗑️", key=f"df_{f_row['id']}"):
                c.execute("DELETE FROM folders WHERE id=?", (f_row['id'],))
                conn.commit(); st.rerun()

# --- تب ثبت پروژه و آپلود ---
with tabs[1]:
    st.subheader("📝 ورود اطلاعات پروژه")
    provs = pd.read_sql("SELECT * FROM locations WHERE level='استان'", conn)
    if not provs.empty:
        c1, c2, c3 = st.columns(3)
        with c1:
            s_prov = st.selectbox("استان", provs['name'].tolist())
            p_id = provs[provs['name'] == s_prov]['id'].values[0]
            counts = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND parent_id={p_id}", conn)
        with c2:
            if not counts.empty:
                s_count = st.selectbox("شهرستان", counts['name'].tolist())
                cnt_id = counts[counts['name'] == s_count]['id'].values[0]
                vills = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id={cnt_id}", conn)
            else: st.info("شهرستان تعریف نشده"); vills = pd.DataFrame()
        with c3:
            if not vills.empty:
                s_vill = st.selectbox("شهر یا روستا", vills['name'].tolist())
                final_loc_id = vills[vills['name'] == s_vill]['id'].values[0]
            else: final_loc_id = None

        if final_loc_id:
            st.divider()
            ca, cb = st.columns(2)
            ptype = ca.radio("نوع پروژه را مشخص کنید:", ["نظارتی 🛡️", "پیمانکاری 👷"])
            pname = cb.text_input("نام پروژه")
            
            st.write("---")
            f_list = pd.read_sql("SELECT * FROM folders", conn)
            if not f_list.empty:
                col_f1, col_f2 = st.columns([1, 2])
                target_f = col_f1.selectbox("انتخاب پوشه برای فایل", f_list['name'].tolist())
                fid = f_list[f_list['name'] == target_f]['id'].values[0]
                up_file = col_f2.file_uploader("انتخاب فایل (هر فرمتی)")
                
                if st.button("🚀 ثبت نهایی پروژه و فایل"):
                    if pname and up_file:
                        c.execute("INSERT OR IGNORE INTO projects (loc_id, name, p_type) VALUES (?,?,?)", (int(final_loc_id), pname, ptype))
                        c.execute("SELECT id FROM projects WHERE name=?", (pname,))
                        proj_id = c.fetchone()[0]
                        c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_blob) VALUES (?,?,?,?)",
                                  (int(proj_id), int(fid), up_file.name, up_file.read()))
                        conn.commit(); st.success("پروژه با موفقیت ثبت و بایگانی شد.")
            else: st.warning("ابتدا در تب تنظیمات، پوشه‌های مورد نیازتان را بسازید.")
    else: st.warning("ابتدا در تب تنظیمات، استان و شهرستان را تعریف کنید.")

# --- تب داشبورد درختی ---
with tabs[0]:
    st.subheader("📂 آرشیو پروژه‌ها")
    type_filter = st.radio("انتخاب بخش:", ["نظارتی 🛡️", "پیمانکاری 👷"], horizontal=True)
    
    query = f"""
    SELECT p.*, l.name as city_or_village, l.parent_id as cnt_id 
    FROM projects p 
    JOIN locations l ON p.loc_id = l.id 
    WHERE p.p_type='{type_filter}'
    """
    all_p = pd.read_sql(query, conn)
    
    if not all_p.empty:
        for _, p_row in all_p.iterrows():
            # استخراج نام شهرستان و استان برای نمایش درختی
            cnt_data = pd.read_sql(f"SELECT name, parent_id FROM locations WHERE id={p_row['cnt_id']}", conn)
            cnt_name = cnt_data['name'].values[0]
            prv_name = pd.read_sql(f"SELECT name FROM locations WHERE id={cnt_data['parent_id'].values[0]}", conn)['name'].values[0]
            
            with st.expander(f"📍 {prv_name} > {cnt_name} > {p_row['city_or_village']} | 🏗️ {p_row['name']}"):
                col_m, col_btns = st.columns([5, 1])
                with col_m:
                    files = pd.read_sql(f"""
                        SELECT pf.*, f.name as folder_name 
                        FROM project_files pf 
                        JOIN folders f ON pf.folder_id = f.id 
                        WHERE pf.proj_id={p_row['id']}
                    """, conn)
                    
                    if not files.empty:
                        for fld in files['folder_name'].unique():
                            st.markdown(f"📁 **{fld}**")
                            sub_f = files[files['folder_name'] == fld]
                            for _, f in sub_f.iterrows():
                                c_name, c_dl = st.columns([4, 1])
                                c_name.text(f"📄 {f['file_name']}")
                                c_dl.download_button("📥 دانلود", f['file_blob'], f['file_name'], key=f"dl_{f['id']}")
                    else:
                        st.write("هنوز فایلی در این پروژه بارگذاری نشده است.")
                
                with col_btns:
                    if st.button("🗑️ حذف کل پروژه", key=f"delp_{p_row['id']}"):
                        c.execute("DELETE FROM projects WHERE id=?", (p_row['id'],))
                        c.execute("DELETE FROM project_files WHERE proj_id=?", (p_row['id'],))
                        conn.commit(); st.rerun()
    else:
        st.info("در این بخش هنوز پروژه‌ای ثبت نشده است.")
