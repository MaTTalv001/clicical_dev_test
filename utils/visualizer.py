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
import pandas as pd

class Visualizer:
    """
    臨床試験データの視覚化を行うクラス
    すべてのメソッドはstaticmethodとして実装され、
    インスタンス化せずに使用できます。
    """
    @staticmethod
    def plot_drug_distribution(interventions):
        """
        薬剤の分布を円グラフで表示する

        Args:
            interventions (list): [薬剤名, 出現回数]のリスト

        Returns:
            tuple: (matplotlib.figure.Figure, pandas.DataFrame)
                - 生成された円グラフ
                - 薬剤の分布データを含むDataFrame
        """
        drug_df = pd.DataFrame(interventions, columns=['Drug', 'Count']).sort_values('Count', ascending=False)
        fig, ax = plt.subplots()
        ax.pie(drug_df['Count'], labels=drug_df['Drug'], autopct='%1.1f%%')
        ax.axis('equal')
        return fig, drug_df

    @staticmethod
    def plot_outcome_distribution(outcomes):
        """
        評価項目の分布を円グラフで表示する

        Args:
            outcomes (list): [評価項目名, 出現回数]のリスト
            
        Returns:
            tuple: (matplotlib.figure.Figure, pandas.DataFrame)
                - 生成された円グラフ
                - 評価項目の分布データを含むDataFrame
        """
        outcome_df = pd.DataFrame(outcomes, columns=['Outcome', 'Count']).sort_values('Count', ascending=False)
        fig, ax = plt.subplots()
        ax.pie(outcome_df['Count'], labels=outcome_df['Outcome'], autopct='%1.1f%%')
        ax.axis('equal')
        return fig, outcome_df