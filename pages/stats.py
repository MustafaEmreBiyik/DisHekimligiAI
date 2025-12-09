"""
İstatistik Sayfası - Dental Tutor AI
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import sys

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.student_profile import init_student_profile, show_profile_card

# Initialize profile system
init_student_profile()

# Page config
st.set_page_config(
    page_title="Dental Tutor AI - İstatistikler",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }
    .metric-label {
        font-size: 1rem;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("📊 Performans İstatistikleri")
st.markdown("---")

# Initialize session state
if "action_history" not in st.session_state:
    st.session_state.action_history = []
if "total_score" not in st.session_state:
    st.session_state.total_score = 0
if "total_actions" not in st.session_state:
    st.session_state.total_actions = 0
if "completed_cases" not in st.session_state:
    st.session_state.completed_cases = set()

# Overview Metrics
st.markdown("## 🎯 Genel Bakış")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <p class="metric-value">{st.session_state.total_score}</p>
        <p class="metric-label">Toplam Puan</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
        <p class="metric-value">{st.session_state.total_actions}</p>
        <p class="metric-label">Toplam Eylem</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    avg_score = st.session_state.total_score / st.session_state.total_actions if st.session_state.total_actions > 0 else 0
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
        <p class="metric-value">{avg_score:.1f}</p>
        <p class="metric-label">Ortalama Puan/Eylem</p>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
        <p class="metric-value">{len(st.session_state.completed_cases)}</p>
        <p class="metric-label">Tamamlanan Vaka</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Action History
if st.session_state.action_history:
    st.markdown("## 📋 Son Eylemler")
    
    # Create DataFrame
    df = pd.DataFrame(st.session_state.action_history)
    
    # Display table
    st.dataframe(
        df[['timestamp', 'case_id', 'action', 'score', 'outcome']].tail(10),
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Puan Trendi")
        
        if len(df) > 0:
            df['cumulative_score'] = df['score'].cumsum()
            
            fig = px.line(
                df, 
                y='cumulative_score',
                title='Kümülatif Puan',
                labels={'cumulative_score': 'Toplam Puan', 'index': 'Eylem Sırası'}
            )
            fig.update_traces(line_color='#667eea', line_width=3)
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 🎯 Vaka Dağılımı")
        
        case_counts = df['case_id'].value_counts()
        
        fig = px.pie(
            values=case_counts.values,
            names=case_counts.index,
            title='Vaka Başına Eylem Sayısı'
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Score Distribution
    st.markdown("### 📊 Puan Dağılımı")
    
    fig = px.histogram(
        df, 
        x='score',
        nbins=20,
        title='Eylem Puanları Histogramı',
        labels={'score': 'Puan', 'count': 'Frekans'}
    )
    fig.update_traces(marker_color='#667eea')
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Performance by Action Type
    if 'action' in df.columns:
        st.markdown("### 🔍 Eylem Tipine Göre Performans")
        
        action_stats = df.groupby('action').agg({
            'score': ['count', 'sum', 'mean']
        }).round(2)
        action_stats.columns = ['Kullanım Sayısı', 'Toplam Puan', 'Ortalama Puan']
        action_stats = action_stats.sort_values('Toplam Puan', ascending=False)
        
        st.dataframe(action_stats, use_container_width=True)

else:
    st.info("📭 Henüz eylem geçmişi bulunmuyor. Vaka çalışmasına başlamak için chat sayfasına gidin!")
    
    if st.button("💬 Vaka Çalışmasına Başla", type="primary"):
        st.switch_page("pages/chat.py")

st.markdown("---")

# Back to Home
if st.button("🏠 Ana Sayfaya Dön", use_container_width=True):
    st.switch_page("Home.py")
