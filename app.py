import streamlit as st
import pandas as pd
import plotly.express as px
from google.cloud import bigquery
import os

# -----------------------------------------------------------------------------
# CONFIGURATION DE LA PAGE
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Olist E-commerce",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🛒 Dashboard Analytique Olist E-commerce")
st.markdown("Données issues des modèles **dbt mart** (BigQuery: `testjocelyn.e_com_dev`)")

# -----------------------------------------------------------------------------
# CHARGEMENT DES DONNÉES (Avec mise en cache pour la performance)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600) # Cache les données pendant 1 heure
def load_data_from_bq():
    # Assurez-vous que vos credentials GCP sont configurés 
    # (ex: export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json")
    client = bigquery.Client(project="testjocelyn")
    
    # 1. Faits : Commandes (Niveau agrégé pour les KPIs)
    query_orders = """
        SELECT 
            order_id, customer_unique_id, customer_state, order_status,
            order_purchase_timestamp, delivery_days, avg_review_score,
            items_total_value, distinct_sellers
        FROM `testjocelyn.e_com_dev.fct_orders`
        WHERE order_purchase_timestamp IS NOT NULL
    """
    df_orders = client.query(query_orders).to_dataframe()
    df_orders['order_purchase_timestamp'] = pd.to_datetime(df_orders['order_purchase_timestamp'])
    df_orders['month'] = df_orders['order_purchase_timestamp'].dt.to_period('M').astype(str)

    # 2. Dimension : Produits (Top catégories)
    query_products = """
        SELECT 
            product_category_name_english, 
            total_orders, 
            total_revenue
        FROM `testjocelyn.e_com_dev.dim_products`
        WHERE product_category_name_english IS NOT NULL
    """
    df_products = client.query(query_products).to_dataframe()

    # 3. Dimension : Clients (Par État pour la géographie)
    query_customers = """
        SELECT 
            state, 
            COUNT(customer_unique_id) as total_customers,
            SUM(lifetime_value) as total_ltv
        FROM `testjocelyn.e_com_dev.dim_customers`
        WHERE state IS NOT NULL
        GROUP BY state
        ORDER BY total_ltv DESC
    """
    df_customers = client.query(query_customers).to_dataframe()

    return df_orders, df_products, df_customers

# Chargement des données
with st.spinner("Chargement des données depuis BigQuery..."):
    df_orders, df_products, df_customers = load_data_from_bq()

# -----------------------------------------------------------------------------
# BARRE LATÉRALE : FILTRES
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ Filtres")

# Filtre Date
min_date = df_orders['order_purchase_timestamp'].min().date()
max_date = df_orders['order_purchase_timestamp'].max().date()
selected_dates = st.sidebar.date_input(
    "Période d'analyse",
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

# Filtre Statut
all_statuses = df_orders['order_status'].dropna().unique().tolist()
selected_status = st.sidebar.multiselect(
    "Statut de commande",
    options=all_statuses,
    default=all_statuses
)

# Filtre État (Brésil)
all_states = df_orders['customer_state'].dropna().unique().tolist()
selected_state = st.sidebar.multiselect(
    "État du client",
    options=all_states,
    default=all_states
)

# -----------------------------------------------------------------------------
# APPLICATION DES FILTRES
# -----------------------------------------------------------------------------
mask = (
    (df_orders['order_purchase_timestamp'].dt.date >= selected_dates[0]) &
    (df_orders['order_purchase_timestamp'].dt.date <= selected_dates[1]) &
    (df_orders['order_status'].isin(selected_status)) &
    (df_orders['customer_state'].isin(selected_state))
)
df_filtered = df_orders[mask]

# -----------------------------------------------------------------------------
# LIGNE 1 : KPIs PRINCIPAUX
# -----------------------------------------------------------------------------
total_revenue = df_filtered['items_total_value'].sum()
total_orders = df_filtered['order_id'].nunique()
avg_delivery = df_filtered['delivery_days'].mean()
avg_score = df_filtered['avg_review_score'].mean()

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Chiffre d'Affaires", f"R$ {total_revenue:,.0f}")
col2.metric("📦 Commandes Totales", f"{total_orders:,}")
col3.metric("🚚 Délai moyen (jours)", f"{avg_delivery:.1f}")
col4.metric("⭐ Note moyenne", f"{avg_score:.2f} / 5")

st.markdown("---")

# -----------------------------------------------------------------------------
# LIGNE 2 : GRAPHIQUES PRINCIPAUX
# -----------------------------------------------------------------------------
col_chart1, col_chart2 = st.columns(2)

# Graphique 1 : Évolution du CA dans le temps
with col_chart1:
    st.subheader("📈 Évolution du Chiffre d'Affaires")
    rev_time = df_filtered.groupby('month')['items_total_value'].sum().reset_index()
    fig_rev = px.line(
        rev_time, x='month', y='items_total_value', 
        markers=True, template="plotly_white",
        labels={'items_total_value': 'Revenu (R$)', 'month': 'Mois'}
    )
    fig_rev.update_traces(line=dict(color='#1f77b4', width=3))
    st.plotly_chart(fig_rev, use_container_width=True)

# Graphique 2 : Répartition des statuts de commande
with col_chart2:
    st.subheader("🍩 Répartition des Statuts")
    status_counts = df_filtered['order_status'].value_counts().reset_index()
    status_counts.columns = ['Statut', 'Nombre']
    fig_status = px.pie(
        status_counts, values='Nombre', names='Statut',
        hole=0.4, template="plotly_white",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig_status, use_container_width=True)

# -----------------------------------------------------------------------------
# LIGNE 3 : ANALYSE PRODUITS & GÉOGRAPHIE
# -----------------------------------------------------------------------------
col_chart3, col_chart4 = st.columns(2)

# Graphique 3 : Top 10 Catégories de produits (basé sur dim_products)
with col_chart3:
    st.subheader("🏆 Top 10 Catégories par Revenu")
    # On filtre les catégories qui ont du revenu
    df_top_cat = df_products.sort_values('total_revenue', ascending=False).head(10)
    fig_cat = px.bar(
        df_top_cat, x='total_revenue', y='product_category_name_english',
        orientation='h', template="plotly_white",
        labels={'total_revenue': 'Revenu Total (R$)', 'product_category_name_english': 'Catégorie'},
        color='total_revenue', color_continuous_scale='Blues'
    )
    fig_cat.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_cat, use_container_width=True)

# Graphique 4 : Performance par État (Brésil)
with col_chart4:
    st.subheader("🗺️ Répartition des Clients par État")
    fig_geo = px.bar(
        df_customers, x='state', y='total_customers',
        template="plotly_white",
        labels={'total_customers': 'Nombre de Clients Uniques', 'state': 'État'},
        color='total_customers', color_continuous_scale='Viridis'
    )
    st.plotly_chart(fig_geo, use_container_width=True)

# -----------------------------------------------------------------------------
# LIGNE 4 : EXPLORATION DES DONNÉES BRUTES
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("🔍 Exploration des Données (Échantillon)")
st.dataframe(
    df_filtered[['order_id', 'order_purchase_timestamp', 'customer_state', 'order_status', 'items_total_value', 'delivery_days']].head(50),
    use_container_width=True,
    hide_index=True
)