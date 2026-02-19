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

# ایجاد جداول پایه (تضمین وجود جداول)
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT, level TEXT, p_type TEXT, parent_id INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, company TEXT, contract_no TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_folders (id INTEGER PRIMARY KEY, proj_id INTEGER, name TEXT, p_type TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder_id INTEGER, file_name TEXT, file_blob BLOB)')
conn.commit()

st.set_page_config(page_title="مدیریت مهندسی شریفی", layout="wide")

# ۲. استایل و تراز راست‌چین
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"], .main, .block-container { 
        direction: rtl !important; 
        text-align: right !important; 
        font-family: 'Segoe UI', Tahoma, sans-serif;
    }
    h1, h2, h3, h4, h5, h6, label, .stMarkdown, p, span {
        text-align: right !important;
        direction: rtl !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        direction: rtl !important;
        display: flex !important;
        justify-content: flex-start !important;
    }
    div[data-testid="column"] { display: flex !important; align-items: center !important; }
    </style>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🛡️ داشبورد نظارتی", "👷 داشبورد شخصی", "📤 آپلود فایل", "📍 تنظیمات سیستم"])

# --- تابع داشبورد ---
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
                        c_name, c_btns = st.columns([4, 1.5])
                        with c_name: st.write(f"📄 {fl['file_name']}")
                        with c_btns:
                            a1, a2, a3 = st.columns([1, 1, 1])
                            if a1.button("🗑️", key=f"del_file_{fl['id']}"):
                                c.execute("DELETE FROM project_files WHERE id=?", (int(fl['id']),)); conn.commit(); st.rerun()
                            if a2.button("🔗", key=f"lnk_{fl['id']}"):
                                st.toast("لینک کپی شد"); st.code(f"data:file;base64,{base64.b64encode(fl['file_blob']).decode()[:10]}...")
                            a3.download_button("💾", fl['file_blob'], fl['file_name'], key=f"dw_{fl['id']}")

with tabs[0]: render_dash("نظارتی 🛡️")
with tabs[1]: render_dash("شخصی 👷")

