import streamlit as st

def initialize_session_state():
    """セッション状態の初期化を管理"""
    states = {
        'structured_studies': [],
        'selected_studies': [],
        'search_performed': False,
        'total_count': 0,
        'summary_generated': False,
        'criteria_analyzed': False,
        'publications_summarized': False,
        'comparison_analyzed': False,
        'analysis_complete': False
    }
    
    for key, default_value in states.items():
        if key not in st.session_state:
            st.session_state[key] = default_value