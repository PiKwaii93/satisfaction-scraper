import streamlit as st
import pandas as pd
import psycopg2
import os
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# Fonction de nettoyage (Data Quality)
def clean_data(df):
    """Supprime les valeurs nulles et normalise les données."""
    # CORRECTION CRITIQUE : Suppression du drop_duplicates sur le verbatim seul.
    # Sinon, tous les avis qui possèdent un texte vide ("") sont écrasés pour n'en garder qu'un seul !
    # Le dédoublonnage global est déjà assuré en amont par la base de données (ON CONFLICT DO NOTHING).
    
    df = df.dropna(subset=['rating'])
    df = df[df['rating'].between(1, 5)]
    df['verbatim'] = df['verbatim'].astype(str).str.strip()
    return df

# Connexion BDD et récupération des données enrichies
def get_data():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "postgres_db"),
            database=os.getenv("DB_NAME", "satisfaction_client"),
            user=os.getenv("DB_USER", "admin"),
            password=os.getenv("DB_PASSWORD", "password123")
        )
        query = """
            SELECT review_id, rating, verbatim, sentiment_label, sentiment_score
            FROM fact_reviews
            ORDER BY review_id
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return clean_data(df)
    except Exception as e:
        st.error(f"Erreur de connexion à la base de données : {e}")
        return pd.DataFrame(columns=['review_id', 'rating', 'verbatim', 'sentiment_label', 'sentiment_score'])

# Configuration du dashboard
st.set_page_config(page_title="Dashboard Satisfaction", layout="wide")
st.title("📊 Dashboard Satisfaction Client")

df = get_data()

if not df.empty:
    # 1. KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("Avis analysés", len(df))
    col2.metric("Note Moyenne", f"{df['rating'].mean():.2f} / 5")
    # Utilisation de col3 qui restait inutilisée dans le script d'origine
    col3.metric("Score de Sentiment Moyen", f"{df['sentiment_score'].mean():.2f}")
    
    # 2. Graphiques : Distribution des notes ET des sentiments
    st.subheader("Analyse de la satisfaction")
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.write("Distribution des notes")
        st.bar_chart(df['rating'].value_counts().sort_index())
    
    with col_b:
        st.write("Répartition des sentiments (IA)")
        # Tri personnalisé pour l'ordre : Négatif, Neutre, Positif
        sentiment_order = ['Négatif', 'Neutre', 'Positif']
        sentiment_counts = df['sentiment_label'].value_counts().reindex(sentiment_order).fillna(0)
        st.bar_chart(sentiment_counts)

    # 3. Nuage de mots
    st.subheader("Analyse sémantique (Nuage de mots)")
    # Sécurité : On filtre pour s'assurer qu'il y a du contenu textuel à analyser
    text_combined = " ".join(review for review in df['verbatim'] if review.strip())
    
    if text_combined.strip():
        wordcloud = WordCloud(width=800, height=300, background_color='white', colormap='viridis').generate(text_combined)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        st.pyplot(fig)
    else:
        st.info("Aucun texte rédigé disponible pour générer un nuage de mots (avis uniquement composés de notes).")

    # 4. Exploration et filtrage des avis
    st.subheader("🔍 Exploration des avis collectés")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtre_note = st.multiselect(
            "Filtrer par Note :", 
            options=sorted(df['rating'].unique()), 
            default=sorted(df['rating'].unique())
        )
    with col_f2:
        filtre_sentiment = st.multiselect(
            "Filtrer par Sentiment (IA) :", 
            options=['Négatif', 'Neutre', 'Positif'], 
            default=['Négatif', 'Neutre', 'Positif']
        )
    
    # Application des filtres sur le DataFrame
    df_filtre = df[df['rating'].isin(filtre_note) & df['sentiment_label'].isin(filtre_sentiment)]
    
    # CORRECTION : Sélection automatique de l'index 3 ("Tous") pour charger la totalité des lignes au démarrage
    nb_affichage = st.selectbox("Nombre d'avis :", options=[10, 50, 100, "Tous"], index=3)
    
    if nb_affichage == "Tous":
        df_final = df_filtre
    else:
        df_final = df_filtre.head(int(nb_affichage))
        
    st.write(f"Affichage de {len(df_final)} avis sur {len(df_filtre)} après filtrage.")
    
    # Affichage avec style conditionnel
    def color_sentiment(val):
        color = 'red' if val == 'Négatif' else 'orange' if val == 'Neutre' else 'green'
        return f'color: {color}; font-weight: bold'

    st.dataframe(
        df_final[['review_id', 'rating', 'sentiment_label', 'sentiment_score', 'verbatim']]
        .style.applymap(color_sentiment, subset=['sentiment_label']),
        use_container_width=True
    )

else:
    st.warning("Aucune donnée disponible. Vérifie que le pipeline ETL a bien tourné.")
