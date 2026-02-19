import streamlit as st
import pandas as pd
import sqlite3
import base64

# ۱. اتصال به دیتابیس
@st.cache_resource
def get_connection():
    conn = sqlite3.connect('civil_pro_final_v26.db', check_same_thread=False)
    return conn

conn = get_connection()
c = conn.cursor()

# ایجاد جداول پایه در صورت عدم وجود
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, p_type TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, company TEXT, contract_no TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# ۲. استایل راست‌چین
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"], .main, .block-container { direction: rtl !important; text-align: right !important; font-family: 'Segoe UI', Tahoma, sans-serif; }
    h1, h2, h3, h4, h5, h6, label, .stMarkdown, p, span { text-align: right !important; direction: rtl !important; }
    .stTabs [data-baseweb="tab-list"] { direction: rtl !important; display: flex !important; justify-content: flex-start !important; }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

# --- تابع رندر داشبورد (مشترک) ---
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
                                    btn_txt = f"📄 ق: {pj['contract_no']}" if pj['contract_no'] else f"🏗️ {pj['name']}"
                                    if st.button(btn_txt, key=f"pj_{label}_{pj['id']}", use_container_width=True):
                                        st.session_state[f'act_{label}'] = pj.to_dict()
    with col_view:
        if f'act_{label}' in st.session_state:
            pj = st.session_state[f'act_{label}']
            st.header(f"🏗️ {pj['name']}")
            st.info(f"🏢 شرکت: {pj['company']} | 📄 قرارداد: {pj['contract_no']}")
            flds = pd.read_sql("SELECT * FROM project_folders WHERE proj_id=?", conn, params=(int(pj['id']),))
            for _, fld in flds.iterrows():
                with st.expander(f"📁 {fld['name']}", expanded=True):
                    files = pd.read_sql("SELECT * FROM project_files WHERE folder_id=?", conn, params=(int(fld['id']),))
                    for _, fl in files.iterrows():
                        c_n, c_b = st.columns([4, 1.5])
                        with c_n: st.write(f"📄 {fl['file_name']}")
                        with c_b:
                            a1, a2, a3 = st.columns([1, 1, 1])
                            if a1.button("🗑️", key=f"del_f_{fl['id']}"):
                                c.execute("DELETE FROM project_files WHERE id=?", (int(fl['id']),)); conn.commit(); st.rerun()
                            if a2.button("🔗", key=f"lnk_{fl['id']}"):
                                st.toast("لینک کپی شد"); st.code(f"data:file;base64,{base64.b64encode(fl['file_blob']).decode()[:10]}...")
                            a3.download_button("💾", fl['file_blob'], fl['file_name'], key=f"dw_{fl['id']}")

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# --- تب تنظیمات (بخش اصلی حذف زنجیره‌ای) ---
with tabs[3]:
    st.subheader("⚙️ تنظیمات سیستم")
    m_sec = st.radio("بخش تنظیمات:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="m_set")
    st.divider()
    cl, cr = st.columns(2)
    
    with cl:
        st.subheader("📍 مدیریت محل پروژه")
        mode_loc = st.radio("عملیات:", ["افزودن جدید", "ویرایش نام", "حذف محل"], horizontal=True, key="l_mode")
        
        if mode_loc == "افزودن جدید":
            # ... (بخش افزودن مثل قبل)
            ps = pd.read_sql("SELECT * FROM locations WHERE level='استان' AND p_type=?", conn, params=(m_sec,))
            s_p = st.selectbox("استان:", ["--- جدید ---"] + ps['name'].tolist(), key="s_p_a")
            if s_p == "--- جدید ---":
                np = st.text_input("نام استان:")
                if st.button("ثبت"): c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,0)", (np,"استان",m_sec)); conn.commit(); st.rerun()
            else:
                p_id = ps[ps['name']==s_p]['id'].values[0]
                cs = pd.read_sql("SELECT * FROM locations WHERE level='شهرستان' AND parent_id=?", conn, params=(int(p_id),))
                s_c = st.selectbox("شهرستان:", ["--- جدید ---"] + cs['name'].tolist(), key="s_c_a")
                if s_c == "--- جدید ---":
                    nc = st.text_input("نام شهرستان:")
                    if st.button("ثبت"): c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(nc,"شهرستان",m_sec,int(p_id))); conn.commit(); st.rerun()
                else:
                    c_id = cs[cs['name']==s_c]['id'].values[0]
                    vs = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id=?", conn, params=(int(c_id),))
                    sv = st.selectbox("محل:", ["--- جدید ---"] + vs['name'].tolist(), key="s_v_a")
                    if sv == "--- جدید ---":
                        nv = st.text_input("نام:"); t = st.selectbox("نوع:",["شهر","روستا"])
                        if st.button("ثبت"): c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(f"{t} {nv}","شهر یا روستا",m_sec,int(c_id))); conn.commit(); st.rerun()

        elif mode_loc == "ویرایش نام":
            lvl = st.selectbox("سطح:", ["استان", "شهرستان", "شهر یا روستا"], key="lvl_e")
            all_l = pd.read_sql("SELECT * FROM locations WHERE level=? AND p_type=?", conn, params=(lvl, m_sec))
            if not all_l.empty:
                tg = st.selectbox("انتخاب:", all_l['name'].tolist(), key="tg_e")
                nn = st.text_input("نام جدید:", value=tg)
                if st.button("بروزرسانی نام"):
                    c.execute("UPDATE locations SET name=? WHERE name=? AND level=? AND p_type=?", (nn, tg, lvl, m_sec))
                    conn.commit(); st.rerun()

        else: # حذف زنجیره‌ای هوشمند
            lvl = st.selectbox("سطح حذف:", ["استان", "شهرستان", "شهر یا روستا"], key="lvl_d")
            all_l = pd.read_sql("SELECT * FROM locations WHERE level=? AND p_type=?", conn, params=(lvl, m_sec))
            if not all_l.empty:
                tg = st.selectbox("انتخاب برای حذف:", all_l['name'].tolist(), key="tg_d")
                tg_id = all_l[all_l['name']==tg]['id'].values[0]
                with st.popover("⚠️ تایید حذف نهایی", use_container_width=True):
                    st.error("با حذف این مورد، تمام زیرمجموعه‌ها و فایل‌ها پاک می‌شوند.")
                    if st.button("بله، حذف زنجیره‌ای انجام شود"):
                        if lvl == "استان":
                            c_ids = [r[0] for r in c.execute("SELECT id FROM locations WHERE parent_id=?", (int(tg_id),)).fetchall()]
                            for cid in c_ids:
                                v_ids = [r[0] for r in c.execute("SELECT id FROM locations WHERE parent_id=?", (int(cid),)).fetchall()]
                                for vid in v_ids:
                                    c.execute("DELETE FROM project_files WHERE proj_id IN (SELECT id FROM projects WHERE loc_id=?)", (int(vid),))
                                    c.execute("DELETE FROM project_folders WHERE proj_id IN (SELECT id FROM projects WHERE loc_id=?)", (int(vid),))
                                    c.execute("DELETE FROM projects WHERE loc_id=?", (int(vid),))
                                    c.execute("DELETE FROM locations WHERE id=?", (int(vid),))
                                c.execute("DELETE FROM locations WHERE id=?", (int(cid),))
                            c.execute("DELETE FROM locations WHERE id=?", (int(tg_id),))
                        elif lvl == "شهرستان":
                            v_ids = [r[0] for r in c.execute("SELECT id FROM locations WHERE parent_id=?", (int(tg_id),)).fetchall()]
                            for vid in v_ids:
                                c.execute("DELETE FROM project_files WHERE proj_id IN (SELECT id FROM projects WHERE loc_id=?)", (int(vid),))
                                c.execute("DELETE FROM project_folders WHERE proj_id IN (SELECT id FROM projects WHERE loc_id=?)", (int(vid),))
                                c.execute("DELETE FROM projects WHERE loc_id=?", (int(vid),))
                                c.execute("DELETE FROM locations WHERE id=?", (int(vid),))
                            c.execute("DELETE FROM locations WHERE id=?", (int(tg_id),))
                        else:
                            c.execute("DELETE FROM project_files WHERE proj_id IN (SELECT id FROM projects WHERE loc_id=?)", (int(tg_id),))
                            c.execute("DELETE FROM project_folders WHERE proj_id IN (SELECT id FROM projects WHERE loc_id=?)", (int(tg_id),))
                            c.execute("DELETE FROM projects WHERE loc_id=?", (int(tg_id),))
                            c.execute("DELETE FROM locations WHERE id=?", (int(tg_id),))
                        conn.commit(); st.rerun()

    with cr:
        st.subheader("🏗️ مدیریت پروژه")
        # ... (بخش مدیریت پروژه مثل قبل)
        mode_pj = st.radio("عملیات:", ["افزودن پروژه", "ویرایش پروژه"], horizontal=True, key="p_mode")
        all_p = pd.read_sql("SELECT * FROM projects WHERE p_type=?", conn, params=(m_sec,))
        if mode_pj == "افزودن پروژه":
            v_list = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type=?", conn, params=(m_sec,))
            if not v_list.empty:
                sv = st.selectbox("محل پروژه:", v_list['name'].tolist(), key="sv_p")
                pn = st.text_input("نام پروژه:"); cp = st.text_input("شرکت:"); cn = st.text_input("قرارداد:")
                if st.button("ثبت پروژه"):
                    v_id = v_list[v_list['name']==sv]['id'].values[0]
                    c.execute("INSERT INTO projects (loc_id,name,company,contract_no,p_type) VALUES (?,?,?,?,?)",(int(v_id),pn,cp,cn,m_sec)); conn.commit(); st.rerun()
