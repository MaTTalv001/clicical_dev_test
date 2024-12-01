# utils/visualizer.py
"""
このモジュールは、臨床試験データの視覚化機能を提供します。
matplotlib.pyplotとpandasを使用して、薬剤分布や評価項目の分布を
円グラフとして表示します。

主な機能：
- 介入（薬剤）の分布の可視化
- アウトカム（評価項目）の分布の可視化
"""
import matplotlib.pyplot as plt
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import random
from collections import Counter
from utils.prompts import (CRITERIA_PROMPT,COMPREHENSIVE_SUMMARY_PROMPT)

import boto3
from langchain_community.chat_models import BedrockChat
# 主要コンポーネントの初期化
bedrock = boto3.client('bedrock-runtime')
llm = BedrockChat(model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", client=bedrock)


class Visualizer:
    """
    臨床試験データの視覚化を行うクラス
    すべてのメソッドはstaticmethodとして実装され、
    インスタンス化せずに使用できます。
    """
    @staticmethod
    def plot_drug_distribution(interventions):
        """
        薬剤の分布を横向きの棒グラフで表示する

        Args:
            interventions (list): [薬剤名, 出現回数]のリスト

        Returns:
            tuple: (plotly.graph_objects.Figure, pandas.DataFrame)
                - 生成された棒グラフ
                - 薬剤の分布データを含むDataFrame
        """
        # DataFrameを作成し、出現回数で降順ソート
        drug_df = pd.DataFrame(interventions, columns=['Drug', 'Count']).sort_values('Count', ascending=True)
        
        # 割合を計算
        total = drug_df['Count'].sum()
        drug_df['Percentage'] = (drug_df['Count'] / total * 100).round(1)
        
        # Plotlyで横向きの棒グラフを作成
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=drug_df['Drug'],
            x=drug_df['Count'],
            orientation='h',
            text=[f'{count} ({pct}%)' for count, pct in zip(drug_df['Count'], drug_df['Percentage'])],
            textposition='auto',
            marker_color='rgb(55, 83, 109)',
            hovertemplate='<b>%{y}</b><br>' +
                        '件数: %{x}<br>' +
                        '割合: %{text}<br>' +
                        '<extra></extra>'
        ))
        
        # レイアウトの設定
        fig.update_layout(
            title={
                'text': '評価対象医薬品の分布',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            xaxis_title="臨床試験数",
            showlegend=False,
            height=max(400, len(drug_df) * 30),  # グラフの高さを動的に調整
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
        )
        
        # 軸の設定
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
        fig.update_yaxes(showgrid=False)
        
        return fig, drug_df

    @staticmethod
    def plot_outcome_distribution(outcomes):
        """
        主要評価項目の分布を横向きの棒グラフで表示する

        Args:
            outcomes (list): [評価項目名, 出現回数]のリスト

        Returns:
            tuple: (plotly.graph_objects.Figure, pandas.DataFrame)
                - 生成された棒グラフ
                - 評価項目の分布データを含むDataFrame
        """
        # DataFrameを作成し、出現回数で降順ソート
        outcome_df = pd.DataFrame(outcomes, columns=['Outcome', 'Count']).sort_values('Count', ascending=True)
        
        # 割合を計算
        total = outcome_df['Count'].sum()
        outcome_df['Percentage'] = (outcome_df['Count'] / total * 100).round(1)
        
        # Plotlyで横向きの棒グラフを作成
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=outcome_df['Outcome'],
            x=outcome_df['Count'],
            orientation='h',
            text=[f'{count} ({pct}%)' for count, pct in zip(outcome_df['Count'], outcome_df['Percentage'])],
            textposition='auto',
            marker_color='rgb(55, 126, 184)',  # 医薬品分布とは異なる色を使用
            hovertemplate='<b>%{y}</b><br>' +
                            '件数: %{x}<br>' +
                            '割合: %{text}<br>' +
                            '<extra></extra>'
        ))
        
        # レイアウトの設定
        fig.update_layout(
            title={
                'text': '主要評価項目の分布',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            xaxis_title="臨床試験数",
            showlegend=False,
            height=max(400, len(outcome_df) * 30),  # グラフの高さを動的に調整
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
        )
        
        # 軸の設定
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
        fig.update_yaxes(showgrid=False)
        
        return fig, outcome_df
    
    @staticmethod
    def visualize_distributions(studies):
        """薬剤と評価項目の分布を可視化"""
        st.subheader("1. 試験の基本特性")
        
        # 介入データの収集と集計
        interventions = []
        primary_outcomes = []
        
        for study in studies:
            # 介入の収集
            if 'interventions' in study:
                for intervention in study['interventions']:
                    if 'name' in intervention:
                        interventions.append(intervention['name'])
            
            # 主要評価項目の収集
            if 'outcomes' in study and 'primary' in study['outcomes']:
                primary_outcomes.extend(study['outcomes']['primary'])
        
        # 介入の集計
        intervention_counts = Counter(interventions)
        top_interventions = intervention_counts.most_common(5)
        
        # 主要評価項目の集計
        outcome_counts = Counter(primary_outcomes)
        top_primary_outcomes = outcome_counts.most_common(5)
        
        # 薬剤の分布
        st.subheader("評価対象医薬品の分布")
        fig1, drug_df = Visualizer.plot_drug_distribution(top_interventions)
        st.plotly_chart(fig1, use_container_width=True)
        st.table(drug_df)

        # 評価項目の分布
        st.subheader("主要評価項目の分布")
        fig2, outcome_df = Visualizer.plot_outcome_distribution(top_primary_outcomes)
        st.plotly_chart(fig2, use_container_width=True)
        st.table(outcome_df)
        
        return top_interventions, top_primary_outcomes
