"""
Clinical Trials Search and Analysis App

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
import boto3
from langchain_community.chat_models import BedrockChat

# 独自のユーティリティモジュールのインポート
from utils.state_manager import initialize_session_state
from utils.form_handler import render_pico_form
from utils.query_generator import QueryGenerator
from utils.result_analyzer import ResultAnalyzer
from utils.visualizer import Visualizer
from utils.protocol_generator import ProtocolGenerator
from utils.api_handler import APIHandler
from utils.prompts import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    SUMMARY_PROMPT_TEMPLATE,
    CRITERIA_PROMPT,
    PROTOCOL_PROMPT,
    COMPREHENSIVE_SUMMARY_PROMPT
)
from utils.utils import get_top_items, convert_df_to_csv

def initialize_app():
    """
    アプリケーションの初期設定を行う
    - ページ設定
    - AWS認証情報の設定
    - LLMモデルの初期化
    - APIハンドラーの初期化
    
    Returns:
        tuple: (BedrockChat, APIHandler) - 初期化されたLLMとAPIハンドラー
    """
    # Streamlitページの設定
    st.set_page_config(
        page_title="Clinical Trials Search and Analysis App",
        layout="wide"
    )

    # AWS認証情報の設定
    os.environ['AWS_ACCESS_KEY_ID'] = st.secrets["AWS_ACCESS_KEY_ID"]
    os.environ['AWS_SECRET_ACCESS_KEY'] = st.secrets["AWS_SECRET_ACCESS_KEY"]
    os.environ['AWS_DEFAULT_REGION'] = st.secrets["AWS_DEFAULT_REGION"]

    # AWS Bedrockクライアントの初期化
    bedrock = boto3.client('bedrock-runtime')
    llm = BedrockChat(
        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
        client=bedrock
    )

    # APIハンドラーの初期化
    api_handler = APIHandler("https://clinicaltrials.gov/api/v2/studies")

    return llm, api_handler

def render_app_description():
    """アプリケーションの説明を表示"""
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

def handle_search_results(llm, studies, total_count, p):
    """
    検索結果の表示と分析機能の提供

    Args:
        llm: LLMインスタンス
        studies (list): 臨床試験データのリスト
        total_count (int): 検索結果の総数
        p (str): Patient (対象患者)
    """
    # 基本的な結果表示
    ResultAnalyzer.display_results(
        studies,
        total_count,
        convert_df_to_csv
    )
    
    # # 詳細分析ボタン
    # if st.button("検索結果の詳細分析を実行"):
    #     with st.spinner("分析を実行中..."):
    #         ResultAnalyzer.analyze_studies(
    #             studies,
    #             p,
    #             llm,
    #             SUMMARY_PROMPT_TEMPLATE,
    #             get_top_items
    #         )
    #         st.session_state.analysis_complete = True
    
    # 詳細分析ボタン
    if st.button("検索結果の詳細分析を実行"):
        with st.spinner("分析を実行中..."):
            # 可視化
            Visualizer.visualize_distributions(studies)
            # 適格基準の分析と総合要約を実行
            ResultAnalyzer.analyze_and_summarize(
                studies, 
                p, 
                llm, 
                COMPREHENSIVE_SUMMARY_PROMPT
            )
            st.session_state.analysis_complete = True
    
    # プロトコル生成支援
    # if st.session_state.analysis_complete:
    #     ProtocolGenerator.render_protocol_form(
    #         studies,
    #         llm,
    #         PROTOCOL_PROMPT
    #     )

def main():
    """
    アプリケーションのメインエントリーポイント
    - アプリの初期化
    - UI要素の表示
    - 検索と分析の実行
    """
    # アプリケーションの初期化
    llm, api_handler = initialize_app()
    initialize_session_state()
    
    # アプリの説明表示
    render_app_description()
    
    # PICO入力フォームの表示と検索実行
    submitted, p, i, c, o, date_ranges, additional = render_pico_form()
    
    if submitted:
        # クエリの生成と検索実行
        query = QueryGenerator.generate_query(
            llm,
            p, i, c, o,
            date_ranges,
            additional,
            SYSTEM_PROMPT,
            USER_PROMPT_TEMPLATE
        )
        
        if query:
            # 検索実行
            st.session_state.structured_studies, st.session_state.total_count = (
                api_handler.fetch_and_structure_studies(query)
            )
            st.session_state.search_performed = True
    
    # 検索結果の処理
    if st.session_state.search_performed:
        handle_search_results(
            llm,
            st.session_state.structured_studies,
            st.session_state.total_count,
            p
        )

if __name__ == "__main__":
    main()