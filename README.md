# 🌿 AgriMind AI (Streamlit)

## Local run
```
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # apni GROQ key daalen
streamlit run app.py
```

## Streamlit Community Cloud par deploy
1. Is folder ko GitHub repo mein push karein.
2. https://share.streamlit.io -> **Create app** -> repo, branch aur main file `app.py` chunen.
3. **Advanced settings -> Secrets** mein paste karein:
   ```
   GROQ_API_KEY = "gsk_..."
   ```
4. **Deploy** dabayen. Live link `https://<app-name>.streamlit.app` hoga.

Optional photos: `hero.jpg`, `field.jpg`, `avatar.jpg` repo ke root mein rakh dein.
