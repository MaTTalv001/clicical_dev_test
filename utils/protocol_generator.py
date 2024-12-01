"""
プロトコル生成支援モジュール

このモジュールは、既存の臨床試験データを基に新しい試験プロトコルの
ドラフト生成を支援する機能を提供します。
"""

import streamlit as st
import pandas as pd

class ProtocolGenerator:
    @staticmethod
    def render_protocol_form(studies, llm, protocol_prompt):
        """
        プロトコルドラフト生成のためのフォームを表示し、
        入力に基づいてドラフトを生成する

        Args:
            studies (list): 参照する臨床試験データのリスト
            llm: LLMインスタンス
            protocol_prompt (str): プロトコル生成用のプロンプトテンプレート
        """
        st.header("プロトコルドラフト生成支援")
        st.write("""
            収集した情報を基に、新しい臨床試験のプロトコルドラフトを生成します。
            以下のフォームに必要な情報を入力してください。
        """)
        
        with st.form("protocol_form"):
            # 基本情報の入力
            col1, col2 = st.columns(2)
            with col1:
                target_condition = st.text_input(
                    "対象疾患",
                    help="研究対象となる疾患や状態を入力してください"
                )
                intervention = st.text_input(
                    "介入方法",
                    help="評価する治療法や介入方法を入力してください"
                )
                phase = st.selectbox(
                    "試験フェーズ",
                    options=["Phase 1", "Phase 2", "Phase 3", "Phase 4"],
                    help="臨床試験のフェーズを選択してください"
                )
            
            with col2:
                primary_outcome = st.text_input(
                    "主要評価項目",
                    help="主たる有効性評価項目を入力してください"
                )
                study_design = st.selectbox(
                    "試験デザイン",
                    options=[
                        "Randomized Controlled Trial",
                        "Single Arm Study",
                        "Observational Study",
                        "Other"
                    ],
                    help="試験のデザインタイプを選択してください"
                )
                duration = st.number_input(
                    "試験期間（週）",
                    min_value=1,
                    max_value=520,
                    value=52,
                    help="計画している試験期間を週単位で入力してください"
                )

            # 追加設定
            st.subheader("追加設定（オプション）")
            
            col3, col4 = st.columns(2)
            with col3:
                population_size = st.number_input(
                    "目標症例数",
                    min_value=1,
                    max_value=10000,
                    value=100,
                    help="計画している目標症例数を入力してください"
                )
                inclusion_criteria = st.text_area(
                    "主な選択基準",
                    height=100,
                    help="主要な選択基準を入力してください"
                )
            
            with col4:
                control_group = st.text_input(
                    "対照群の設定",
                    help="対照群がある場合の詳細を入力してください"
                )
                exclusion_criteria = st.text_area(
                    "主な除外基準",
                    height=100,
                    help="主要な除外基準を入力してください"
                )

            # 参照する試験の選択
            st.subheader("参照する試験の選択")
            reference_studies = st.multiselect(
                "このプロトコルの作成時に特に参照したい試験を選択してください：",
                options=[f"{study['nct_id']}: {study['title']}" for study in studies],
                help="選択した試験の設計を特に参考にしてプロトコルを生成します"
            )

            # 生成オプション
            st.subheader("生成オプション")
            detail_level = st.select_slider(
                "詳細度",
                options=["Basic", "Standard", "Detailed"],
                value="Standard",
                help="生成するプロトコルの詳細度を選択してください"
            )
            
            focus_areas = st.multiselect(
                "特に詳しく記載してほしい項目",
                options=[
                    "適格基準",
                    "評価項目",
                    "統計解析計画",
                    "安全性モニタリング",
                    "中止基準",
                    "症例報告書",
                    "検査スケジュール"
                ],
                default=["適格基準", "評価項目"],
                help="特に詳細な記載が必要な項目を選択してください"
            )

            submitted = st.form_submit_button("プロトコルドラフトを生成")

        if submitted:
            ProtocolGenerator._generate_protocol_draft(
                studies,
                llm,
                protocol_prompt,
                {
                    'target_condition': target_condition,
                    'intervention': intervention,
                    'phase': phase,
                    'primary_outcome': primary_outcome,
                    'study_design': study_design,
                    'duration': duration,
                    'population_size': population_size,
                    'inclusion_criteria': inclusion_criteria,
                    'control_group': control_group,
                    'exclusion_criteria': exclusion_criteria,
                    'reference_studies': reference_studies,
                    'detail_level': detail_level,
                    'focus_areas': focus_areas
                }
            )

    @staticmethod
    def _generate_protocol_draft(studies, llm, protocol_prompt, params):
        """
        入力パラメータに基づいてプロトコルドラフトを生成

        Args:
            studies (list): 臨床試験データのリスト
            llm: LLMインスタンス
            protocol_prompt (str): プロトコル生成用のプロンプト
            params (dict): 生成パラメータ
        """
        # 参照試験の詳細情報を取得
        reference_study_details = []
        if params['reference_studies']:
            for ref in params['reference_studies']:
                nct_id = ref.split(":")[0].strip()
                study = next((s for s in studies if s['nct_id'] == nct_id), None)
                if study:
                    reference_study_details.append(
                        ProtocolGenerator._format_study_details(study)
                    )

        # プロンプトの構築
        formatted_prompt = protocol_prompt.format(
            target_condition=params['target_condition'],
            intervention=params['intervention'],
            phase=params['phase'],
            primary_outcome=params['primary_outcome'],
            study_design=params['study_design'],
            duration=params['duration'],
            population_size=params['population_size'],
            inclusion_criteria=params['inclusion_criteria'],
            control_group=params['control_group'],
            exclusion_criteria=params['exclusion_criteria'],
            detail_level=params['detail_level'],
            focus_areas=", ".join(params['focus_areas']),
            reference_studies="\n".join(reference_study_details)
        )

        # プロトコルの生成
        with st.spinner("プロトコルドラフトを生成中..."):
            response = llm.invoke(formatted_prompt)
            protocol_draft = response.content

        # 生成結果の表示
        st.subheader("生成されたプロトコルドラフト")
        
        # タブで表示形式を切り替え可能に
        tab1, tab2 = st.tabs(["プレビュー", "編集可能テキスト"])
        
        with tab1:
            st.markdown(protocol_draft)
        
        with tab2:
            edited_protocol = st.text_area(
                "プロトコルの編集",
                value=protocol_draft,
                height=500
            )
            
            # ダウンロードボタン
            st.download_button(
                label="プロトコルをダウンロード",
                data=edited_protocol,
                file_name="protocol_draft.md",
                mime="text/markdown"
            )

        # 生成されたプロトコルの評価オプション
        st.subheader("プロトコルの評価")
        
        quality_metrics = {
            "完全性": st.slider(
                "必要な要素がすべて含まれていますか？",
                0, 10, 5
            ),
            "明確性": st.slider(
                "記述は明確で分かりやすいですか？",
                0, 10, 5
            ),
            "実現可能性": st.slider(
                "実施可能な内容になっていますか？",
                0, 10, 5
            )
        }
        
        feedback = st.text_area(
            "追加のフィードバック",
            placeholder="プロトコルに対する具体的なフィードバックがあれば入力してください"
        )
        
        if st.button("フィードバックを送信"):
            # フィードバックの保存や処理をここに実装
            st.success("フィードバックを受け付けました。ありがとうございます。")

    @staticmethod
    def _format_study_details(study):
        """
        参照用の試験詳細情報をフォーマット

        Args:
            study (dict): 臨床試験データ

        Returns:
            str: フォーマットされた試験詳細
        """
        return f"""
        ## 試験 {study['nct_id']}
        タイトル: {study['title']}
        デザイン: {study['study_design']}
        対象患者: {study['eligibility']['criteria']}
        介入: {', '.join([i['name'] for i in study['interventions']])}
        主要評価項目: {', '.join(study['outcomes']['primary'])}
        副次評価項目: {', '.join(study['outcomes']['secondary'])}
        試験期間: {study['start_date']} - {study['end_date']}
        """