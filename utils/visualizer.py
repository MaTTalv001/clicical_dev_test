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
        # DataFrameを作成し、Drugカラムを大文字に変換した上で出現回数で降順ソート
        drug_df = pd.DataFrame(interventions, columns=['Drug', 'Count'])
        drug_df['Drug'] = drug_df['Drug'].str.upper()  # Drugカラムを大文字に変換
        # 同じ薬剤名でグループ化して集計
        drug_df = drug_df.groupby('Drug')['Count'].sum().reset_index()
        drug_df = drug_df.sort_values('Count', ascending=True)
        
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
    def truncate_text(text, max_length=80):
        """
        文字列を指定の長さで切り詰め、省略記号を追加する
        
        Args:
            text (str): 元の文字列
            max_length (int): 最大文字数 (デフォルト: 80)
        
        Returns:
            str: 切り詰められた文字列
        """
        if len(text) > max_length:
            return text[:max_length] + '...'
        return text
    
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
        # DataFrameを作成し、Outcomeカラムを大文字に変換した上で出現回数で降順ソート
        outcome_df = pd.DataFrame(outcomes, columns=['Outcome', 'Count'])
        outcome_df['Outcome'] = outcome_df['Outcome'].str.upper()  # Outcomeカラムを大文字に変換
        # 同じ評価項目でグループ化して集計
        outcome_df = outcome_df.groupby('Outcome')['Count'].sum().reset_index()
        outcome_df = outcome_df.sort_values('Count', ascending=True)
        
        # 短縮版のOutcomeカラムを追加
        outcome_df['Outcome_Short'] = outcome_df['Outcome'].apply(lambda x: Visualizer.truncate_text(x))
        outcome_df = outcome_df.sort_values('Count', ascending=True)
        
        # 割合を計算
        total = outcome_df['Count'].sum()
        outcome_df['Percentage'] = (outcome_df['Count'] / total * 100).round(1)
        
        # Plotlyで横向きの棒グラフを作成
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=outcome_df['Outcome_Short'],  # 短縮版を表示用に使用
            x=outcome_df['Count'],
            orientation='h',
            text=[f'{count} ({pct}%)' for count, pct in zip(outcome_df['Count'], outcome_df['Percentage'])],
            textposition='auto',
            marker_color='rgb(55, 126, 184)',  # 医薬品分布とは異なる色を使用
            hovertemplate='<b>完全な評価項目名:</b><br>%{customdata}<br>' +
                            '件数: %{x}<br>' +
                            '割合: %{text}<br>' +
                            '<extra></extra>',
            customdata=outcome_df['Outcome']  # ホバー時に完全な文字列を表示
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
            # y軸のテキスト設定を追加
            yaxis=dict(
                tickmode='array',
                ticktext=outcome_df['Outcome_Short'],
                tickvals=list(range(len(outcome_df))),
                tickfont=dict(size=11),  # フォントサイズの調整
            )
        )
        
        # 軸の設定
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
        fig.update_yaxes(showgrid=False)
        
        # 表示用のDataFrameからOutcome_Shortを削除
        outcome_df = outcome_df.drop('Outcome_Short', axis=1)
        
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
        st.dataframe(drug_df, hide_index=True)

        # 評価項目の分布
        st.subheader("主要評価項目の分布")
        fig2, outcome_df = Visualizer.plot_outcome_distribution(top_primary_outcomes)
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(outcome_df, hide_index=True)
        
        return top_interventions, top_primary_outcomes
    
    @staticmethod
    def plot_age_distribution(age_df):
        """
        年齢条件の分布を横向きの棒グラフで表示する

        Args:
            age_df (pandas.DataFrame): 年齢条件の分布データ

        Returns:
            plotly.graph_objects.Figure: 生成された棒グラフ
        """
        age_df_sorted = age_df.sort_values('件数', ascending=True)  # グラフ表示用に昇順（表示は下から上に向かって降順になる）
    
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=age_df_sorted['年齢条件'],
            x=age_df_sorted['件数'],
            orientation='h',
            text=[f'{count} ({pct}%)' for count, pct in zip(age_df_sorted['件数'], age_df_sorted['割合(%)'])],
            textposition='auto',
            marker_color='rgb(158, 202, 225)',
            hovertemplate='<b>%{y}</b><br>' +
                        '件数: %{x}<br>' +
                        '割合: %{text}<br>' +
                        '<extra></extra>'
        ))
        
        fig.update_layout(
            title={
                'text': '年齢条件の分布（上位10パターン）',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            xaxis_title="臨床試験数",
            showlegend=False,
            height=max(400, len(age_df) * 30),
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
        )
        
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
        fig.update_yaxes(showgrid=False)
        
        return fig

    @staticmethod
    def plot_gender_distribution(gender_df):
        """
        性別条件の分布を円グラフで表示する

        Args:
            gender_df (pandas.DataFrame): 性別条件の分布データ

        Returns:
            plotly.graph_objects.Figure: 生成された円グラフ
        """
        fig = go.Figure(data=[go.Pie(
            labels=gender_df['性別条件'],
            values=gender_df['件数'],
            text=gender_df['割合(%)'].apply(lambda x: f'{x:.1f}%'),
            hovertemplate="<b>%{label}</b><br>" +
                        "件数: %{value}<br>" +
                        "割合: %{text}<br>" +
                        "<extra></extra>"
        )])
        
        fig.update_layout(
            title={
                'text': '性別条件の分布',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            showlegend=True,
            height=400,
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        return fig
