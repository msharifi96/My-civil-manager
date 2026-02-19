# --- اصلاح بخش نمایش فایل در داشبورد ---
with st.expander(f"📁 {fld['name']}", expanded=True):
    files = pd.read_sql(f"SELECT * FROM project_files WHERE folder_id={fld['id']}", conn)
    for _, fl in files.iterrows():
        # ایجاد دو ستون: ستون سمت چپ برای آیکون‌ها (باریک) و ستون سمت راست برای نام (پهن)
        col_icons, col_filename = st.columns([1, 4])
        
        # ۱. نمایش نام فایل در سمت راست (با تراز راست)
        col_filename.markdown(f"""
            <div style="text-align: right; direction: rtl; padding-top: 5px;">
                📄 {fl['file_name']}
            </div>
            """, unsafe_allow_html=True)
        
        # ۲. نمایش آیکون‌ها در سمت چپ (بدون کادر و مربع)
        with col_icons:
            # ایجاد ۳ زیرستون بسیار فشرده برای آیکون‌ها
            i1, i2, i3 = st.columns(3)
            
            # آیکون حذف
            if i1.button("🗑️", key=f"del_{fl['id']}", help="حذف"):
                c.execute(f"DELETE FROM project_files WHERE id={fl['id']}")
                conn.commit()
                st.rerun()
            
            # آیکون لینک
            if i2.button("🔗", key=f"lnk_{fl['id']}", help="کپی لینک"):
                b64 = base64.b64encode(fl['file_blob']).decode()
                st.toast("لینک تولید شد")
                st.code(f"data:file;base64,{b64[:20]}...")

            # آیکون دانلود
            i3.download_button("📥", fl['file_blob'], fl['file_name'], key=f"dn_{fl['id']}")

# --- بخش CSS برای حذف نهایی مربع دور دکمه‌ها ---
st.markdown("""
    <style>
    /* حذف کادر، سایه و پس‌زمینه دکمه‌های آیکونی */
    div[data-testid="column"] button, 
    div[data-testid="stDownloadButton"] button {
        border: none !important;
        background: transparent !important;
        background-color: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
        width: 30px !important;
        height: 30px !important;
    }
    /* جابجایی ستون آیکون‌ها به منتهی‌الیه سمت چپ */
    div[data-testid="column"]:nth-child(1) {
        justify-content: flex-start;
    }
    </style>
    """, unsafe_allow_html=True)
