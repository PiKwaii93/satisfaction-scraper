import pandas as pd
import psycopg2
import os
from textblob import TextBlob

def run_analysis():
    # 1. Connexion et récupération des données
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres_db"),
        database=os.getenv("DB_NAME", "satisfaction_client"),
        user=os.getenv("DB_USER", "admin"),
        password=os.getenv("DB_PASSWORD", "password123")
    )
    
    df = pd.read_sql("SELECT rating, verbatim FROM fact_reviews", conn)
    conn.close()

    # 2. Analyse de sentiment avec TextBlob
    def get_sentiment(text):
        # polarity: -1 (très négatif) à 1 (très positif)
        return TextBlob(text).sentiment.polarity

    df['sentiment_score'] = df['verbatim'].apply(get_sentiment)

    # 3. Calcul de KPIs
    avg_note = df['rating'].mean()
    avg_sentiment = df['sentiment_score'].mean()
    
    print(f"\n--- RAPPORT D'ANALYSE ---")
    print(f"Nombre d'avis analysés : {len(df)}")
    print(f"Note moyenne (sur 5)   : {avg_note:.2f}")
    print(f"Sentiment moyen (NLP)  : {avg_sentiment:.2f} (de -1 à 1)")
    
    print("\n--- ÉCHANTILLON D'AVIS ---")
    print(df[['rating', 'sentiment_score', 'verbatim']].head(10))

if __name__ == "__main__":
    run_analysis()