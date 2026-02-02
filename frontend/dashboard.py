"""
IoT Data Lake - Streamlit Dashboard
Interactive visualization of IoT data storage system
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
import time
from datetime import datetime
import json

# Configuration
API_BASE = "http://localhost:8000"
REFRESH_INTERVAL = 2  # seconds

# Page configuration
st.set_page_config(
    page_title="IoT Data Lake Intelligent",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme and modern look
st.markdown("""
<style>
    /* Main theme */
    .stApp {
        background: linear-gradient(180deg, #0f0f23 0%, #1a1a3e 100%);
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #00d4ff !important;
        font-family: 'Segoe UI', sans-serif;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #1e1e3f 0%, #2d2d5a 100%);
        border-radius: 15px;
        padding: 20px;
        border: 1px solid rgba(0, 212, 255, 0.2);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        margin: 10px 0;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #00d4ff;
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #a0a0c0;
        margin: 0;
    }
    
    /* Tier badges */
    .tier-hot {
        background: linear-gradient(135deg, #ff4444 0%, #ff6b6b 100%);
        padding: 5px 15px;
        border-radius: 20px;
        color: white;
        font-weight: bold;
    }
    
    .tier-warm {
        background: linear-gradient(135deg, #ffaa00 0%, #ffcc44 100%);
        padding: 5px 15px;
        border-radius: 20px;
        color: #333;
        font-weight: bold;
    }
    
    .tier-cold {
        background: linear-gradient(135deg, #0088ff 0%, #00aaff 100%);
        padding: 5px 15px;
        border-radius: 20px;
        color: white;
        font-weight: bold;
    }
    
    /* Anomaly indicator */
    .anomaly-badge {
        background: #ff0055;
        color: white;
        padding: 3px 10px;
        border-radius: 10px;
        font-size: 0.8rem;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: #1a1a3e;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #00d4ff 0%, #0088ff 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 25px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(0, 212, 255, 0.4);
    }
</style>
""", unsafe_allow_html=True)


def check_api_available():
    """Check if API is running"""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def generate_data(count: int, include_anomalies: bool, anomaly_rate: float):
    """Generate and store sensor data"""
    try:
        response = requests.post(
            f"{API_BASE}/data/store",
            json={
                "count": count,
                "include_anomalies": include_anomalies,
                "anomaly_rate": anomaly_rate
            },
            timeout=10
        )
        return response.json()
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_metrics():
    """Get storage metrics"""
    try:
        response = requests.get(f"{API_BASE}/metrics", timeout=5)
        return response.json()
    except:
        return None


def get_recent_data(limit: int = 50):
    """Get recent data"""
    try:
        response = requests.get(f"{API_BASE}/data/recent?limit={limit}", timeout=5)
        return response.json()
    except:
        return None


def get_feature_importance():
    """Get ML feature importance"""
    try:
        response = requests.get(f"{API_BASE}/ml/feature-importance", timeout=5)
        return response.json()
    except:
        return None


def render_metric_card(label: str, value: any, color: str = "#00d4ff"):
    """Render a styled metric card"""
    return f"""
    <div class="metric-card">
        <p class="metric-value" style="color: {color};">{value}</p>
        <p class="metric-label">{label}</p>
    </div>
    """


def main():
    # Header
    st.markdown("""
    <div style="text-align: center; padding: 20px;">
        <h1 style="font-size: 3rem; margin-bottom: 0;">🌐 IoT Data Lake Intelligent</h1>
        <p style="color: #a0a0c0; font-size: 1.2rem;">
            Système de stockage intelligent avec classification ML
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check API availability
    api_available = check_api_available()
    
    if not api_available:
        st.error("""
        ⚠️ **API non disponible**
        
        Veuillez lancer le backend en premier:
        ```bash
        cd IoT-DataLake-Project
        python -m uvicorn backend.main:app --reload
        ```
        """)
        
        # Show demo mode
        st.info("🎭 Mode Démo - Données simulées affichées")
        demo_mode = True
    else:
        st.success("✅ API connectée")
        demo_mode = False
    
    # Sidebar controls
    with st.sidebar:
        st.markdown("## ⚙️ Contrôles")
        
        st.markdown("### Génération de données")
        count = st.slider("Nombre de lectures", 1, 100, 20)
        include_anomalies = st.checkbox("Inclure anomalies", True)
        anomaly_rate = st.slider("Taux d'anomalies", 0.0, 0.5, 0.1)
        
        if st.button("🚀 Générer & Stocker", use_container_width=True):
            if not demo_mode:
                with st.spinner("Génération en cours..."):
                    result = generate_data(count, include_anomalies, anomaly_rate)
                    if result.get("success"):
                        st.success(f"✅ {result['data']['total_processed']} lectures traitées!")
                        st.rerun()
                    else:
                        st.error(f"Erreur: {result.get('message')}")
            else:
                st.warning("API non disponible - Mode démo")
        
        st.markdown("---")
        
        auto_refresh = st.checkbox("🔄 Auto-refresh", False)
        if auto_refresh:
            refresh_rate = st.slider("Intervalle (sec)", 1, 10, 2)
        
        st.markdown("---")
        st.markdown("### 📊 Tiers de Stockage")
        st.markdown("""
        - 🔥 **Hot**: Mémoire (< 1ms)
        - 🌤️ **Warm**: SQLite (< 10ms)
        - ❄️ **Cold**: Fichiers compressés
        """)
    
    # Main content area
    if demo_mode:
        # Demo data
        metrics_data = {
            "summary": {
                "hot_count": 45, "warm_count": 120, "cold_count": 340,
                "hot_size_bytes": 15000, "warm_size_bytes": 85000, "cold_size_bytes": 42000,
                "compression_ratio": 8.5, "total_processed": 505, "anomalies_detected": 23
            }
        }
        recent_data = {"data": {"recent": []}}
    else:
        metrics_data = get_metrics()
        recent_data = get_recent_data(100)
    
    if metrics_data and metrics_data.get("data"):
        summary = metrics_data["data"]["summary"]
        
        # Top metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(render_metric_card(
                "Total Traités", 
                f"{summary['total_processed']:,}",
                "#00d4ff"
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown(render_metric_card(
                "Anomalies Détectées",
                f"{summary['anomalies_detected']:,}",
                "#ff4444"
            ), unsafe_allow_html=True)
        
        with col3:
            st.markdown(render_metric_card(
                "Ratio Compression",
                f"{summary['compression_ratio']:.1f}x",
                "#00ff88"
            ), unsafe_allow_html=True)
        
        with col4:
            total_size = (summary['hot_size_bytes'] + summary['warm_size_bytes'] + 
                         summary['cold_size_bytes']) / 1024
            st.markdown(render_metric_card(
                "Stockage Total",
                f"{total_size:.1f} KB",
                "#ffaa00"
            ), unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Storage distribution charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📊 Distribution par Tier")
            
            tier_data = pd.DataFrame({
                'Tier': ['🔥 Hot', '🌤️ Warm', '❄️ Cold'],
                'Count': [summary['hot_count'], summary['warm_count'], summary['cold_count']],
                'Color': ['#ff4444', '#ffaa00', '#0088ff']
            })
            
            fig = px.pie(
                tier_data, 
                values='Count', 
                names='Tier',
                color='Tier',
                color_discrete_map={
                    '🔥 Hot': '#ff4444',
                    '🌤️ Warm': '#ffaa00',
                    '❄️ Cold': '#0088ff'
                },
                hole=0.4
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#ffffff',
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.2,
                    xanchor="center",
                    x=0.5
                )
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### 💾 Taille par Tier")
            
            size_data = pd.DataFrame({
                'Tier': ['Hot', 'Warm', 'Cold'],
                'Size (KB)': [
                    summary['hot_size_bytes'] / 1024,
                    summary['warm_size_bytes'] / 1024,
                    summary['cold_size_bytes'] / 1024
                ]
            })
            
            fig = px.bar(
                size_data,
                x='Tier',
                y='Size (KB)',
                color='Tier',
                color_discrete_map={
                    'Hot': '#ff4444',
                    'Warm': '#ffaa00',
                    'Cold': '#0088ff'
                }
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#ffffff',
                showlegend=False,
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Feature Importance
        if not demo_mode:
            importance_data = get_feature_importance()
            if importance_data and importance_data.get("data"):
                st.markdown("### 🤖 Importance des Features ML")
                
                importance = importance_data["data"]["importance"]
                imp_df = pd.DataFrame([
                    {"Feature": k, "Importance": v} 
                    for k, v in importance.items()
                ])
                
                fig = px.bar(
                    imp_df,
                    x='Importance',
                    y='Feature',
                    orientation='h',
                    color='Importance',
                    color_continuous_scale='viridis'
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#ffffff',
                    showlegend=False,
                    height=400,
                    yaxis=dict(showgrid=False),
                    xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Recent data table
        st.markdown("### 📋 Données Récentes")
        
        if recent_data and recent_data.get("data", {}).get("recent"):
            recent = recent_data["data"]["recent"]
            
            df = pd.DataFrame(recent)
            
            if not df.empty:
                # Format for display
                display_cols = ['timestamp', 'sensor_type', 'value', 'storage_tier', 
                               'confidence', 'is_anomaly']
                display_df = df[display_cols].copy() if all(c in df.columns for c in display_cols) else df
                
                # Color code by tier
                def highlight_tier(row):
                    tier = row.get('storage_tier', '')
                    if tier == 'hot':
                        return ['background-color: rgba(255,68,68,0.3)'] * len(row)
                    elif tier == 'warm':
                        return ['background-color: rgba(255,170,0,0.3)'] * len(row)
                    elif tier == 'cold':
                        return ['background-color: rgba(0,136,255,0.3)'] * len(row)
                    return [''] * len(row)
                
                styled_df = display_df.style.apply(highlight_tier, axis=1)
                st.dataframe(styled_df, use_container_width=True, height=400)
            else:
                st.info("Aucune donnée récente. Cliquez sur 'Générer & Stocker' pour commencer.")
        else:
            st.info("Aucune donnée disponible. Générez des données pour commencer!")
    else:
        st.warning("Impossible de récupérer les métriques")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
        <p>🎓 Projet Académique - Master Big Data AI</p>
        <p>Stockage des Données IoT: Avancées et Défis</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Auto-refresh
    if not demo_mode and auto_refresh:
        time.sleep(refresh_rate)
        st.rerun()


if __name__ == "__main__":
    main()
