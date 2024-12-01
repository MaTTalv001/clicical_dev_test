# app.py
"""
このモジュールは、臨床試験データの検索・分析・可視化を行うStreamlitベースのWebアプリケーションです。

主な機能：
1. PICO形式での臨床試験検索
2. 検索結果の構造化と可視化
3. LLMを用いた結果の分析と要約
4. 試験プロトコルの生成支援

アーキテクチャ：
- AWSのBedrock（Claude）を利用したLLM処理
- ClinicalTrials.gov APIを使用したデータ取得
- Streamlitによるインターフェース提供
"""

import streamlit as st
import os
import re
import json
import datetime
import boto3
import pandas as pd
import urllib.parse
from langchain_community.chat_models import BedrockChat
from utils.prompts import (
    SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, SUMMARY_PROMPT_TEMPLATE,
    CROSS_STUDY_PROMPT, CRITERIA_PROMPT, PUBLICATION_PROMPT,
    COMPARISON_PROMPT, PROTOCOL_PROMPT)
from utils.utils import get_top_items, convert_df_to_csv
from utils.api_handler import APIHandler
from utils.visualizer import Visualizer

# 定数とグローバル設定
st.set_page_config(page_title="Clinical Trials Search and Analysis App", layout="wide")

# AWSの認証情報の設定
os.environ['AWS_ACCESS_KEY_ID'] = st.secrets["AWS_ACCESS_KEY_ID"]
os.environ['AWS_SECRET_ACCESS_KEY'] = st.secrets["AWS_SECRET_ACCESS_KEY"]
os.environ['AWS_DEFAULT_REGION'] = st.secrets["AWS_DEFAULT_REGION"]

