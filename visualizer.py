import matplotlib.pyplot as plt
import pandas as pd

class Visualizer:
    @staticmethod
    def plot_drug_distribution(interventions):
        drug_df = pd.DataFrame(interventions, columns=['Drug', 'Count']).sort_values('Count', ascending=False)
        fig, ax = plt.subplots()
        ax.pie(drug_df['Count'], labels=drug_df['Drug'], autopct='%1.1f%%')
        ax.axis('equal')
        return fig, drug_df

    @staticmethod
    def plot_outcome_distribution(outcomes):
        outcome_df = pd.DataFrame(outcomes, columns=['Outcome', 'Count']).sort_values('Count', ascending=False)
        fig, ax = plt.subplots()
        ax.pie(outcome_df['Count'], labels=outcome_df['Outcome'], autopct='%1.1f%%')
        ax.axis('equal')
        return fig, outcome_df