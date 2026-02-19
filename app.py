import streamlit as st
import pandas as pd
import sqlite3

# اتصال به دیتابیس
conn = sqlite3.connect('civil_system_v12.db', check_same_thread=False)
c = conn.cursor()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل برای حذف فضاهای خالی اضافی
st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3 { direction: rtl; text-align: right; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #004a99; color: white; font-weight: bold; }
    .sidebar-tree { background-color: #f8f9fa; padding: 10px; border-radius: 10px; border-left: 3px solid #004a99; min-height: 80vh; }
    .content-view { background-color: #ffffff; padding: 15px; border: 1px solid #dee2e6; border-radius: 10px; min-height: 80vh; }
    .stat-box { background-color: #f1f3f5; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-right: 5px solid #28a745; font-weight: bold; color: #004a99; }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["📊 داشبورد", "🏗️ پروژه‌ها", "📍 تنظیمات مناطق"])

# --- تب داشبورد (با اصلاح فضای خالی) ---
with tabs[0]:
    col_tree, col_viewer = st.columns([1, 2])
    
    with col_tree:
        st.markdown('<div class="sidebar-tree">', unsafe_allow_html=True)
        st.subheader("بایگانی درختی")
        d_section = st.radio("بخش نمایش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True)
        
        # متغیری برای ذخیره آخرین وضعیت باز شده
        current_selection = None
        
        provs = pd.read_sql("SELECT * FROM locations WHERE level='استان'", conn)
        for _, prov in provs.iterrows():
            with st.expander(f"📁 استان {prov['name']}"):
                current_selection = {'level': 'prov', 'id': prov['id'], 'name': prov['name']}
                counts = pd.read_sql(f"SELECT * FROM locations WHERE level='شهرستان' AND parent_id={prov['id']}", conn)
                for _, count in counts.iterrows():
                    with st.expander(f"📂 {count['name']}"):
                        current_selection = {'level': 'count', 'id': count['id'], 'name': count['name']}
                        vills = pd.read_sql(f"SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id={count['id']}", conn)
                        for _, vill in vills.iterrows():
                            with st.expander(f"📍 {vill['name']}"):
                                current_selection = {'level': 'vill', 'id': vill['id'], 'name': vill['name']}
                                projs = pd.read_sql(f"SELECT * FROM projects WHERE loc_id={vill['id']} AND p_type='{d_section}'", conn)
                                for _, proj in projs.iterrows():
                                    with st.expander(f"🏗️ {proj['name']}"):
                                        current_selection = {'level': 'proj', 'id': proj['id'], 'name': proj['name']}
        st.markdown('</div>', unsafe_allow_html=True)

    with col_viewer:
        st.markdown('<div class="content-view">', unsafe_allow_html=True)
        if current_selection:
            st.header(current_selection['name'])
            # منطق نمایش آمار و فایل‌ها (همان کدهای قبلی)
            if current_selection['level'] == 'prov':
                f_count = pd.read_sql(f"SELECT COUNT(pf.id) as total FROM project_files pf JOIN projects p ON pf.proj_id = p.id JOIN locations v ON p.loc_id = v.id JOIN locations c ON v.parent_id = c.id WHERE c.parent_id = {current_selection['id']}", conn)['total'].values[0]
                st.markdown(f'<div class="stat-box">📊 آمار کل استان: {f_count} فایل</div>', unsafe_allow_html=True)
            elif current_selection['level'] == 'proj':
                folders = pd.read_sql(f"SELECT * FROM project_folders WHERE proj_id={current_selection['id']}", conn)
                for _, fld in folders.iterrows():
                    files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
                    with st.expander(f"📁 {fld['name']} ({len(files)} فایل)"):
                        for _, fl in files.iterrows():
                            cn, cd = st.columns([4, 1])
                            cn.text(fl['file_name'])
                            cd.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dl_{fl['id']}")
        else:
            # نمایش پیش‌فرض وقتی هنوز چیزی باز نشده
            st.header("خلاصه وضعیت بایگانی")
            total_f = pd.read_sql("SELECT COUNT(*) as total FROM project_files", conn)['total'].values[0]
            st.markdown(f'<div class="stat-box">تعداد کل فایل‌های ثبت شده در سیستم: {total_f}</div>', unsafe_allow_html=True)
            st.info("برای مشاهده جزئیات، یکی از استان‌ها را از منوی سمت راست باز کنید.")
        st.markdown('</div>', unsafe_allow_html=True)
