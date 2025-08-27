import requests
import streamlit as st
from openai import OpenAI
import json
from pathlib import Path
import os

# 🔑 Keys
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")             

client = OpenAI(api_key=OPENAI_API_KEY)

st.set_page_config(page_title="🌍 Environment News Monitor", layout="wide")
st.title("🌍 Environment & Climate News Monitor")
st.write("Powered by AI — fetching and summarizing the latest environment & EU climate news for Earthly.")

# ---------- FETCH NEWS WITH BACKUP ----------
url = f"https://newsapi.org/v2/everything?q=environment+climate+EU&sortBy=publishedAt&language=en&apiKey={NEWS_API_KEY}"

try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    articles = data.get("articles", [])[:15]

    # Save backup
    with open("backup.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

except Exception as e:
    st.warning(f"⚠️ Live fetch failed: {e}\nLoading backup data instead.")
    if Path("backup.json").exists():
        with open("backup.json", "r", encoding="utf-8") as f:
            articles = json.load(f)
    else:
        articles = []

# ---------- CREATE TABS ----------
tab1, tab2 = st.tabs(["🌍 General News", "🌱 Earthly Projects"])

# ---------- TAB 1: GENERAL NEWS ----------
with tab1:
    st.subheader("🌍 Latest Environment & Climate News")

    # Filter options
    # Filter options with synonyms and corporate commitments
filters = {
    "All": [],
    "EU": [
        "EU", "European Union", "Brussels", "EC", "European Commission"
    ],
    "Climate": [
        "climate", "global warming", "climate change", "heatwave", "extreme weather"
    ],
    "Sustainability": [
        "sustainability", "net zero", "renewable", "green transition",
        "environmental", "circular economy", "sustainable"
    ],
    "Carbon": [
        "carbon", "emissions", "carbon market", "carbon credits",
        "decarbonization", "ETS", "offset"
    ],
    "Corporate Commitments": [
        "net zero", "carbon neutral", "carbon neutrality", 
        "science-based targets initiative", "SBTi", 
        "2030 climate target", "2050 climate target", 
        "climate pledge", "climate commitment"
    ]
}

choice = st.selectbox("Filter news by keyword group:", list(filters.keys()))

for article in articles:
    title = article["title"]
    description = article.get("description", "")
    source = article["source"]["name"]
    link = article["url"]

    text = (title + " " + description).lower()

    # Skip if filter doesn't match
    if choice != "All":
        keywords = [kw.lower() for kw in filters[choice]]
        if not any(kw in text for kw in keywords):
            continue

    # Summarize with AI
    prompt = f"Summarize this news in 2 sentences for a business audience:\n\nTitle: {title}\nDescription: {description}"
    try:
        summary = client.responses.create(
            model="gpt-4o-mini",
            input=prompt
        ).output_text
    except Exception as e:
        summary = f"⚠️ Summary unavailable (API issue: {e})"

    # Display
    with st.container():
        st.subheader(title)
        st.caption(f"{source}")
        st.write(summary)
        st.markdown(f"[Read full article]({link})")
        st.divider()


# ---------- TAB 2: EARTHLY PROJECTS ----------
with tab2:
    st.subheader("🌱 News Relevant to Earthly Projects")

    # Earthly projects and keywords
    projects = {
        "Rimba Raya": ["Rimba Raya"],
        "EthioTrees": ["EthioTrees"],
        "TIST": ["TIST"],
        "Delta Blue": ["Delta Blue"],
        "Kukumuty": ["Kukumuty"],
        "Iford": ["Iford"],
        "South Downs": ["South Downs"],
        "Voa Aina": ["Voa Aina"],
        "Scolel'te": ["Scolel'te"]
    }

    for project, keywords in projects.items():
        st.markdown(f"### {project}")
        found = False

        for article in articles:
            text = (article["title"] + " " + article.get("description", "")).lower()
            if any(keyword.lower() in text for keyword in keywords):
                found = True
                st.write(f"**{article['title']}** ({article['source']['name']})")
                st.write(article["url"])
                st.divider()

        if not found:
            st.caption("No recent matching news.")
