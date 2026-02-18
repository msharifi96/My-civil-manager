import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

# اتصال به دیتابیس (ذخیره دائمی - طبق دستور کاربر)
conn = sqlite3.connect('civil_pro_ultra_v5.db', check_same_thread=False)
c = conn.cursor()

# ایجاد جداول مورد نیاز
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, name TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, p_type TEXT, progress INTEGER DEFAULT 0, expiry_date TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS project_files (id INTEGER PRIMARY KEY, proj_id INTEGER, folder TEXT, file_name TEXT, file_blob BLOB)')
c.execute('CREATE TABLE IF NOT EXISTS finances (id INTEGER PRIMARY KEY, proj_id INTEGER, type TEXT, amount REAL, description TEXT, date TEXT, is_check BOOLEAN, due_date TEXT)')
conn.commit()

# تنظیمات صفحه و استایل RTL
st.set_page_config(page_title="پنل مهندسی شریفی", layout="wide")
st.markdown("""
    <style>
    .main, .stTabs, .stSelectbox, .stTextInput, .stButton, .stMarkdown, p, h1, h2, h3, .stSlider {
        direction: rtl; text-align: right;
    }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #004a99; color: white; font-weight: bold; }
    .stExpander { border: 1px solid #004a99; border-radius: 10px; background-color: #f8f9fa; }
    .status-card { padding: 20px; border-radius: 10px; background-color: #e9ecef; border-right: 5px solid #004a99; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 سامانه جامع مدیریت مهندسی و مالی")

tabs = st.tabs(["📊 داشبورد و آرشیو", "📤 ثبت مستندات", "💰 مدیریت مالی و چک‌ها", "📍 تنظیمات"])

# --- تب تنظیمات و مناطق ---
with tabs[3]:
    st.subheader("📍 مدیریت مناطق و خروجی داده‌ها")
    new_loc = st.text_input("نام شهر یا روستای جدید")
    if st.button("ثبت مکان"):
        if new_loc:
            c.execute("INSERT INTO locations (name) VALUES (?)", (new_loc,))
            conn.commit()
            st.success(f"'{new_loc}' با موفقیت ثبت شد.")
            st.rerun()
    
    st.divider()
    if st.button("📥 خروجی کل داده‌ها (Excel)"):
        all_data = pd.read_sql("SELECT p.name, p.p_type, p.progress, l.name as location FROM projects p JOIN locations l ON p.loc_id = l.id", conn)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            all_data.to_excel(writer, sheet_name='Projects', index=False)
        st.download_button(label="📥 دانلود فایل اکسل پروژه‌ها", data=buffer, file_name="Engineering_Report.xlsx")

# --- تب ثبت و آپلود ---
with tabs[1]:
    st.subheader("📝 تعریف پروژه و بارگذاری فایل")
    locs = pd.read_sql("SELECT * FROM locations", conn)
    if not locs.empty:
        c1, c2 = st.columns(2)
        with c1:
            p_type = st.radio("نوع پروژه:", ["نظارتی 🛡️", "پیمانکاری 👷"])
            selected_city = st.selectbox("مکان پروژه", locs['name'].tolist())
            c_id = locs[locs['name'] == selected_city]['id'].values[0]
        with c2:
            p_name = st.text_input("نام پروژه (مثلاً: پروژه جناب محمدی)")
            p_expiry = st.date_input("تاریخ اتمام قرارداد/پروانه")
        
        st.divider()
        folders = ["گزارش‌ها/صورت‌وضعیت", "دستور کار/قرارداد", "نقشه‌ها", "فاکتور/مکاتبات", "سایر"]
        c3, c4 = st.columns([1, 2])
        with c3:
            fld_sel = st.selectbox("📁 پوشه مقصد", folders)
        with c4:
            up_file = st.file_uploader("📎 انتخاب فایل (تمامی فرمت‌ها)")
            
        if st.button("🚀 ذخیره و ثبت نهایی"):
            if p_name and up_file:
                c.execute("INSERT OR IGNORE INTO projects (loc_id, name, p_type, expiry_date) VALUES (?,?,?,?)", 
                          (int(c_id), p_name, p_type, str(p_expiry)))
                c.execute("SELECT id FROM projects WHERE name=?", (p_name,))
                p_id = c.fetchone()[0]
                c.execute("INSERT INTO project_files (proj_id, folder, file_name, file_blob) VALUES (?,?,?,?)",
                          (int(p_id), fld_sel, up_file.name, up_file.read()))
                conn.commit()
                st.success("اطلاعات با موفقیت ذخیره شد.")
    else:
        st.warning("ابتدا یک منطقه در تب تنظیمات تعریف کنید.")

# --- تب مدیریت مالی ---
with tabs[2]:
    st.subheader("💰 حسابداری پروژه و مدیریت چک‌ها")
    projs = pd.read_sql("SELECT id, name FROM projects", conn)
    if not projs.empty:
        c1, c2, c3 = st.columns(3)
        with c1:
            sel_p_fin = st.selectbox("انتخاب پروژه برای ثبت مالی", projs['name'].tolist(), key="fin_p")
            p_id_fin = projs[projs['name'] == sel_p_fin]['id'].values[0]
            f_type = st.selectbox("نوع تراکنش", ["دریافتی (درآمد)", "پرداختی (هزینه)"])
        with c2:
            amount = st.number_input("مبلغ (ریال)", min_value=0)
            is_check = st.checkbox("این مبلغ به صورت چک است")
        with c3:
            f_desc = st.text_input("بابت (توضیحات)")
            due_date = st.date_input("تاریخ سررسید (اگر چک است)")
            
        if st.button("💵 ثبت سند مالی"):
            c.execute("INSERT INTO finances (proj_id, type, amount, description, date, is_check, due_date) VALUES (?,?,?,?,?,?,?)",
                      (int(p_id_fin), f_type, amount, f_desc, str(datetime.now().date()), is_check, str(due_date)))
            conn.commit()
            st.success("سند مالی ثبت شد.")
            
        st.divider()
        st.write("📋 لیست چک‌های نزدیک به سررسید:")
        checks = pd.read_sql(f"SELECT * FROM finances WHERE is_check=1", conn)
        if not checks.empty:
            st.dataframe(checks[['description', 'amount', 'due_date']])
    else:
        st.info("پروژه‌ای برای ثبت مالی یافت نشد.")

# --- تب داشبورد و آرشیو ---
with tabs[0]:
    search_q = st.text_input("🔍 جستجوی سریع پروژه...")
    query = "SELECT p.*, l.name as loc_name FROM projects p JOIN locations l ON p.loc_id = l.id"
    if search_q:
        query += f" WHERE p.name LIKE '%{search_q}%'"
    
    all_p = pd.read_sql(query, conn)
    
    for _, p_row in all_p.iterrows():
        with st.expander(f"📌 {p_row['name']} ({p_row['p_type']}) - {p_row['loc_name']}"):
            col_a, col_b = st.columns([2, 1])
            with col_a:
                # مدیریت پیشرفت فیزیکی
                new_prog = st.slider("درصد پیشرفت فیزیکی", 0, 100, int(p_row['progress']), key=f"prog_{p_row['id']}")
                if new_prog != p_row['progress']:
                    c.execute("UPDATE projects SET progress=? WHERE id=?", (new_prog, p_row['id']))
                    conn.commit()
                
                # نمایش فایل‌ها
                files_df = pd.read_sql(f"SELECT * FROM project_files WHERE proj_id={p_row['id']}", conn)
                for fld in files_df['folder'].unique():
                    st.write(f"📂 **{fld}**")
                    for _, f_row in files_df[files_df['folder'] == fld].iterrows():
                        cx, cy = st.columns([4, 1])
                        cx.text(f"📄 {f_row['file_name']}")
                        cy.download_button("📥", f_row['file_blob'], f_row['file_name'], key=f"dl_{f_row['id']}")
            
            with col_b:
                # خلاصه مالی پروژه
                fin_df = pd.read_sql(f"SELECT type, amount FROM finances WHERE proj_id={p_row['id']}", conn)
                income = fin_df[fin_df['type'] == "دریافتی (درآمد)"]['amount'].sum()
                expense = fin_df[fin_df['type'] == "پرداختی (هزینه)"]['amount'].sum()
                st.metric("مانده سود/طلب", f"{income - expense:,.0f} ریال")
                st.caption(f"📅 اعتبار: {p_row['expiry_date']}")
                if st.button("❌ حذف پروژه", key=f"del_p_{p_row['id']}"):
                    c.execute("DELETE FROM projects WHERE id=?", (p_row['id'],))
                    conn.commit()
                    st.rerun()
