"""
Credit Portfolio Risk & Strategy Simulator - Streamlit Dashboard

This interactive dashboard provides comprehensive portfolio analysis including:
- Portfolio overview and key metrics
- Risk segmentation and monitoring
- Strategy simulation and optimization
- Early warning system for high-risk customers

Usage: streamlit run app/dashboard.py

Author: Credit Risk Analytics Team  
Date: 2024
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
import os
import sys
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Add the app directory to Python path for imports
app_dir = Path(__file__).parent
sys.path.append(str(app_dir))

try:
    from db_setup import CreditPortfolioDatabase
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    st.warning("Database module not available. Using CSV fallback.")

# Page configuration
st.set_page_config(
    page_title="Credit Portfolio Risk & Strategy Simulator",
    page_icon="chart_with_upwards_trend",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.8rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
    }
    .metric-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3498db;
        margin: 0.5rem 0;
    }
    .risk-high {
        background-color: #fee;
        border-left-color: #dc3545;
    }
    .risk-medium {
        background-color: #fff3cd;
        border-left-color: #ffc107;
    }
    .risk-low {
        background-color: #d4edda;
        border-left-color: #28a745;
    }
    .sidebar .element-container {
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_portfolio_data():
    """Load portfolio data with caching"""
    data_dir = Path(__file__).parent.parent / "data"
    
    try:
        # Primary data files
        portfolio_df = pd.read_csv(data_dir / "credit_portfolio.csv")
        
        # Optional risk metrics (if available)
        risk_file = data_dir / "portfolio_with_risk_metrics.csv"
        if risk_file.exists():
            risk_df = pd.read_csv(risk_file)
            portfolio_df = portfolio_df.merge(risk_df, on='customer_id', how='left')
        
        return portfolio_df
        
    except FileNotFoundError as e:
        st.error(f"Data file not found: {e}")
        return pd.DataFrame()

@st.cache_data  
def calculate_portfolio_metrics(df):
    """Calculate key portfolio metrics"""
    if df.empty:
        return {}
    
    approved_df = df[df['acceptance_decision'] == 'Approved']
    
    metrics = {
        'total_customers': len(df),
        'approved_customers': len(approved_df),
        'approval_rate': len(approved_df) / len(df) * 100 if len(df) > 0 else 0,
        'portfolio_balance': approved_df['balance'].sum(),
        'total_limits': approved_df['credit_limit'].sum(),
        'avg_utilization': approved_df['utilization_rate'].mean(),
        'avg_credit_score': approved_df['application_score'].mean(),
        'delinquency_rate': (approved_df['delinquency_status'] > 0).mean() * 100,
        'delinquent_customers': (approved_df['delinquency_status'] > 0).sum(),
        'high_risk_customers': len(approved_df[approved_df.get('risk_segment', '') == 'High Risk']) if 'risk_segment' in approved_df.columns else 0
    }
    
    return metrics

def create_portfolio_overview_charts(df, metrics):
    """Create portfolio overview visualizations"""
    approved_df = df[df['acceptance_decision'] == 'Approved']
    
    # Portfolio composition pie chart
    fig_composition = px.pie(
        values=[metrics['approved_customers'], metrics['total_customers'] - metrics['approved_customers']], 
        names=['Approved', 'Declined'],
        title="Portfolio Composition",
        color_discrete_map={'Approved': '#2ecc71', 'Declined': '#e74c3c'}
    )
    fig_composition.update_traces(textposition='inside', textinfo='percent+label')
    
    # Credit score distribution
    fig_score_dist = px.histogram(
        approved_df, 
        x='application_score',
        nbins=30,
        title="Credit Score Distribution (Approved Customers)",
        labels={'application_score': 'Application Score', 'count': 'Number of Customers'}
    )
    fig_score_dist.update_layout(bargap=0.1)
    
    # Balance distribution by income band
    if 'income_band' in approved_df.columns:
        balance_by_income = approved_df.groupby('income_band')['balance'].sum().reset_index()
        fig_income_balance = px.bar(
            balance_by_income,
            x='income_band', 
            y='balance',
            title="Portfolio Balance by Income Band",
            labels={'balance': 'Total Balance (£)', 'income_band': 'Income Band'}
        )
        fig_income_balance.update_traces(marker_color='#3498db')
    else:
        fig_income_balance = go.Figure().add_annotation(text="Income band data not available")
    
    # Regional distribution
    if 'region' in approved_df.columns:
        regional_counts = approved_df['region'].value_counts().head(10)
        fig_regional = px.bar(
            x=regional_counts.values,
            y=regional_counts.index,
            orientation='h',
            title="Top 10 Regions by Customer Count",
            labels={'x': 'Number of Customers', 'y': 'Region'}
        )
        fig_regional.update_traces(marker_color='#9b59b6')
    else:
        fig_regional = go.Figure().add_annotation(text="Regional data not available")
    
    return fig_composition, fig_score_dist, fig_income_balance, fig_regional

def create_risk_analysis_charts(df):
    """Create risk analysis visualizations"""
    approved_df = df[df['acceptance_decision'] == 'Approved']
    
    # Delinquency status distribution
    delinq_counts = approved_df['delinquency_status'].value_counts().sort_index()
    delinq_labels = ['Current', '30 DPD', '60 DPD', '90+ DPD'][:len(delinq_counts)]
    
    fig_delinq_dist = px.bar(
        x=delinq_labels,
        y=delinq_counts.values,
        title="Delinquency Status Distribution",
        labels={'x': 'Delinquency Status', 'y': 'Number of Customers'},
        color=delinq_counts.values,
        color_continuous_scale='Reds'
    )
    
    # Risk by credit score bands
    approved_df['score_band'] = pd.cut(
        approved_df['application_score'], 
        bins=[0, 500, 600, 650, 700, 750, 900],
        labels=['<500', '500-599', '600-649', '650-699', '700-749', '750+']
    )
    
    risk_by_score = approved_df.groupby('score_band', observed=True).agg({
        'customer_id': 'count',
        'delinquency_status': lambda x: (x > 0).mean() * 100
    }).reset_index()
    risk_by_score.columns = ['score_band', 'customers', 'delinquency_rate']
    
    fig_risk_score = px.bar(
        risk_by_score,
        x='score_band',
        y='delinquency_rate', 
        title="Delinquency Rate by Credit Score Band",
        labels={'delinquency_rate': 'Delinquency Rate (%)', 'score_band': 'Credit Score Band'},
        text='delinquency_rate'
    )
    fig_risk_score.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    
    # Utilization vs Risk scatter plot
    fig_util_risk = px.scatter(
        approved_df.sample(min(1000, len(approved_df))),  # Sample for performance
        x='utilization_rate',
        y='application_score',
        color='delinquency_status',
        title="Utilization vs Credit Score (Risk Analysis)",
        labels={'utilization_rate': 'Utilization Rate (%)', 'application_score': 'Credit Score'},
        color_continuous_scale='RdYlBu_r'
    )
    
    return fig_delinq_dist, fig_risk_score, fig_util_risk

def create_strategy_simulation():
    """Create strategy simulation interface"""
    st.markdown('<div class="section-header">Strategy Simulator</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Credit Policy Parameters")
        min_score = st.slider("Minimum Credit Score", 400, 800, 500, 25)
        limit_multiplier = st.slider("Credit Limit Multiplier", 0.5, 2.0, 1.0, 0.1)
        
    with col2:
        st.subheader("Target Segments")
        income_targets = st.multiselect(
            "Target Income Bands",
            options=['Low', 'Medium', 'High'],
            default=['Low', 'Medium', 'High']
        )
        
    # Simulate strategy impact
    if st.button("Simulate Strategy Impact", type="primary"):
        df = load_portfolio_data()
        if not df.empty:
            baseline_metrics = calculate_portfolio_metrics(df)
            
            # Apply strategy filters
            strategy_df = df.copy()
            eligible_mask = (
                (strategy_df['application_score'] >= min_score) &
                (strategy_df['income_band'].isin(income_targets))
            )
            strategy_df.loc[~eligible_mask, 'acceptance_decision'] = 'Declined'
            
            # Calculate new metrics
            strategy_metrics = calculate_portfolio_metrics(strategy_df)
            
            # Display comparison
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                approval_change = strategy_metrics['approval_rate'] - baseline_metrics['approval_rate']
                st.metric(
                    "Approval Rate", 
                    f"{strategy_metrics['approval_rate']:.1f}%",
                    f"{approval_change:+.1f}%"
                )
                
            with col2:
                balance_change = (strategy_metrics['portfolio_balance'] - baseline_metrics['portfolio_balance']) / baseline_metrics['portfolio_balance'] * 100
                st.metric(
                    "Portfolio Balance", 
                    f"£{strategy_metrics['portfolio_balance']/1e6:.1f}M",
                    f"{balance_change:+.1f}%"
                )
                
            with col3:
                delinq_change = strategy_metrics['delinquency_rate'] - baseline_metrics['delinquency_rate']
                st.metric(
                    "Delinquency Rate",
                    f"{strategy_metrics['delinquency_rate']:.1f}%", 
                    f"{delinq_change:+.1f}%"
                )
                
            with col4:
                score_change = strategy_metrics['avg_credit_score'] - baseline_metrics['avg_credit_score']
                st.metric(
                    "Avg Credit Score",
                    f"{strategy_metrics['avg_credit_score']:.0f}",
                    f"{score_change:+.0f}"
                )
            
            # Strategy impact visualization
            comparison_data = {
                'Metric': ['Customers', 'Portfolio Balance (£M)', 'Delinquency Rate (%)'],
                'Current': [
                    baseline_metrics['approved_customers'],
                    baseline_metrics['portfolio_balance'] / 1e6,
                    baseline_metrics['delinquency_rate']
                ],
                'Strategy': [
                    strategy_metrics['approved_customers'], 
                    strategy_metrics['portfolio_balance'] / 1e6,
                    strategy_metrics['delinquency_rate']
                ]
            }
            
            comparison_df = pd.DataFrame(comparison_data)
            fig_strategy = px.bar(
                comparison_df.melt(id_vars='Metric', var_name='Scenario', value_name='Value'),
                x='Metric',
                y='Value', 
                color='Scenario',
                barmode='group',
                title="Strategy Impact Comparison"
            )
            st.plotly_chart(fig_strategy, use_container_width=True)

def main():
    """Main dashboard application"""
    st.markdown('<div class="main-header">Credit Portfolio Risk & Strategy Simulator</div>', unsafe_allow_html=True)
    
    # Sidebar navigation
    st.sidebar.image("https://via.placeholder.com/200x80/3498db/white?text=NEXT+CREDIT", width=200)
    st.sidebar.title("Navigation")
    
    page = st.sidebar.selectbox(
        "Select Analysis",
        [
            "Portfolio Overview", 
            "Risk Analysis",
            "Strategy Simulator",
            "High-Risk Customers",
            "Performance Trends"
        ]
    )
    
    # Load data
    with st.spinner("Loading portfolio data..."):
        df = load_portfolio_data()
        
    if df.empty:
        st.error("❌ Unable to load portfolio data. Please check data files.")
        st.stop()
        
    metrics = calculate_portfolio_metrics(df)
    
    # Sidebar metrics
    st.sidebar.markdown("### Key Metrics")
    st.sidebar.metric("Total Customers", f"{metrics['total_customers']:,}")
    st.sidebar.metric("Portfolio Balance", f"£{metrics['portfolio_balance']/1e6:.1f}M")
    st.sidebar.metric("Approval Rate", f"{metrics['approval_rate']:.1f}%")
    st.sidebar.metric("Delinquency Rate", f"{metrics['delinquency_rate']:.1f}%")
    
    # Main content based on page selection
    if page == "Portfolio Overview":
        st.markdown('<div class="section-header">Portfolio Overview</div>', unsafe_allow_html=True)
        
        # Key metrics row
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Total Customers", 
                f"{metrics['total_customers']:,}"
            )
            
        with col2:
            st.metric(
                "Portfolio Balance",
                f"£{metrics['portfolio_balance']/1e6:.1f}M"
            )
            
        with col3:
            st.metric(
                "Avg Credit Score", 
                f"{metrics['avg_credit_score']:.0f}"
            )
            
        with col4:
            st.metric(
                "Utilization Rate",
                f"{metrics['avg_utilization']:.1f}%"
            )
            
        with col5:
            st.metric(
                "Delinquency Rate",
                f"{metrics['delinquency_rate']:.1f}%"
            )
        
        # Charts
        st.markdown("### Portfolio Analysis")
        fig_comp, fig_score, fig_income, fig_regional = create_portfolio_overview_charts(df, metrics)
        
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig_comp, use_container_width=True)
            st.plotly_chart(fig_income, use_container_width=True)
            
        with col2:
            st.plotly_chart(fig_score, use_container_width=True)
            st.plotly_chart(fig_regional, use_container_width=True)
            
    elif page == "Risk Analysis":
        st.markdown('<div class="section-header">Risk Analysis</div>', unsafe_allow_html=True)
        
        # Risk metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="metric-container risk-high">', unsafe_allow_html=True)
            st.metric("Delinquent Customers", f"{metrics['delinquent_customers']:,}")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col2:
            st.markdown('<div class="metric-container risk-medium">', unsafe_allow_html=True)
            st.metric("High Risk Customers", f"{metrics['high_risk_customers']:,}")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col3:
            st.markdown('<div class="metric-container risk-low">', unsafe_allow_html=True)
            current_customers = metrics['approved_customers'] - metrics['delinquent_customers']
            st.metric("Current Customers", f"{current_customers:,}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Risk analysis charts
        fig_delinq, fig_risk_score, fig_util_risk = create_risk_analysis_charts(df)
        
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig_delinq, use_container_width=True)
            st.plotly_chart(fig_util_risk, use_container_width=True)
            
        with col2:
            st.plotly_chart(fig_risk_score, use_container_width=True)
            
            # Risk concentration table
            approved_df = df[df['acceptance_decision'] == 'Approved']
            if 'region' in approved_df.columns:
                risk_by_region = approved_df.groupby('region').agg({
                    'customer_id': 'count',
                    'balance': 'sum',
                    'delinquency_status': lambda x: (x > 0).mean() * 100
                }).round(2)
                risk_by_region.columns = ['Customers', 'Balance (£)', 'Delinq Rate (%)']
                risk_by_region['Balance (£M)'] = (risk_by_region['Balance (£)'] / 1e6).round(1)
                
                st.subheader("Risk by Region")
                st.dataframe(
                    risk_by_region[['Customers', 'Balance (£M)', 'Delinq Rate (%)']].sort_values('Delinq Rate (%)', ascending=False),
                    use_container_width=True
                )
                
    elif page == "Strategy Simulator":
        create_strategy_simulation()
        
    elif page == "High-Risk Customers":
        st.markdown('<div class="section-header">High-Risk Customer Alert System</div>', unsafe_allow_html=True)
        
        approved_df = df[df['acceptance_decision'] == 'Approved']
        
        # High-risk filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            min_balance = st.number_input("Minimum Balance (£)", 0, 50000, 1000)
        with col2:
            max_score = st.number_input("Maximum Credit Score", 300, 900, 650)
        with col3:
            min_utilization = st.number_input("Minimum Utilization (%)", 0, 100, 50)
        
        # Filter high-risk customers
        high_risk_df = approved_df[
            (approved_df['balance'] >= min_balance) &
            (approved_df['application_score'] <= max_score) &
            (approved_df['utilization_rate'] >= min_utilization)
        ].copy()
        
        if 'risk_score' in high_risk_df.columns:
            high_risk_df = high_risk_df.sort_values('risk_score', ascending=False)
        else:
            high_risk_df = high_risk_df.sort_values(['delinquency_status', 'utilization_rate'], ascending=[False, False])
        
        st.markdown(f"### {len(high_risk_df)} High-Risk Customers Identified")
        
        if len(high_risk_df) > 0:
            # Display top high-risk customers
            display_cols = ['customer_id', 'application_score', 'credit_limit', 'balance', 'utilization_rate', 'delinquency_status']
            if 'region' in high_risk_df.columns:
                display_cols.append('region')
            if 'income_band' in high_risk_df.columns:
                display_cols.append('income_band')
            if 'risk_score' in high_risk_df.columns:
                display_cols.append('risk_score')
                
            st.dataframe(
                high_risk_df[display_cols].head(20),
                use_container_width=True
            )
            
            # Action recommendations
            st.markdown("### Recommended Actions")
            
            delinquent_count = (high_risk_df['delinquency_status'] > 0).sum()
            high_util_count = (high_risk_df['utilization_rate'] > 80).sum()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Immediate Actions:**")
                st.markdown(f"• Review {delinquent_count} delinquent accounts")
                st.markdown(f"• Reduce limits for {high_util_count} high-utilization accounts")
                st.markdown("• Initiate collection procedures")
                
            with col2:
                st.markdown("**Preventive Actions:**")
                st.markdown("• Send risk alerts to account managers")
                st.markdown("• Implement payment reminders")
                st.markdown("• Consider credit limit reductions")
        
    elif page == "Performance Trends":
        st.markdown('<div class="section-header">Portfolio Performance Trends</div>', unsafe_allow_html=True)
        
        # Try to load trend data
        data_dir = Path(__file__).parent.parent / "data"
        trend_file = data_dir / "portfolio_trends_simulation.csv"
        
        if trend_file.exists():
            trends_df = pd.read_csv(trend_file)
            
            # Create trend charts
            fig_trends = make_subplots(
                rows=2, cols=2,
                subplot_titles=("Delinquency Rate Trend", "Portfolio Balance Trend", 
                               "Expected Loss Trend", "High-Risk Customer Count"),
                specs=[[{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            # Delinquency rate trend
            fig_trends.add_trace(
                go.Scatter(x=trends_df['month'], y=trends_df['delinquency_rate'],
                          mode='lines+markers', name='Delinquency Rate', line=dict(color='red')),
                row=1, col=1
            )
            
            # Portfolio balance trend
            fig_trends.add_trace(
                go.Scatter(x=trends_df['month'], y=trends_df['total_balance']/1e6,
                          mode='lines+markers', name='Portfolio Balance (£M)', line=dict(color='blue')),
                row=1, col=2
            )
            
            # Expected loss trend
            if 'expected_loss' in trends_df.columns:
                fig_trends.add_trace(
                    go.Scatter(x=trends_df['month'], y=trends_df['expected_loss']/1000,
                              mode='lines+markers', name='Expected Loss (£000s)', line=dict(color='orange')),
                    row=2, col=1
                )
            
            # High-risk customer trend
            if 'high_risk_customers' in trends_df.columns:
                fig_trends.add_trace(
                    go.Scatter(x=trends_df['month'], y=trends_df['high_risk_customers'],
                              mode='lines+markers', name='High Risk Customers', line=dict(color='purple')),
                    row=2, col=2
                )
            
            fig_trends.update_layout(height=600, showlegend=False, title_text="12-Month Portfolio Trends")
            st.plotly_chart(fig_trends, use_container_width=True)
            
            # Trend insights
            st.markdown("### Key Insights")
            
            delinq_start = trends_df['delinquency_rate'].iloc[0]
            delinq_end = trends_df['delinquency_rate'].iloc[-1]
            delinq_change = delinq_end - delinq_start
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Delinquency Trend", f"{delinq_end:.1f}%", f"{delinq_change:+.1f}%")
                
            with col2:
                balance_start = trends_df['total_balance'].iloc[0]
                balance_end = trends_df['total_balance'].iloc[-1]
                balance_change = (balance_end - balance_start) / balance_start * 100
                st.metric("Portfolio Growth", f"£{balance_end/1e6:.1f}M", f"{balance_change:+.1f}%")
                
            with col3:
                avg_customers = trends_df['total_customers'].mean()
                st.metric("Avg Customers", f"{avg_customers:,.0f}")
                
        else:
            st.info("Trend data not available. Run the risk analysis notebook to generate trend simulations.")
            
            # Show static portfolio breakdown instead
            approved_df = df[df['acceptance_decision'] == 'Approved']
            
            if 'income_band' in approved_df.columns:
                income_trends = approved_df.groupby('income_band').agg({
                    'customer_id': 'count',
                    'balance': 'sum',
                    'utilization_rate': 'mean',
                    'delinquency_status': lambda x: (x > 0).mean() * 100
                }).round(2)
                
                st.subheader("Portfolio Performance by Segment")
                st.dataframe(income_trends, use_container_width=True)

if __name__ == "__main__":
    main()