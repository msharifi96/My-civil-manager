        elif mode_pj == "ویرایش پروژه":
            if not all_p.empty:
                # ایجاد نام نمایشی برای انتخاب پروژه
                all_p['disp'] = all_p.apply(lambda x: f"ق: {x['contract_no']} - {x['name']}", axis=1)
                target_p = st.selectbox("انتخاب پروژه جهت ویرایش:", all_p['disp'].tolist(), key="ed_pj_select")
                
                # استخراج اطلاعات فعلی پروژه
                p_id = all_p[all_p['disp']==target_p]['id'].values[0]
                p_data = all_p[all_p['id']==p_id].iloc[0]
                
                st.markdown("---")
                # ۱. ویرایش محل پروژه (اصلاح کل موقعیت مکانی)
                v_list = pd.read_sql("SELECT * FROM locations WHERE level='شهر یا روستا' AND p_type=?", conn, params=(m_sec,))
                if not v_list.empty:
                    # پیدا کردن نام محل فعلی پروژه برای نمایش در پیش‌فرض
                    current_loc_row = v_list[v_list['id'] == p_data['loc_id']]
                    current_loc_name = current_loc_row['name'].values[0] if not current_loc_row.empty else v_list['name'].tolist()[0]
                    
                    new_loc = st.selectbox("اصلاح/تغییر محل پروژه:", v_list['name'].tolist(), 
                                           index=v_list['name'].tolist().index(current_loc_name),
                                           key="ed_pj_loc")
                    new_vid = v_list[v_list['name']==new_loc]['id'].values[0]
                
                # ۲. ویرایش سایر مشخصات
                new_pn = st.text_input("اصلاح نام پروژه:", value=p_data['name'], key="ed_pj_name")
                new_cp = st.text_input("اصلاح نام شرکت:", value=p_data['company'], key="ed_pj_comp")
                new_cn = st.text_input("اصلاح شماره قرارداد:", value=p_data['contract_no'], key="ed_pj_cont")

                if st.button("💾 ثبت تغییرات کلی پروژه", use_container_width=True, type="primary"):
                    c.execute("""
                        UPDATE projects 
                        SET loc_id=?, name=?, company=?, contract_no=? 
                        WHERE id=?
                    """, (int(new_vid), new_pn, new_cp, new_cn, int(p_id)))
                    conn.commit()
                    st.success("تمامی مشخصات پروژه با موفقیت بروزرسانی شد.")
                    st.rerun()
            else:
                st.info("پروژه‌ای برای ویرایش یافت نشد.")
