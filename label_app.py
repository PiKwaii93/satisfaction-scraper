import streamlit as st
import pandas as pd
import os

st.title("🗂️ Labellisation Manuelle")

csv_path = st.text_input("Chemin du CSV", value="2026-05-21T22-20_export.csv")

if os.path.exists(csv_path):
    df = pd.read_csv(csv_path)
    if 'manual_label' not in df.columns:
        df['manual_label'] = None
    
    to_label = df[df['manual_label'].isna()]
    
    if len(to_label) > 0:
        index = to_label.index[0]
        st.info(f"Avis : {df.loc[index, 'verbatim']}")
        
        col1, col2, col3 = st.columns(3)
        if col1.button("POSITIF"):
            df.loc[index, 'manual_label'] = 'Positif'
            df.to_csv(csv_path, index=False)
            st.rerun()
        if col2.button("NÉGATIF"):
            df.loc[index, 'manual_label'] = 'Négatif'
            df.to_csv(csv_path, index=False)
            st.rerun()
        if col3.button("NEUTRE"):
            df.loc[index, 'manual_label'] = 'Neutre'
            df.to_csv(csv_path, index=False)
            st.rerun()
    else:
        st.success("Terminé !")