# app/sentiment_analysis.py
from textblob import TextBlob

def get_sentiment(text):
    """
    Analyse le sentiment d'un texte.
    Note : TextBlob est limité sur le français, la règle métier sera appliquée dans etl.py.
    """
    if not text or not isinstance(text, str):
        return 'Neutre', 0.0

    analysis = TextBlob(text)
    score = analysis.sentiment.polarity
    
    # Classification simplifiée
    if score > 0:
        category = 'Positif'
    elif score < 0:
        category = 'Négatif'
    else:
        category = 'Neutre'
        
    return category, round(score, 2)