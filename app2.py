import streamlit as st
import pandas as pd
import plotly.express as px
from google.cloud import bigquery
from google.oauth2 import service_account
import datetime

# -----------------------------------------------------------------------------
# CONFIGURATION DE LA PAGE
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Olist E-commerce Avancé",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🛒 Dashboard Analytique Olist E-commerce")
st.markdown("Données issues des modèles **dbt mart** (BigQuery: `testjocelyn.e_com_dev`)")

# -----------------------------------------------------------------------------
# INITIALISATION BIGQUERY (Avec gestion des secrets)
# -----------------------------------------------------------------------------
@st.cache_resource
def init_bq_client():
    try:
        # Essai avec les secrets Streamlit (Recommandé)
        secrets = st.secrets["gcp"]
        creds = service_account.Credentials.from_service_account_info(
            eval(secrets["service_account_info"]) if isinstance(secrets["service_account_info"], str) else secrets["service_account_info"]
        )
        return bigquery.Client(project=secrets["project_id"], credentials=creds)
    except Exception:
        # Fallback sur les credentials par défaut du système
        return bigquery.Client(project="testjocelyn")

client = init_bq_client()

# -----------------------------------------------------------------------------
# CHARGEMENT DES DONNÉES (Mise en cache pour la performance)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_all_data():
    # 1. Faits : Commandes
    query_orders = """
        SELECT 
            order_id, customer_unique_id, customer_state, order_status,
            order_purchase_timestamp, delivery_days, avg_review_score,
            items_total_value
        FROM `testjocelyn.e_com_dev.fct_orders`
        WHERE order_purchase_timestamp IS NOT NULL
    """
    df_orders = client.query(query_orders).to_dataframe()
    df_orders['order_purchase_timestamp'] = pd.to_datetime(df_orders['order_purchase_timestamp'], utc=True)
    df_orders['month'] = df_orders['order_purchase_timestamp'].dt.tz_convert(None).dt.to_period('M').astype(str)

    # 2. Dimension : Clients
    query_customers = """
        SELECT 
            customer_unique_id, state, zip_code_prefix, lat, lng,
            total_orders, last_order_at, lifetime_value
        FROM `testjocelyn.e_com_dev.dim_customers`
        WHERE lat IS NOT NULL AND lng IS NOT NULL
    """
    df_customers = client.query(query_customers).to_dataframe()
    df_customers['last_order_at'] = pd.to_datetime(df_customers['last_order_at'], utc=True)

    # 3. Dimension : Produits
    query_products = """
        SELECT product_category_name_english, total_orders, total_revenue
        FROM `testjocelyn.e_com_dev.dim_products`
        WHERE product_category_name_english IS NOT NULL
    """
    df_products = client.query(query_products).to_dataframe()

    # 4. Dimension : Vendeurs
    query_sellers = """
        SELECT seller_id, city, state, total_orders, total_revenue
        FROM `testjocelyn.e_com_dev.dim_sellers`
        ORDER BY total_revenue DESC
        LIMIT 50
    """
    df_sellers = client.query(query_sellers).to_dataframe()

    return df_orders, df_customers, df_products, df_sellers

with st.spinner("Chargement des données depuis BigQuery..."):
    df_orders, df_customers, df_products, df_sellers = load_all_data()

# -----------------------------------------------------------------------------
# BARRE LATÉRALE : FILTRES GLOBAUX
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ Filtres Globaux")

min_date = df_orders['order_purchase_timestamp'].min().date()
max_date = df_orders['order_purchase_timestamp'].max().date()
selected_dates = st.sidebar.date_input("Période d'analyse", [min_date, max_date], min_value=min_date, max_value=max_date)

all_statuses = sorted(df_orders['order_status'].dropna().unique().tolist())
selected_status = st.sidebar.multiselect("Statut de commande", options=all_statuses, default=all_statuses)

all_states = sorted(df_orders['customer_state'].dropna().unique().tolist())
selected_state = st.sidebar.multiselect("État du client", options=all_states, default=all_states)

# Application des filtres
mask = (
    (df_orders['order_purchase_timestamp'].dt.date >= selected_dates[0]) &
    (df_orders['order_purchase_timestamp'].dt.date <= selected_dates[1]) &
    (df_orders['order_status'].isin(selected_status)) &
    (df_orders['customer_state'].isin(selected_state))
)
df_filtered = df_orders[mask]

# -----------------------------------------------------------------------------
# NAVIGATION PAR ONGLETS (TABS)
# -----------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📊 Vue d'ensemble", "🗺️ Géographie & RFM", "📦 Produits & Vendeurs"])

# =============================================================================
# ONGLET 1 : VUE D'ENSEMBLE
# =============================================================================
with tab1:
    # KPIs
    total_revenue = df_filtered['items_total_value'].sum()
    total_orders = df_filtered['order_id'].nunique()
    avg_delivery = df_filtered['delivery_days'].mean()
    avg_score = df_filtered['avg_review_score'].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Chiffre d'Affaires", f"R$ {total_revenue:,.0f}")
    col2.metric("📦 Commandes", f"{total_orders:,}")
    col3.metric("🚚 Délai moyen", f"{avg_delivery:.1f} jours")
    col4.metric("⭐ Note moyenne", f"{avg_score:.2f} / 5")

    st.markdown("---")
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("📈 Évolution du CA mensuel")
        rev_time = df_filtered.groupby('month')['items_total_value'].sum().reset_index()
        fig_rev = px.line(rev_time, x='month', y='items_total_value', markers=True, template="plotly_white")
        fig_rev.update_traces(line=dict(color='#1f77b4', width=3))
        st.plotly_chart(fig_rev, use_container_width=True)

    with col_chart2:
        st.subheader("🍩 Répartition des Statuts")
        status_counts = df_filtered['order_status'].value_counts().reset_index()
        status_counts.columns = ['Statut', 'Nombre']
        fig_status = px.pie(status_counts, values='Nombre', names='Statut', hole=0.4, template="plotly_white")
        st.plotly_chart(fig_status, use_container_width=True)

    # Export
    st.markdown("---")
    csv = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Exporter les commandes filtrées (CSV)",
        data=csv,
        file_name=f"olist_commandes_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

