import streamlit as st
import pandas as pd
import psycopg2
import os
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# Fonction de nettoyage (Data Quality)
def clean_data(df):
    """Supprime les doublons, les valeurs nulles et normalise les données."""
    df = df.drop_duplicates(subset=['verbatim'])
    df = df.dropna(subset=['rating'])
    df = df[df['rating'].between(1, 5)]
    df['verbatim'] = df['verbatim'].str.strip()
    return df

# Connexion BDD
def get_data():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "postgres_db"),
            database=os.getenv("DB_NAME", "satisfaction_client"),
            user=os.getenv("DB_USER", "admin"),
            password=os.getenv("DB_PASSWORD", "password123")
        )
        query = "SELECT rating, verbatim FROM fact_reviews"
        df = pd.read_sql(query, conn)
        conn.close()
        return clean_data(df)
    except Exception as e:
        st.error(f"Erreur de connexion à la base de données : {e}")
        return pd.DataFrame(columns=['rating', 'verbatim'])

# Configuration du dashboard
st.set_page_config(page_title="Dashboard Satisfaction", layout="wide")
st.title("📊 Dashboard Satisfaction Client")

df = get_data()

if not df.empty:
    # 1. KPIs
    col1, col2 = st.columns(2)
    col1.metric("Nombre d'avis analysés", len(df))
    col2.metric("Note Moyenne", f"{df['rating'].mean():.2f}")

    # 2. Histogramme
    st.subheader("Distribution des notes")
    st.bar_chart(df['rating'].value_counts().sort_index())

    # 3. Nuage de mots
    st.subheader("Analyse sémantique (Nuage de mots)")
    text = " ".join(df['verbatim'].astype(str))
    wordcloud = WordCloud(width=800, height=300, background_color='white').generate(text)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    st.pyplot(fig)

    # 4. Derniers avis
    st.subheader("Derniers avis collectés")
    st.dataframe(df.sort_index(ascending=False).head(10))
else:
    st.warning("Aucune donnée disponible ou erreur de connexion.")