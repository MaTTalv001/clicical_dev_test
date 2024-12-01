import streamlit as st
import pandas as pd
from utils.visualizer import Visualizer

class ResultAnalyzer:
    @staticmethod
    def display_results(studies, total_count, df_converter):
        """
        検索結果の表示と基本的な分析を行う

        Args:
            studies (list): 臨床試験データのリスト
            total_count (int): 検索結果の総数
            df_converter (function): DataFrameをCSVに変換する関数
        """
        st.divider()
        st.subheader(f"Total studies found: {total_count}")
        st.write(f"Studies retrieved: {len(studies)}")

        # データフレームへの変換
        df = pd.DataFrame(studies)

        # データフレームの表示
        st.subheader("取得データの一覧")
        st.dataframe(df)

        # データのダウンロード
        csv = df_converter(df)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name='structured_clinical_trials.csv',
            mime='text/csv',
        )

        # 検索結果一覧
        st.subheader("個別試験の確認(Optional)")
        study_options = [
            f"{study['nct_id']}: {study['title']}" 
            for study in studies 
            if study['title']
        ]
        st.session_state.selected_studies = st.multiselect(
            "詳細を確認したい試験を選択してください:", 
            study_options, 
            key='study_selector', 
            default=st.session_state.selected_studies
        )

        for study_option in st.session_state.selected_studies:
            nct_id = study_option.split(":")[0]
            study = next((s for s in studies if s['nct_id'] == nct_id), None)
            if study:
                ResultAnalyzer._display_study_details(study)

        st.divider()
        st.subheader("取得データの要約")

    @staticmethod
    def _display_study_details(study):
        """
        個別の臨床試験の詳細を表示

        Args:
            study (dict): 臨床試験データ
        """
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

    @staticmethod
    def analyze_studies(studies, p, llm, summary_prompt_template, get_top_items):
        """
        取得した臨床試験データの詳細分析を実行

        Args:
            studies (list): 臨床試験データのリスト
            p (str): Patient (対象患者)
            llm: LLMインスタンス
            summary_prompt_template (str): 要約生成用のプロンプトテンプレート
            get_top_items (function): アイテムの頻度カウント関数
        """
        st.header("結果の要約と可視化")

        num_studies = len(studies)

        # 介入、適格基準、アウトカムの集計
        interventions = [
            intervention['name'] 
            for study in studies 
            for intervention in study['interventions']
        ]
        eligibility_criteria = [
            study['eligibility']['criteria'] 
            for study in studies
        ]
        primary_outcomes = [
            outcome 
            for study in studies 
            for outcome in study['outcomes']['primary']
        ]
        secondary_outcomes = [
            outcome 
            for study in studies 
            for outcome in study['outcomes']['secondary']
        ]

        # 集計
        top_interventions = get_top_items(interventions)
        top_eligibility = get_top_items(eligibility_criteria)
        top_primary_outcomes = get_top_items(primary_outcomes)
        top_secondary_outcomes = get_top_items(secondary_outcomes)

        # LLMを使用して要約文を生成
        summary_prompt = summary_prompt_template.format(
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
        st.plotly_chart(fig1, use_container_width=True)

        st.subheader("主要評価項目の分布")
        fig2, outcome_df = Visualizer.plot_outcome_distribution(top_primary_outcomes)
        st.plotly_chart(fig2, use_container_width=True)

        # 結果の出力
        st.subheader("全体の要約")
        st.write(summary)

        st.subheader("Top 5 Evaluated Drugs:")
        st.table(drug_df)

        st.subheader("Top 5 Primary Outcomes:")
        st.table(outcome_df)

        # 選択された試験の横断的な要約
        ResultAnalyzer._analyze_selected_studies(studies, llm)

    @staticmethod
    def _analyze_selected_studies(studies, llm):
        """
        選択された試験の横断的な分析を実行

        Args:
            studies (list): 臨床試験データのリスト
            llm: LLMインスタンス
        """
        if st.session_state.selected_studies:
            selected_study_data = [
                study for study in studies 
                if f"{study['nct_id']}: {study['title']}" in st.session_state.selected_studies
            ]
            cross_study_summaries = [
                ResultAnalyzer._format_study_summary(study) 
                for study in selected_study_data
            ]

            cross_study_prompt = ResultAnalyzer._generate_cross_study_prompt(
                ' '.join(cross_study_summaries)
            )

            with st.spinner("選択された試験の横断的な要約を生成中..."):
                response = llm.invoke(cross_study_prompt)
                cross_study_summary = response.content

            st.subheader("選択された試験の横断的な要約")
            st.write(cross_study_summary)

    @staticmethod
    def _format_study_summary(study):
        """
        試験データを要約用にフォーマット

        Args:
            study (dict): 臨床試験データ

        Returns:
            str: フォーマットされた試験要約
        """
        return f"""
        ### 試験ID: {study['nct_id']}
        - タイトル: {study['title']}
        - ステータス: {study['status']}
        - 開始日: {study['start_date']}
        - 終了日: {study['end_date']}
        - 介入内容: {', '.join([intervention['name'] for intervention in study['interventions']])}
        - 主要評価項目: {', '.join(study['outcomes']['primary'])}
        - 副次評価項目: {', '.join(study['outcomes']['secondary'])}
        """

    @staticmethod
    def _generate_cross_study_prompt(summaries):
        """
        横断的分析用のプロンプトを生成

        Args:
            summaries (str): 試験要約の文字列

        Returns:
            str: 生成されたプロンプト
        """
        return f"""
        以下の臨床試験データを横断的に分析し、主な特徴、類似点、相違点、
        および重要な知見をまとめてください：

        {summaries}
        """

    @staticmethod
    def analyze_eligibility_criteria(studies, llm, criteria_prompt):
        """
        適格基準の詳細分析を実行

        Args:
            studies (list): 臨床試験データのリスト
            llm: LLMインスタンス
            criteria_prompt (str): 適格基準分析用のプロンプト
        """
        st.header("適格基準の詳細分析")

        if studies:
            eligibility_criteria = [
                study['eligibility']['criteria'] 
                for study in studies
            ]

            criteria_analysis_prompt = criteria_prompt.format(
                criteria=' '.join(eligibility_criteria)
            )

            with st.spinner("適格基準の分析を生成中..."):
                response = llm.invoke(criteria_analysis_prompt)
                criteria_analysis = response.content

            st.write(criteria_analysis)

    @staticmethod
    def summarize_publications(studies, llm, publication_prompt):
        """
        関連文献の要約を生成

        Args:
            studies (list): 臨床試験データのリスト
            llm: LLMインスタンス
            publication_prompt (str): 文献要約用のプロンプト
        """
        st.header("関連文献の要約")

        if studies:
            publications = [
                pub 
                for study in studies 
                for pub in study['publications']
            ]

            if publications:
                publication_summaries = [
                    f"""
                    タイトル: {pub['title']}
                    引用: {pub['citation']}
                    PMID: {pub['pmid']}
                    """ 
                    for pub in publications[:5]
                ]

                pub_analysis_prompt = publication_prompt.format(
                    summaries=' '.join(publication_summaries)
                )

                with st.spinner("関連文献の要約を生成中..."):
                    response = llm.invoke(pub_analysis_prompt)
                    publication_analysis = response.content

                st.write(publication_analysis)
            else:
                st.write("関連文献が見つかりませんでした。")

    @staticmethod
    def compare_studies(studies, llm, comparison_prompt):
        """
        複数の試験の横断的な比較分析を実行

        Args:
            studies (list): 臨床試験データのリスト
            llm: LLMインスタンス
            comparison_prompt (str): 比較分析用のプロンプト
        """
        st.header("複数の試験の横断的な比較分析")

        if len(studies) >= 2:
            selected_studies = st.multiselect(
                "比較分析する試験を2つ以上選択してください：",
                options=[
                    f"{study['nct_id']}: {study['title']}" 
                    for study in studies
                ],
                default=[
                    f"{studies[0]['nct_id']}: {studies[0]['title']}",
                    f"{studies[1]['nct_id']}: {studies[1]['title']}"
                ],
                key='comparison_selector'
            )

            if len(selected_studies) >= 2:
                comparison_data = []
                for selected in selected_studies:
                    nct_id = selected.split(":")[0].strip()
                    study = next(
                        (s for s in studies if s['nct_id'] == nct_id), 
                        None
                    )
                    if study:
                        comparison_data.append(
                            ResultAnalyzer._format_study_for_comparison(study)
                        )

                comparison_analysis_prompt = comparison_prompt.format(
                    comparison_data=' '.join(comparison_data)
                )

                with st.spinner("試験の比較分析を生成中..."):
                    response = llm.invoke(comparison_analysis_prompt)
                    comparison_analysis = response.content

                st.write(comparison_analysis)
            else:
                st.write("比較するには2つ以上の試験を選択してください。")

    @staticmethod
    def _format_study_for_comparison(study):
        """
        比較分析用に試験データをフォーマット

        Args:
            study (dict): 臨床試験データ

        Returns:
            str: フォーマットされた試験データ
        """
        return f"""
        NCT ID: {study['nct_id']}
        タイトル: {study['title']}
        状態: {study['status']}
        介入: {', '.join([i['name'] for i in study['interventions']])}
        主要評価項目: {', '.join(study['outcomes']['primary'])}
        副次評価項目: {', '.join(study['outcomes']['secondary'])}
        適格基準: {study['eligibility']['criteria']}
        """