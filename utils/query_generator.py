import json
import re
import urllib.parse
import streamlit as st

class QueryGenerator:
    @staticmethod
    def generate_query(llm, p, i, c, o, date_ranges, additional, system_prompt, user_prompt_template):
        """
        LLMを使用して検索クエリを生成

        Args:
            llm: LLMインスタンス
            p (str): Patient (対象患者)
            i (str): Intervention (介入)
            c (str): Comparison (比較対象)
            o (str): Outcome (結果)
            date_ranges (dict): 日付範囲の指定
            additional (str): 追加条件
            system_prompt (str): システムプロンプト
            user_prompt_template (str): ユーザープロンプトのテンプレート

        Returns:
            dict: 生成されたクエリパラメータ
            None: クエリ生成に失敗した場合
        """
        user_prompt = user_prompt_template.format(p=p, i=i, c=c, o=o, additional=additional)
        
        with st.spinner("クエリを生成中..."):
            response = llm.invoke(system_prompt + "\n" + user_prompt)

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
                date_filters.append(
                    f"AREA[StartDate]RANGE[{start_min.strftime('%Y-%m-%d')},"
                    f"{start_max.strftime('%Y-%m-%d')}]"
                )
            if end_min and end_max:      # 完了日範囲が指定されている場合
                date_filters.append(
                    f"AREA[CompletionDate]RANGE[{end_min.strftime('%Y-%m-%d')},"
                    f"{end_max.strftime('%Y-%m-%d')}]"
                )
            
            # 日付フィルターがある場合はadvancedフィルターに追加
            if date_filters:
                query['filter.advanced'] = " AND ".join(date_filters)

            st.success("クエリのパースに成功しました。")
            
            # clinicaltrials.govのURLを生成
            ct_gov_url = QueryGenerator.create_clinicaltrials_gov_url(query)
            
            # リンクボタンを作成
            st.markdown(f"[ClinicalTrials.govで確認する]({ct_gov_url})")
            
            return query
            
        except json.JSONDecodeError:
            st.error("生成されたクエリが正しいJSON形式ではありません。")
            return None

    @staticmethod
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
            start_date_match = re.search(
                r'AREA\[StartDate\]RANGE\[(.*?),(.*?)\]',
                advanced
            )
            if start_date_match:
                start_date = start_date_match.group(1).strip()
                end_date = start_date_match.group(2).strip()
                params['start'] = f"{start_date}_{end_date}"
            
            # 完了日の範囲を抽出
            comp_date_match = re.search(
                r'AREA\[CompletionDate\]RANGE\[(.*?),(.*?)\]',
                advanced
            )
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
        
        # パラメータのエンコード
        encoded_params = urllib.parse.urlencode(
            params,
            quote_via=urllib.parse.quote
        )
        
        return base_url + encoded_params