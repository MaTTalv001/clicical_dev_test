import streamlit as st
import datetime

def render_pico_form():
    """PICO形式での入力フォームを提供"""
    with st.form(key='pico_form'):
        p = st.text_input(
            "Patient (対象患者):", 
            key='p',
            placeholder="例: 2型糖尿病の成人患者"
        )
        i = st.text_input(
            "Intervention (介入):", 
            key='i',
            placeholder="例: DPP-4阻害薬"
        )
        c = st.text_input(
            "Comparison (比較対象):", 
            key='c',
            placeholder="例: プラセボ、または標準治療"
        )
        o = st.text_input(
            "Outcome (結果):", 
            key='o',
            placeholder="例: HbA1cの改善"
        )
        
        # 試験開始期間
        st.write("試験開始期間")
        start_cols = st.columns(2)
        with start_cols[0]:
            start_date_min = st.date_input(
                "開始日（From）",
                value=None,
                min_value=datetime.date(2000, 1, 1),
                max_value=datetime.date.today(),
                key='start_date_min'
            )
        with start_cols[1]:
            start_date_max = st.date_input(
                "開始日（To）",
                value=None,
                min_value=datetime.date(2000, 1, 1),
                max_value=datetime.date.today(),
                key='start_date_max'
            )
        
        # 試験完了期間
        st.write("試験完了期間")
        end_cols = st.columns(2)
        with end_cols[0]:
            end_date_min = st.date_input(
                "完了日（From）",
                value=None,
                min_value=datetime.date(2000, 1, 1),
                max_value=datetime.date.today(),
                key='end_date_min'
            )
        with end_cols[1]:
            end_date_max = st.date_input(
                "完了日（To）",
                value=None,
                min_value=datetime.date(2000, 1, 1),
                max_value=datetime.date.today(),
                key='end_date_max'
            )

        additional = st.text_input(
            "Additional conditions (その他の追加条件):", 
            key='additional',
            placeholder="例: 18歳以上、BMI 25以上"
        )
        submitted = st.form_submit_button(label='検索')
        
    return submitted, p, i, c, o, {
        'start_date_range': (start_date_min, start_date_max),
        'end_date_range': (end_date_min, end_date_max)
    }, additional