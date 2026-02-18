import streamlit as st
import pandas as pd
import sqlite3
import json
import datetime

# اتصال به دیتابیس برای ذخیره همیشگی اطلاعات
conn = sqlite3.connect('civil_data.db', check_same_thread=False)
c = conn.cursor()

# ایجاد جداول
c.execute('CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY, parent_id INTEGER, name TEXT, level TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, loc_id INTEGER, name TEXT, data TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS finances (id INTEGER PRIMARY KEY, proj_id INTEGER, amount REAL, type TEXT, note TEXT, date TEXT)')
conn.commit()

st.set_page_config(page_title="مدیریت مهندسی", layout="wide")

tab1, tab2, tab3 = st.tabs(["🏗️ مدیریت پروژه‌ها", "💰 ثبت مالی", "🌍 تعریف مناطق"])

# --- بخش تعریف مناطق (استان/شهر/روستا) ---
with tab3:
    st.header("تعریف سلسله‌مراتب مکانی")
    level = st.selectbox("سطح جدید", ["استان", "شهرستان", "شهر/روستا"])
    parent_id = 0
    
    if level == "شهرستان":
        provinces = pd.read_sql("SELECT * FROM locations WHERE level='استان'", conn)
        if not provinces.empty:
            p_choice = st.selectbox("انتخاب استان", provinces['name'].tolist())
            parent_id = provinces[provinces['name'] == p_choice]['id'].values[0]
    elif level == "شهر/روستا":
        counties = pd.read_sql("SELECT * FROM locations WHERE level='شهرستان'", conn)
        if not counties.empty:
            c_choice = st.selectbox("انتخاب شهرستان", counties['name'].tolist())
            parent_id = counties[counties['name'] == c_choice]['id'].values[0]

    loc_name = st.text_input(f"نام {level}")
    if st.button(f"ثبت {level}"):
        c.execute("INSERT INTO locations (parent_id, name, level) VALUES (?,?,?)", (int(parent_id), loc_name, level))
        conn.commit()
        st.success(f"{level} با موفقیت ثبت شد.")

# --- بخش مدیریت پروژه‌ها ---
with tab1:
    st.header("پروژه‌ها و ویژگی‌های دلخواه")
    villages = pd.read_sql("SELECT * FROM locations WHERE level='شهر/روستا'", conn)
    if not villages.empty:
        selected_v = st.selectbox("انتخاب محل پروژه (شهر/روستا)", villages['name'].tolist())
        v_id = villages[villages['name'] == selected_v]['id'].values[0]
        
        st.divider()
        p_name = st.text_input("نام پروژه جدید")
        
        if 'fields' not in st.session_state: st.session_state.fields = {}
        
        col1, col2 = st.columns(2)
        f_name = col1.text_input("نام ویژگی (مثلاً پلاک ثبتی)")
        f_val = col2.text_input("مقدار")
        if st.button("افزودن ویژگی"):
            st.session_state.fields[f_name] = f_val
        
        st.write("ویژگی‌های این پروژه:", st.session_state.fields)
        
        if st.button("ذخیره نهایی پروژه"):
            data_str = json.dumps(st.session_state.fields)
            c.execute("INSERT INTO projects (loc_id, name, data) VALUES (?,?,?)", (int(v_id), p_name, data_str))
            conn.commit()
            st.session_state.fields = {}
            st.success("پروژه با موفقیت ذخیره شد.")
    else:
        st.info("ابتدا از تب 'تعریف مناطق'، استان و شهر و روستا را بسازید.")

# --- بخش مالی ---
with tab2:
    st.header("حساب‌داری پروژه")
    all_projs = pd.read_sql("SELECT * FROM projects", conn)
    if not all_projs.empty:
        p_sel = st.selectbox("پروژه مورد نظر", all_projs['name'].tolist())
        p_id = all_projs[all_projs['name'] == p_sel]['id'].values[0]
        
        amount = st.number_input("مبلغ (تومان)", step=500000)
        f_type = st.radio("نوع تراکنش", ["واریزی / درآمد", "هزینه / مخارج"])
        note = st.text_input("توضیحات")
        
        if st.button("ثبت تراکنش"):
            d = datetime.datetime.now().strftime("%Y-%m-%d")
            c.execute("INSERT INTO finances (proj_id, amount, type, note, date) VALUES (?,?,?,?,?)", 
                      (int(p_id), amount, f_type, note, d))
            conn.commit()
            st.success("تراکنش مالی ثبت شد.")
