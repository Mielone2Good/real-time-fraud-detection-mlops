import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_manager import DataService, PostgresDataService

if "data_service" not in st.session_state:
    st.session_state.data_service = PostgresDataService()

def load_transactions(data_service: DataService):
    try:
        transactions = data_service.get_transactions()
        if not transactions:
            return pd.DataFrame()
        df = pd.DataFrame(transactions)
        if 'transaction_data' in df.columns and df['transaction_data'].dtype == 'object':
            import json
            df['transaction_data'] = df['transaction_data'].apply(lambda x: json.loads(x) if isinstance(x, str) else x)
        if 'timestamp' in df.columns and df['timestamp'].dtype == 'object':
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()


st.set_page_config(page_title="Credit-Card Fraud Detection Dashboard", layout="wide")
auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 1, 10, 2)

if st.sidebar.button("Clean Transactions Table"):
    st.session_state.data_service._clean_transactions_table()
    st.sidebar.write("Transactions table cleaned")

df = load_transactions(st.session_state.data_service)

if df.empty:
    st.warning("No transactions found")
else:
    st.title("Credit-Card Fraud Detection Dashboard")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    total = len(df)
    fraud = len(df[df['prediction'] == 1]) if 'prediction' in df.columns else 0
    fraud_rate = (fraud / total * 100) if total > 0 else 0
    
    if 'timestamp' in df.columns and len(df) > 1:
        time_diff = df['timestamp'].diff().dropna()
        avg_interval_seconds = time_diff.mean().total_seconds() if not time_diff.empty else 0
        tps = 1 / avg_interval_seconds if avg_interval_seconds > 0 else 0
    else:
        tps = 0
    
    col1.metric("Total Transactions", f"{total:,}")
    col2.metric("Fraud Detected", f"{fraud:,}", delta=f"{fraud_rate:.2f}%")
    col3.metric("Avg Probability", f"{df['probability'].mean():.3f}" if 'probability' in df.columns else "0.000")
    col4.metric("Transactions/sec", f"{tps:.2f}")
    col5.metric("Avg Processing Time", f"{df['processing_time'].mean():.2f} ms" if 'processing_time' in df.columns else "0.00 ms")
    col1, col2 = st.columns(2)
    
    with col1:
        if 'prediction' in df.columns:
            counts = df['prediction'].value_counts()
            fig = px.pie(values=counts.values, names=['No Fraud' if k == 0 else 'Fraud' for k in counts.index])
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'timestamp' in df.columns and not df['timestamp'].isna().all():
            df_time = df.groupby([df['timestamp'].dt.date, 'prediction']).size().reset_index(name='count')
            df_time['label'] = df_time['prediction'].map({0: 'No Fraud', 1: 'Fraud'})
            fig = px.line(df_time, x='timestamp', y='count', color='label')
            st.plotly_chart(fig, use_container_width=True)
    
    if 'probability' in df.columns:
        fig = px.histogram(df, x='probability', color='prediction', nbins=50)
        st.plotly_chart(fig, use_container_width=True)
    
    df_sorted = df.sort_values('timestamp', ascending=False) if 'timestamp' in df.columns else df
    cols = ['transaction_id', 'timestamp', 'prediction', 'probability', 'processing_time']
    available = [c for c in cols if c in df_sorted.columns]
    st.dataframe(df_sorted[available].head(100) if available else df_sorted.head(100), use_container_width=True, hide_index=True)

if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