# --- آپلود فایل ---
with tabs[2]:
    st.subheader("📤 آپلود مدارک")
    u_sec = st.radio("بخش:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="up_sec_main")
    all_p = pd.read_sql("SELECT * FROM projects WHERE p_type=?", conn, params=(u_sec,))
    if not all_p.empty:
        all_p['display_name'] = all_p.apply(lambda x: f"قرارداد: {x['contract_no']} - پروژه: {x['name']}", axis=1)
        c1, c2 = st.columns(2)
        with c1:
            s_p_display = st.selectbox("انتخاب پروژه:", all_p['display_name'].tolist())
            p_id = all_p[all_p['display_name']==s_p_display]['id'].values[0]
            fs = pd.read_sql("SELECT * FROM project_folders WHERE proj_id=?", conn, params=(int(p_id),))
            if not fs.empty:
                s_f = st.selectbox("پوشه:", fs['name'].tolist())
                f_id = fs[fs['name']==s_f]['id'].values[0]
                up_file = st.file_uploader("انتخاب فایل")
                if st.button("ثبت فایل") and up_file:
                    c.execute("INSERT INTO project_files (proj_id,folder_id,file_name,file_blob) VALUES (?,?,?,?)", (int(p_id), int(f_id), up_file.name, up_file.read()))
                    conn.commit(); st.success("انجام شد")

# --- تنظیمات سیستم ---
with tabs[3]:
    st.subheader("⚙️ تنظیمات سیستم")
    m_sec = st.radio("بخش تنظیمات:", ["نظارتی 🛡️", "شخصی 👷"], horizontal=True, key="m_setting")
    st.divider()
    
    cl, cr = st.columns(2)
    
    with cl:
        st.subheader("📍 مدیریت محل پروژه")
        mode_loc = st.radio("عملیات محل:", ["افزودن محل پروژه", "ویرایش محل پروژه"], horizontal=True)
        
        if mode_loc == "افزودن محل پروژه":
            ps = pd.read_sql("SELECT * FROM locations WHERE level='استان' AND p_type=?", conn, params=(m_sec,))
            s_p = st.selectbox("استان:", ["--- جدید ---"] + ps['name'].tolist(), key="add_p")
            if s_p == "--- جدید ---":
                np = st.text_input("نام استان جدید:")
                if st.button("ثبت استان"):
                    c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,0)", (np,"استان",m_sec)); conn.commit(); st.rerun()
            else:
                p_id = ps[ps['name']==s_p]['id'].values[0]
                cs = pd.read_sql("SELECT * FROM locations WHERE level='شهرستان' AND parent_id=?", conn, params=(int(p_id),))
                s_c = st.selectbox("شهرستان:", ["--- جدید ---"] + cs['name'].tolist(), key="add_c")
                if s_c == "--- جدید ---":
                    nc = st.text_input("نام شهرستان:")
                    if st.button("ثبت شهرستان"):
                        c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(nc,"شهرستان",m_sec,int(p_id))); conn.commit(); st.rerun()
                else:
                    c_id = cs[cs['name']==s_c]['id'].values[0]
                    vs = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND parent_id=?", conn, params=(int(c_id),))
                    s_v = st.selectbox("شهر/روستا:", ["--- جدید ---"] + vs['name'].tolist(), key="add_v")
                    if s_v == "--- جدید ---":
                        nv = st.text_input("نام محل:"); t = st.selectbox("نوع:",["شهر","روستا"])
                        if st.button("ثبت محل"):
                            c.execute("INSERT INTO locations (name,level,p_type,parent_id) VALUES (?,?,?,?)",(f"{t} {nv}","شهر یا روستا",m_sec,int(c_id))); conn.commit(); st.rerun()
        
        else: # ویرایش و حذف محل پروژه
            level_to_edit = st.selectbox("قصد ویرایش کدام سطح را دارید؟", ["استان", "شهرستان", "شهر یا روستا"])
            all_locs = pd.read_sql("SELECT * FROM locations WHERE level=? AND p_type=?", conn, params=(level_to_edit, m_sec))
            
            if not all_locs.empty:
                target_loc = st.selectbox(f"انتخاب {level_to_edit} برای عملیات:", all_locs['name'].tolist())
                new_loc_name = st.text_input("نام جدید:", value=target_loc)
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ اعمال تغییر نام", use_container_width=True):
                        c.execute("UPDATE locations SET name=? WHERE name=? AND level=? AND p_type=?", (new_loc_name, target_loc, level_to_edit, m_sec))
                        conn.commit(); st.success("نام ویرایش شد"); st.rerun()
                with c2:
                    with st.popover("🗑️ حذف این مورد"):
                        st.warning(f"آیا از حذف '{target_loc}' اطمینان دارید؟")
                        if st.button("بله، حذف شود"):
                            c.execute("DELETE FROM locations WHERE name=? AND level=? AND p_type=?", (target_loc, level_to_edit, m_sec))
                            conn.commit(); st.rerun()
            else:
                st.info("موردی برای نمایش وجود ندارد.")

    with cr:
        st.subheader("🏗️ مدیریت پروژه")
        mode_proj = st.radio("عملیات:", ["افزودن پروژه", "ویرایش پروژه"], horizontal=True)
        
        all_p_list = pd.read_sql("SELECT * FROM projects WHERE p_type=?", conn, params=(m_sec,))
        if not all_p_list.empty:
            all_p_list['display_name'] = all_p_list.apply(lambda x: f"قرارداد: {x['contract_no']} - پروژه: {x['name']}", axis=1)

        if mode_proj == "افزودن پروژه":
            v_list = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type=?", conn, params=(m_sec,))
            if not v_list.empty:
                sv = st.selectbox("انتخاب محل پروژه:", v_list['name'].tolist(), key="set_pj_loc")
                pn = st.text_input("نام پروژه:"); cp = st.text_input("شرکت:"); cn = st.text_input("شماره قرارداد:")
                if st.button("ثبت پروژه جدید"):
                    v_id = v_list[v_list['name']==sv]['id'].values[0]
                    c.execute("INSERT INTO projects (loc_id,name,company,contract_no,p_type) VALUES (?,?,?,?,?)",(int(v_id),pn,cp,cn,m_sec)); conn.commit(); st.rerun()
            else:
                st.warning("ابتدا یک محل در بخش مدیریت محل ثبت کنید.")
                
            st.divider()
            if not all_p_list.empty:
                st.write("### 📁 ایجاد پوشه")
                spj_display = st.selectbox("انتخاب پروژه:", all_p_list['display_name'].tolist(), key="set_fld_pj")
                nf = st.text_input("نام پوشه جدید:")
                if st.button("ایجاد پوشه"):
                    pid = all_p_list[all_p_list['display_name']==spj_display]['id'].values[0]
                    c.execute("INSERT INTO project_folders (proj_id,name,p_type) VALUES (?,?,?)",(int(pid),nf,m_sec)); conn.commit(); st.rerun()
        
        else: # حالت ویرایش و حذف پروژه
            if not all_p_list.empty:
                edit_p = st.selectbox("انتخاب پروژه:", all_p_list['display_name'].tolist())
                p_id = all_p_list[all_p_list['display_name']==edit_p]['id'].values[0]
                p_data = all_p_list[all_p_list['id']==p_id].iloc[0]
                
                with st.expander("🛠️ ویرایش و حذف مشخصات", expanded=True):
                    v_list = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type=?", conn, params=(m_sec,))
                    current_loc_name = v_list[v_list['id']==p_data['loc_id']]['name'].values[0] if p_data['loc_id'] in v_list['id'].values else v_list['name'].tolist()[0]
                    new_loc = st.selectbox("محل پروژه:", v_list['name'].tolist(), index=v_list['name'].tolist().index(current_loc_name))
                    new_pn = st.text_input("نام پروژه:", value=p_data['name'])
                    new_cp = st.text_input("شرکت:", value=p_data['company'])
                    new_cn = st.text_input("شماره قرارداد:", value=p_data['contract_no'])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("💾 بروزرسانی پروژه", use_container_width=True):
                            new_vid = v_list[v_list['name']==new_loc]['id'].values[0]
                            c.execute("UPDATE projects SET loc_id=?, name=?, company=?, contract_no=? WHERE id=?", 
                                      (int(new_vid), new_pn, new_cp, new_cn, int(p_id)))
                            conn.commit(); st.success("بروز شد"); st.rerun()
                    with col2:
                        with st.popover("🗑️ حذف کامل پروژه"):
                            st.error("هشدار: با حذف پروژه، تمام پوشه‌ها و فایل‌های آن نیز حذف می‌شوند.")
                            if st.button("تایید حذف نهایی"):
                                c.execute("DELETE FROM projects WHERE id=?", (int(p_id),))
                                c.execute("DELETE FROM project_folders WHERE proj_id=?", (int(p_id),))
                                c.execute("DELETE FROM project_files WHERE proj_id=?", (int(p_id),))
                                conn.commit(); st.rerun()

                with st.expander("📁 مدیریت پوشه‌ها"):
                    flds = pd.read_sql("SELECT * FROM project_folders WHERE proj_id=?", conn, params=(int(p_id),))
                    if not flds.empty:
                        target_fld = st.selectbox("انتخاب پوشه:", flds['name'].tolist())
                        fld_id = flds[flds['name']==target_fld]['id'].values[0]
                        new_fld_name = st.text_input("نام جدید پوشه:", value=target_fld)
                        
                        b1, b2 = st.columns(2)
                        with b1:
                            if st.button("✏️ تغییر نام پوشه", use_container_width=True):
                                c.execute("UPDATE project_folders SET name=? WHERE id=?", (new_fld_name, int(fld_id)))
                                conn.commit(); st.rerun()
                        with b2:
                            if st.button("🗑️ حذف پوشه", use_container_width=True):
                                c.execute("DELETE FROM project_folders WHERE id=?", (int(fld_id),))
                                c.execute("DELETE FROM project_files WHERE folder_id=?", (int(fld_id),))
                                conn.commit(); st.rerun()
                    else:
                        st.info("پوشه‌ای یافت نشد.")