# =============================================================================
# ONGLET 2 : GÉOGRAPHIE & ANALYSE RFM
# =============================================================================
with tab2:
    col_map, col_rfm = st.columns([2, 1])

    with col_map:
        st.subheader("🗺️ Répartition Géographique des Clients (par Code Postal)")
        # Agrégation pour la carte
        df_map = df_customers.groupby('zip_code_prefix').agg(
            lat=('lat', 'first'),
            lng=('lng', 'first'),
            nb_customers=('customer_unique_id', 'nunique'),
            total_ltv=('lifetime_value', 'sum')
        ).reset_index()

        fig_map = px.scatter_mapbox(
            df_map, lat="lat", lon="lng", size="nb_customers", color="total_ltv",
            color_continuous_scale="Viridis", # <--- CORRECTION APPLIQUÉE ICI
            size_max=15, zoom=3,
            center={"lat": -14.2350, "lon": -51.9253}, 
            mapbox_style="open-street-map",
            hover_data=["zip_code_prefix", "nb_customers", "total_ltv"],
            title="Taille = Nb Clients | Couleur = Lifetime Value (R$)"
        )
        fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=600)
        st.plotly_chart(fig_map, use_container_width=True)

    with col_rfm:
        st.subheader("💎 Segmentation RFM")
        today = pd.Timestamp.now(tz='UTC')
        df_rfm = df_customers.copy()
        df_rfm['recency_days'] = (today - df_rfm['last_order_at']).dt.days
        
        try:
            df_rfm['R_Score'] = pd.qcut(df_rfm['recency_days'].rank(ascending=False), q=4, labels=[4, 3, 2, 1], duplicates='drop').astype(int)
            df_rfm['F_Score'] = pd.qcut(df_rfm['total_orders'].rank(ascending=True), q=4, labels=[1, 2, 3, 4], duplicates='drop').astype(int)
            df_rfm['M_Score'] = pd.qcut(df_rfm['lifetime_value'].rank(ascending=True), q=4, labels=[1, 2, 3, 4], duplicates='drop').astype(int)
            
            df_rfm['RFM_Score'] = df_rfm['R_Score'] + df_rfm['F_Score'] + df_rfm['M_Score']
            
            def segmenter(score):
                if score >= 9: return "🏆 Champions"
                if score >= 7: return "💎 Fidèles"
                if score >= 5: return "🌱 Potentiels"
                if score >= 3: return "⚠️ À risque"
                return "💀 Perdus"
                
            df_rfm['Segment'] = df_rfm['RFM_Score'].apply(segmenter)
            
            rfm_counts = df_rfm['Segment'].value_counts().reset_index()
            rfm_counts.columns = ['Segment', 'Nombre']
            
            color_map = {"🏆 Champions": "gold", "💎 Fidèles": "green", "🌱 Potentiels": "blue", "⚠️ À risque": "orange", "💀 Perdus": "red"}
            fig_rfm = px.pie(rfm_counts, values='Nombre', names='Segment', 
                             color='Segment', color_discrete_map=color_map, hole=0.5)
            st.plotly_chart(fig_rfm, use_container_width=True)
            
        except Exception as e:
            st.warning("Données insuffisantes pour calculer les quartiles RFM.")

# =============================================================================
# ONGLET 3 : PRODUITS & VENDEURS
# =============================================================================
with tab3:
    col_prod, col_sell = st.columns(2)

    with col_prod:
        st.subheader("🏆 Top 10 Catégories par Revenu")
        df_top_cat = df_products.sort_values('total_revenue', ascending=False).head(10)
        fig_cat = px.bar(
            df_top_cat, x='total_revenue', y='product_category_name_english',
            orientation='h', template="plotly_white", color='total_revenue',
            color_continuous_scale='Blues',
            labels={'total_revenue': 'Revenu (R$)', 'product_category_name_english': 'Catégorie'}
        )
        fig_cat.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_cat, use_container_width=True)

    with col_sell:
        st.subheader("🏪 Top 10 Vendeurs par Revenu")
        df_top_sellers = df_sellers.head(10)
        fig_sell = px.bar(
            df_top_sellers, x='total_revenue', y='seller_id',
            orientation='h', template="plotly_white", color='total_revenue',
            color_continuous_scale='Greens',
            labels={'total_revenue': 'Revenu (R$)', 'seller_id': 'ID Vendeur'}
        )
        fig_sell.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_sell, use_container_width=True)

    st.markdown("---")
    st.subheader("🔍 Exploration des Données (Échantillon des 50 dernières lignes)")
    st.dataframe(
        df_filtered[['order_id', 'order_purchase_timestamp', 'customer_state', 'order_status', 'items_total_value', 'delivery_days']].tail(50),
        use_container_width=True, hide_index=True
    )