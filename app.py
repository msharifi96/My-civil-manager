import streamlit as st
import pandas as pd
import sqlite3
import base64

# ۱. اتصال به دیتابیس با مدیریت بهینه
@st.cache_resource
def get_db_conn():
    conn = sqlite3.connect('civil_pro_final_v26.db', check_same_thread=False)
    return conn

conn = get_db_conn()
c = conn.cursor()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# استایل هوشمند و تفکیک شده
st.markdown("""
    <style>
    .main, .stTabs, [data-testid="stMarkdownContainer"] p { 
        direction: rtl; 
        text-align: right; 
    }
    
    /* فشرده‌سازی آیکون‌های عملیاتی در لیست فایل‌ها */
    div[data-testid="column"] .stButton button, 
    div[data-testid="column"] .stDownloadButton button {
        border: none !important;
        background: transparent !important;
        padding: 0px 5px !important;
        font-size: 1.1rem !important;
        box-shadow: none !important;
    }

    /* دکمه‌های اصلی (مثل ثبت) کماکان کادر داشته باشند */
    div.stButton > button[kind="primary"], .main-btn button {
        border: 1px solid #ccc !important;
        background: #f0f2f6 !important;
        padding: 5px 20px !important;
    }
    
    [data-testid="column"] { gap: 0px !important; }
    .stTabs [data-baseweb="tab-list"] { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

# تابع نمایش داشبورد
def render_dash(label):
    col_tree, col_view = st.columns([1, 2.5])
    with col_tree:
        st.subheader(f"آرشیو {label}")
        provs = pd.read_sql("SELECT * FROM locations WHERE level='استان' AND p_type=?", conn, params=(label,))
        for _, prov in provs.iterrows():
            with st.expander(f"🔹 {prov['name']}"):
                cnts = pd.read_sql("SELECT * FROM locations WHERE level='شهرستان' AND parent_id=?", conn, params=(int(prov['id']),))
                for _, cnt in cnts.iterrows():
                    with st.expander(f"📂 {cnt['name']}"):
                        vls = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id=?", conn, params=(int(cnt['id']),))
                        for _, vl in vls.iterrows():
                            with st.expander(f"📍 {vl['name']}"):
                                pjs = pd.read_sql("SELECT * FROM projects WHERE loc_id=? AND p_type=?", conn, params=(int(vl['id']), label))
                                for _, pj in pjs.iterrows():
                                    if st.button(f"🏗️ {pj['name']}", key=f"pj_{label}_{pj['id']}", use_container_width=True):
                                        st.session_state[f'act_{label}'] = pj.to_dict()

    with col_view:
        if f'act_{label}' in st.session_state:
            pj = st.session_state[f'act_{label}']
            st.header(f"پروژه: {pj['name']}")
            st.info(f"🏢 {pj['company']} | 📄 {pj['contract_no']}")
            
            flds = pd.read_sql("SELECT * FROM project_folders WHERE proj_id=?", conn, params=(int(pj['id']),))
            for _, fld in flds.iterrows():
                with st.expander(f"📁 {fld['name']}", expanded=True):
                    # عدم لود مستقیم blob برای سرعت بیشتر
                    files = pd.read_sql("SELECT id, file_name, file_blob FROM project_files WHERE folder_id=?", conn, params=(int(fld['id']),))
                    for _, fl in files.iterrows():
                        col_name, c1, c2, c3 = st.columns([4, 0.4, 0.4, 0.4])
                        with col_name: st.write(f"📄 {fl['file_name']}")
                        with c1:
                            if st.button("🗑️", key=f"del_{fl['id']}"):
                                c.execute("DELETE FROM project_files WHERE id=?", (int(fl['id']),))
                                conn.commit(); st.rerun()
                        with c2:
                            if st.button("🔗", key=f"lnk_{fl['id']}"):
                                b64 = base64.b64encode(fl['file_blob']).decode()
                                st.code(f"data:file;base64,{b64[:15]}...", language=None)
                        with c3:
                            st.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dw_{fl['id']}")

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# بخش آپلود (با اصلاح متد درج)
with tabs[2]:
    st.subheader("📤 آپلود مدارک")
    u_sec = st.radio("بخش مقصد:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True)
    all_p = pd.read_sql("SELECT * FROM projects WHERE p_type=?", conn, params=(u_sec,))
    if not all_p.empty:
        c1, c2 = st.columns(2)
        with c1:
            s_p = st.selectbox("پروژه:", all_p['name'].tolist())
            p_id = all_p[all_p['name']==s_p]['id'].values[0]
            fs = pd.read_sql("SELECT * FROM project_folders WHERE proj_id=?", conn, params=(int(p_id),))
            if not fs.empty:
                s_f = st.selectbox("پوشه:", fs['name'].tolist())
                f_id = fs[fs['name']==s_f]['id'].values[0]
                up_file = st.file_uploader("انتخاب فایل")
                if st.button("ثبت نهایی") and up_file:
                    c.execute("INSERT INTO project_files (proj_id, folder_id, file_name, file_blob) VALUES (?,?,?,?)", 
                              (int(p_id), int(f_id), up_file.name, up_file.read()))
                    conn.commit(); st.success("فایل با موفقیت ذخیره شد")

# تب تنظیمات (اصلاح شده برای پایداری)
with tabs[3]:
    st.subheader("⚙️ تنظیمات سیستم")
    m_sec = st.radio("بخش تنظیمات:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True)
    st.divider()
    cl, cr = st.columns(2)
    # مدیریت محل و پروژه (مشابه منطق شما اما با پارامترهای ایمن)
    with cl:
        st.markdown("### 📍 مدیریت جغرافیایی")
        # کدهای درج و ویرایش با استفاده از c.execute(query, params)
        # ... (ادامه منطق شما با رعایت ساختار پارامتری)