# 主要コンポーネントの初期化
bedrock = boto3.client('bedrock-runtime')
llm = BedrockChat(model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", client=bedrock)
api_handler = APIHandler("https://clinicaltrials.gov/api/v2/studies")

# セッション状態の初期化
if 'structured_studies' not in st.session_state:
    st.session_state.structured_studies = []
if 'selected_studies' not in st.session_state:
    st.session_state.selected_studies = []
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False
if 'total_count' not in st.session_state:
    st.session_state.total_count = 0
# 新しいステップの完了状態
if 'summary_generated' not in st.session_state:
    st.session_state.summary_generated = False
if 'criteria_analyzed' not in st.session_state:
    st.session_state.criteria_analyzed = False
if 'publications_summarized' not in st.session_state:
    st.session_state.publications_summarized = False
if 'comparison_analyzed' not in st.session_state:
    st.session_state.comparison_analyzed = False

@st.cache_data
def cached_fetch_and_structure_studies(query):
    """
    APIからの臨床試験データの取得と構造化を行い、結果をキャッシュする

    @st.cache_dataデコレータにより:
    - 同じクエリに対する結果がキャッシュされる
    - アプリの実行効率が向上する
    - APIへの不要なリクエストを削減できる

    Args:
        query (dict): 検索クエリパラメータ

    Returns:
        tuple: (構造化された試験データのリスト, 総試験数)
    """
    return api_handler.fetch_and_structure_studies(query)

def main():
    """
    APIからの臨床試験データの取得と構造化を行い、結果をキャッシュする

    @st.cache_dataデコレータにより:
    - 同じクエリに対する結果がキャッシュされる
    - アプリの実行効率が向上する
    - APIへの不要なリクエストを削減できる

    Args:
        query (dict): 検索クエリパラメータ

    Returns:
        tuple: (構造化された試験データのリスト, 総試験数)
    """
    st.title("Clinical Trials Search and Analysis App β版")
    st.markdown("""
        ### このアプリでできること
        1. **臨床試験の体系的な検索**: PICO形式での条件指定により、目的に合った臨床試験を検索
        2. **結果の自動要約**: 検索結果の傾向分析と可視化
        3. **個別試験の詳細確認**: 興味のある試験について詳しい情報を確認

        #### 使い方
        1. 下のフォームに検索条件を入力
        2. 必要に応じて試験期間を指定
        3. 「検索」ボタンをクリック
        
        > 💡 **Tip**: 検索結果が多すぎる場合は、試験期間や条件をより具体的に指定してください
        """)

    # PICO入力フォーム
    submitted, p, i, c, o, date_ranges, additional = input_pico_form()
    
    
    if submitted:
        query = generate_query(p, i, c, o, date_ranges, additional)
        if query:
            st.session_state.structured_studies, st.session_state.total_count = cached_fetch_and_structure_studies(query)
            st.session_state.search_performed = True
        
    if st.session_state.search_performed:
        # 結果の表示
        display_results(st.session_state.structured_studies, st.session_state.total_count)
        
        # 結果の要約と可視化
        if st.button("結果の要約と可視化を実行"):
            analyze_studies(st.session_state.structured_studies, p)
            st.session_state.summary_generated = True
        
        # 適格基準の詳細分析
        if st.session_state.summary_generated:
            if st.button("適格基準の詳細分析を実行"):
                analyze_eligibility_criteria(st.session_state.structured_studies)
                st.session_state.criteria_analyzed = True
        
        # 関連文献の要約
        if st.session_state.criteria_analyzed:
            if st.button("関連文献の要約を実行"):
                summarize_publications(st.session_state.structured_studies)
                st.session_state.publications_summarized = True
        
        # 複数の試験の横断的な比較分析
        if st.session_state.publications_summarized:
            if st.button("試験の比較分析を実行"):
                compare_studies(st.session_state.structured_studies)
                st.session_state.comparison_analyzed = True
        
        # プロトコルドラフト生成支援
        if st.session_state.comparison_analyzed:
            generate_protocol_draft(st.session_state.structured_studies)

def input_pico_form():
   """PICO形式での入力フォームを提供"""
   with st.form(key='pico_form'):
       p = st.text_input("Patient (対象患者):", key='p')
       i = st.text_input("Intervention (介入):", key='i')
       c = st.text_input("Comparison (比較対象):", key='c')
       o = st.text_input("Outcome (結果):", key='o')
       
       # 試験開始期間
       st.write("試験開始期間")
       start_cols = st.columns(2)
       with start_cols[0]:
           start_date_min = st.date_input(
               "開始日（From）",
               value=datetime.date(2010, 1, 1),
               min_value=datetime.date(2000, 1, 1),
               max_value=datetime.date.today(),
               key='start_date_min'
           )
       with start_cols[1]:
           start_date_max = st.date_input(
               "開始日（To）",
               value=datetime.date(2018, 12, 31),
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
               value=datetime.date(2010, 1, 1),
               min_value=datetime.date(2000, 1, 1),
               max_value=datetime.date.today(),
               key='end_date_min'
           )
       with end_cols[1]:
           end_date_max = st.date_input(
               "完了日（To）",
               value=datetime.date(2018, 12, 31),
               min_value=datetime.date(2000, 1, 1),
               max_value=datetime.date.today(),
               key='end_date_max'
           )

       additional = st.text_input("Additional conditions (その他の追加条件):", key='additional')
       submitted = st.form_submit_button(label='検索')
       
   return submitted, p, i, c, o, {
       'start_date_range': (start_date_min, start_date_max),
       'end_date_range': (end_date_min, end_date_max)
   }, additional

def generate_query(p, i, c, o, date_ranges, additional):
    """LLMを使用して検索クエリを生成"""
    user_prompt = USER_PROMPT_TEMPLATE.format(p=p, i=i, c=c, o=o, additional=additional)
    
    with st.spinner("クエリを生成中..."):
        response = llm.invoke(SYSTEM_PROMPT + "\n" + user_prompt)

    st.subheader("生成されたクエリ:")
    st.code(response.content, language='json')

    try:
        query = json.loads(response.content)
        
        # 日付範囲を追加
        start_min, start_max = date_ranges['start_date_range']
        end_min, end_max = date_ranges['end_date_range']
        
        # 日付フィルターの構築
        date_filters = []
        if start_min and start_max:  # 開始日範囲が指定されている場合
            date_filters.append(f"AREA[StartDate]RANGE[{start_min.strftime('%Y-%m-%d')},{start_max.strftime('%Y-%m-%d')}]")
        if end_min and end_max:      # 完了日範囲が指定されている場合
            date_filters.append(f"AREA[CompletionDate]RANGE[{end_min.strftime('%Y-%m-%d')},{end_max.strftime('%Y-%m-%d')}]")
        
        # 日付フィルターがある場合はadvancedフィルターに追加
        if date_filters:
            query['filter.advanced'] = " AND ".join(date_filters)

        st.success("クエリのパースに成功しました。")
        
        # clinicaltrials.govのURLを生成
        ct_gov_url = create_clinicaltrials_gov_url(query)
        
        # リンクボタンを作成
        st.markdown(f"[ClinicalTrials.govで確認する]({ct_gov_url})")
        
        return query
    except json.JSONDecodeError:
        st.error("生成されたクエリが正しいJSON形式ではありません。")
        return None
    
def create_clinicaltrials_gov_url(query):
    """
    APIクエリパラメータからClinicalTrials.govの検索URLを生成する

    Args:
        query (dict): APIクエリパラメータを含む辞書

    Returns:
        str: ClinicalTrials.govの検索URL
    """
    base_url = "https://clinicaltrials.gov/search?"
    params = {'viewType': 'Table'}  # デフォルトでテーブル表示
    
    # 疾患・状態の検索条件
    if 'query.cond' in query:
        params['cond'] = query['query.cond']
    
    # 介入方法の検索条件
    if 'query.intr' in query:
        params['intr'] = query['query.intr']
    
    # 日付範囲の処理
    if 'filter.advanced' in query:
        advanced = query['filter.advanced']
        
        # 開始日の範囲を抽出
        start_date_match = re.search(r'AREA\[StartDate\]RANGE\[(.*?),(.*?)\]', advanced)
        if start_date_match:
            start_date = start_date_match.group(1).strip()
            end_date = start_date_match.group(2).strip()
            params['start'] = f"{start_date}_{end_date}"
        
        # 完了日の範囲を抽出
        comp_date_match = re.search(r'AREA\[CompletionDate\]RANGE\[(.*?),(.*?)\]', advanced)
        if comp_date_match:
            start_date = comp_date_match.group(1).strip()
            end_date = comp_date_match.group(2).strip()
            params['studyComp'] = f"{start_date}_{end_date}"
    
    # 試験の状態
    if 'filter.overallStatus' in query:
        status = query['filter.overallStatus']
        if isinstance(status, list):
            status = status[0]  # リストの場合は最初の要素を使用
        
        status_map = {
            'COMPLETED': 'com',
            'RECRUITING': 'rec',
            'NOT_YET_RECRUITING': 'nyr',
            'ACTIVE_NOT_RECRUITING': 'anr',
            'TERMINATED': 'term',
            'WITHDRAWN': 'wth',
            'SUSPENDED': 'sus'
        }
        
        if status in status_map:
            params['aggFilters'] = f"status:{status_map[status]}"
    
    # ソート順
    if 'sort' in query:
        sort_options = query['sort']
        if isinstance(sort_options, list) and sort_options:
            if 'LastUpdatePostDate:desc' in sort_options:
                params['sort'] = 'nwst'
    
    encoded_params = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return base_url + encoded_params

def display_results(studies, total_count):
    """検索結果の表示と基本的な分析を行う"""
    st.divider()
    st.subheader(f"Total studies found: {total_count}")
    st.write(f"Studies retrieved: {len(studies)}")

    # データフレームへの変換
    df = pd.DataFrame(studies)

    # データフレームの表示
    st.subheader("取得データの一覧")
    st.dataframe(df)

    # データのダウンロード
    csv = convert_df_to_csv(df)
    st.download_button(
        label="Download as CSV",
        data=csv,
        file_name='structured_clinical_trials.csv',
        mime='text/csv',
    )

    # 検索結果一覧
    st.subheader("個別試験の要約(Optional)")
    study_options = [f"{study['nct_id']}: {study['title']}" for study in studies if study['title']]
    st.session_state.selected_studies = st.multiselect("詳細を確認したい試験を選択してください:", study_options, key='study_selector', default=st.session_state.selected_studies)

    for study_option in st.session_state.selected_studies:
        nct_id = study_option.split(":")[0]
        study = next((s for s in studies if s['nct_id'] == nct_id), None)
        if study:
            st.subheader(f"{study['nct_id']}: {study['title']}")
            st.write(f"**ステータス:** {study['status']}")
            st.write(f"**開始日:** {study['start_date']}")
            st.write(f"**終了日:** {study['end_date']}")
            st.write("**概要:**")
            st.write(study['brief_summary'])
            st.write("**介入内容:**")
            st.write(', '.join([intervention['name'] for intervention in study['interventions']]))
            st.write("**主要評価項目:**")
            st.write(', '.join(study['outcomes']['primary']))
            st.write("**副次評価項目:**")
            st.write(', '.join(study['outcomes']['secondary']))
            st.write("---")
    st.divider()
    st.subheader("取得データの要約")

def analyze_studies(studies, p):
    """
    取得した臨床試験データの詳細分析を実行
    - 介入の分布分析
    - 評価項目の分析
    - LLMによる要約生成
    """
    st.header("結果の要約と可視化")

    num_studies = len(studies)

    # 介入、適格基準、アウトカムの集計
    interventions = [intervention['name'] for study in studies for intervention in study['interventions']]
    eligibility_criteria = [study['eligibility']['criteria'] for study in studies]
    primary_outcomes = [outcome for study in studies for outcome in study['outcomes']['primary']]
    secondary_outcomes = [outcome for study in studies for outcome in study['outcomes']['secondary']]

    # 集計
    top_interventions = get_top_items(interventions)
    top_eligibility = get_top_items(eligibility_criteria)
    top_primary_outcomes = get_top_items(primary_outcomes)
    top_secondary_outcomes = get_top_items(secondary_outcomes)

    # LLMを使用して要約文を生成
    summary_prompt = SUMMARY_PROMPT_TEMPLATE.format(
        num_studies=num_studies,
        p=p,
        interventions=', '.join([f"{i[0]} ({i[1]}件)" for i in top_interventions]),
        eligibility=', '.join([f"{e[0][:50]}... ({e[1]}件)" for e in top_eligibility]),
        primary_outcomes=', '.join([f"{o[0]} ({o[1]}件)" for o in top_primary_outcomes]),
        secondary_outcomes=', '.join([f"{o[0]} ({o[1]}件)" for o in top_secondary_outcomes])
    )

    with st.spinner("結果を要約中..."):
        response = llm.invoke(summary_prompt)
        summary = response.content

    # 可視化
    st.subheader("評価対象医薬品の分布")
    fig1, drug_df = Visualizer.plot_drug_distribution(top_interventions)
    st.pyplot(fig1)

    st.subheader("主要評価項目の分布")
    fig2, outcome_df = Visualizer.plot_outcome_distribution(top_primary_outcomes)
    st.pyplot(fig2)

    # 結果の出力
    st.subheader("全体の要約")
    st.write(summary)

    st.subheader("Top 5 Evaluated Drugs:")
    st.table(drug_df)

    st.subheader("Top 5 Primary Outcomes:")
    st.table(outcome_df)

    # 選択された試験の横断的な要約
    if st.session_state.selected_studies:
        selected_study_data = [study for study in studies if f"{study['nct_id']}: {study['title']}" in st.session_state.selected_studies]
        cross_study_summaries = [f"""
        ### 試験ID: {study['nct_id']}
        - タイトル: {study['title']}
        - ステータス: {study['status']}
        - 開始日: {study['start_date']}
        - 終了日: {study['end_date']}
        - 介入内容: {', '.join([intervention['name'] for intervention in study['interventions']])}
        - 主要評価項目: {', '.join(study['outcomes']['primary'])}
        - 副次評価項目: {', '.join(study['outcomes']['secondary'])}
        """ for study in selected_study_data]

        cross_study_prompt = CROSS_STUDY_PROMPT.format(summaries=' '.join(cross_study_summaries))

        with st.spinner("選択された試験の横断的な要約を生成中..."):
            response = llm.invoke(cross_study_prompt)
            cross_study_summary = response.content

        st.subheader("選択された試験の横断的な要約")
        st.write(cross_study_summary)

def analyze_eligibility_criteria(studies):
    st.header("適格基準の詳細分析")

    if studies:
        eligibility_criteria = [study['eligibility']['criteria'] for study in studies]

        criteria_prompt = CRITERIA_PROMPT.format(criteria=' '.join(eligibility_criteria))

        with st.spinner("適格基準の分析を生成中..."):
            response = llm.invoke(criteria_prompt)
            criteria_analysis = response.content

        st.write(criteria_analysis)

def summarize_publications(studies):
    st.header("関連文献の要約")

    if studies:
        publications = [pub for study in studies for pub in study['publications']]

        if publications:
            publication_summaries = [f"""
            タイトル: {pub['title']}
            引用: {pub['citation']}
            PMID: {pub['pmid']}
            """ for pub in publications[:5]]

            publication_prompt = PUBLICATION_PROMPT.format(summaries=' '.join(publication_summaries))

            with st.spinner("関連文献の要約を生成中..."):
                response = llm.invoke(publication_prompt)
                publication_analysis = response.content

            st.write(publication_analysis)
        else:
            st.write("関連文献が見つかりませんでした。")

def compare_studies(studies):
    st.header("複数の試験の横断的な比較分析")

    if len(studies) >= 2:
        selected_studies = st.multiselect(
            "比較分析する試験を2つ以上選択してください：",
            options=[f"{study['nct_id']}: {study['title']}" for study in studies],
            default=[f"{studies[0]['nct_id']}: {studies[0]['title']}",
                    f"{studies[1]['nct_id']}: {studies[1]['title']}"],
            key='comparison_selector'
        )

        if len(selected_studies) >= 2:
            comparison_data = []
            for selected in selected_studies:
                nct_id = selected.split(":")[0].strip()
                study = next((s for s in studies if s['nct_id'] == nct_id), None)
                if study:
                    comparison_data.append(f"""
                    NCT ID: {study['nct_id']}
                    タイトル: {study['title']}
                    状態: {study['status']}
                    介入: {', '.join([i['name'] for i in study['interventions']])}
                    主要評価項目: {', '.join(study['outcomes']['primary'])}
                    副次評価項目: {', '.join(study['outcomes']['secondary'])}
                    適格基準: {study['eligibility']['criteria']}
                    """)

            comparison_prompt = COMPARISON_PROMPT.format(comparison_data=' '.join(comparison_data))

            with st.spinner("試験の比較分析を生成中..."):
                response = llm.invoke(comparison_prompt)
                comparison_analysis = response.content

            st.write(comparison_analysis)
        else:
            st.write("比較するには2つ以上の試験を選択してください。")

def generate_protocol_draft(studies):
    st.header("プロトコルドラフト生成支援")
    st.write("収集した情報を基に、新しい臨床試験のプロトコルドラフトを生成します。")
    
    target_condition = st.text_input("対象疾患：", key='target_condition')
    intervention = st.text_input("介入方法：", key='intervention')
    primary_outcome = st.text_input("主要評価項目：", key='primary_outcome')

    if st.button("プロトコルドラフトを生成", key='generate_protocol'):
        existing_studies = [
            f"NCT ID: {s['nct_id']}, タイトル: {s['title']}, 状態: {s['status']}, "
            f"介入: {', '.join([i['name'] for i in s['interventions']])}, "
            f"主要評価項目: {', '.join(s['outcomes']['primary'])}"
            for s in studies[:5]
        ]

        protocol_prompt = PROTOCOL_PROMPT.format(
            target_condition=target_condition,
            intervention=intervention,
            primary_outcome=primary_outcome,
            existing_studies=' '.join(existing_studies)
        )

        with st.spinner("プロトコルドラフトを生成中..."):
            response = llm.invoke(protocol_prompt)
            protocol_draft = response.content

        st.subheader("生成されたプロトコルドラフト")
        st.write(protocol_draft)

if __name__ == "__main__":
    main()