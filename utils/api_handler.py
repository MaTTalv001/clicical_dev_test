# utils/api_handler.py
"""
このモジュールは、臨床試験データをClinicalTrials.govのAPIから効率的に取得し、アプリケーションで扱いやすい形式に
変換することを目的としています。

主な機能：
- 外部APIからの臨床試験データの取得
- 取得したデータの構造化
- ページネーション処理による大量データの効率的な取得

fetch_studies関数では、指定されたAPIエンドポイントに対してリクエストを送信し、
ページネーションを使用して全ての該当データを取得します。nextPageTokenを使用して
次のページが存在する限り、データの取得を継続します。

structure_data関数では、APIから取得した生データを、アプリケーション内で扱いやすい
一貫した形式に変換します。utils.pyで定義されたstructure_clinical_trial関数を
使用して、各試験データを構造化します。

fetch_and_structure_studies関数は、上記の2つの機能を組み合わせた高レベルな
インターフェースを提供し、データの取得から構造化までを一括で行います。
"""

import requests
import re
import urllib.parse
import streamlit as st
from utils.utils import structure_clinical_trial

class APIHandler:
    """
    臨床試験データのAPI操作を担当するクラス
    外部APIとの通信、データの取得、構造化を処理する
    """
    def __init__(self, api_url):
        self.api_url = api_url

    def fetch_studies(self, params):
        """
        APIから臨床試験データを取得する
        """
        # filter.overallStatusがリストの場合、カンマ区切りの文字列に変換
        if 'filter.overallStatus' in params:
            if isinstance(params['filter.overallStatus'], list):
                params['filter.overallStatus'] = ','.join(params['filter.overallStatus'])
            elif isinstance(params['filter.overallStatus'], str):
                # 既に文字列の場合はそのまま
                pass

        all_studies = []
        total_count = 0

        # デバッグ
        st.write(params)

        while True:
            response = requests.get(self.api_url, params=params)

            if response.status_code != 200:
                raise Exception(f"API Error: {response.status_code}\n{response.text}")

            data = response.json()

            if 'studies' in data:
                all_studies.extend(data['studies'])

            if 'totalCount' in data:
                total_count = data['totalCount']

            if 'nextPageToken' in data:
                params['pageToken'] = data['nextPageToken']
            else:
                break

        return all_studies, total_count

    def structure_data(self, studies):
        """
        取得した生データを構造化された形式に変換
        
        Args:
            studies (list): 生の臨床試験データのリスト
        
        Returns:
            list: 構造化された臨床試験データのリスト
        """
        return [structure_clinical_trial(study) for study in studies if study is not None]

    def fetch_and_structure_studies(self, query_params):
        """
        データの取得と構造化を一括で行うメインメソッド
        
        Args:
            query_params (dict): 検索条件などのクエリパラメータ
        
        Returns:
            tuple: (構造化されたデータのリスト, 総件数)
        """
        params = {
            'format': 'json',
            'pageSize': 100,  # 1ページあたりの結果数
            'countTotal': 'true',  # 総結果数を取得
        }
        params.update(query_params)

        studies, total_count = self.fetch_studies(params)
        structured_studies = self.structure_data(studies)

        return structured_studies, total_count