import requests
import streamlit as st
from openai import OpenAI
import json
from pathlib import Path
import os
import pandas as pd
from datetime import datetime

# 🔑 Keys
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")             

client = OpenAI(api_key=OPENAI_API_KEY)

st.set_page_config(page_title="🌍 Earthly News Monitor", layout="wide")
st.title("🌍 Earthly News Monitor")
st.write("AI-powered tool tracking Earthly projects and registry news.")

# ---------- LOAD KEYWORDS ----------
df = pd.read_csv("keywords.csv")

# Build dictionary {Category: [keywords]}
filters = {}
for cat, group in df.groupby("Category"):
    filters[cat] = group["Keyword"].dropna().tolist()

# ---------- FETCH NEWS WITH BACKUP ----------
# (for now still fetching broadly – then filtering with keywords)
url = f"https://newsapi.org/v2/everything?q=climate+carbon+sustainability&sortBy=publishedAt&language=en&apiKey={NEWS_API_KEY}"

try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    articles = data.get("articles", [])[:20]

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
tab1, tab2 = st.tabs(["🌱 Earthly Projects", "🏛 Registry News"])

# ---------- TAB 1: EARTHLY PROJECTS ----------
with tab1:
    st.subheader("🌱 News Relevant to Earthly Projects")

    from datetime import datetime, timedelta

    def fetch_articles(query, start_date, end_date):
        url = (
            f"https://newsapi.org/v2/everything?q={query}"
            f"&from={start_date}&to={end_date}"
            f"&sortBy=publishedAt&language=en&apiKey={NEWS_API_KEY}"
        )
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json().get("articles", [])
        except:
            return []

    # Define 2-year range
    today = datetime.utcnow()
    two_years_ago = today - timedelta(days=730)

    # Collect articles for each Earthly Project keyword
    earthly_articles = []
    for kw in filters.get("Earthly Project", []):
        results = fetch_articles(
            kw,
            start_date=two_years_ago.strftime("%Y-%m-%d"),
            end_date=today.strftime("%Y-%m-%d")
        )
        earthly_articles.extend(results)

    # Deduplicate by URL
    seen = set()
    unique_articles = []
    for art in earthly_articles:
        if art["url"] not in seen:
            unique_articles.append(art)
            seen.add(art["url"])

    # Sort newest first
    sorted_articles = sorted(
        unique_articles,
        key=lambda x: x.get("publishedAt", ""),
        reverse=True
    )

    # Display results
    for article in sorted_articles:
        title = article["title"]
        description = article.get("description", "")
        source = article["source"]["name"]
        link = article["url"]
        published = article.get("publishedAt", "")

        text = (title + " " + description).lower()

        if any(kw.lower() in text for kw in filters.get("Earthly Project", [])):
            prompt = f"Summarize this project-related news in 2 sentences:\n\nTitle: {title}\nDescription: {description}"
            try:
                summary = client.responses.create(
                    model="gpt-4o-mini",
                    input=prompt
                ).output_text
            except Exception:
                summary = "⚠️ Summary unavailable."

            st.subheader(title)
            if published:
                published_fmt = datetime.fromisoformat(
                    published.replace("Z", "+00:00")
                ).strftime("%Y-%m-%d %H:%M")
                st.caption(f"{source} • Published: {published_fmt}")
            else:
                st.caption(f"{source}")
            st.write(summary)
            st.markdown(f"[Read full article]({link})")
            st.divider()

# ---------- TAB 2: REGISTRY NEWS ----------
# ---------- TAB 2: REGISTRY NEWS ----------
with tab2:
    st.subheader("🏛 Registry & Methodology News")

    from datetime import datetime, timedelta

    def fetch_articles(query, start_date, end_date):
        url = (
            f"https://newsapi.org/v2/everything?q={query}"
            f"&from={start_date}&to={end_date}"
            f"&sortBy=publishedAt&language=en&apiKey={NEWS_API_KEY}"
        )
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json().get("articles", [])
        except:
            return []

    # Define 2-year range
    today = datetime.utcnow()
    two_years_ago = today - timedelta(days=730)

    # Collect articles for each Registry keyword
    registry_articles = []
    for kw in filters.get("Registry News", []):
        results = fetch_articles(
            kw,
            start_date=two_years_ago.strftime("%Y-%m-%d"),
            end_date=today.strftime("%Y-%m-%d")
        )
        registry_articles.extend(results)

    # Deduplicate by URL
    seen = set()
    unique_articles = []
    for art in registry_articles:
        if art["url"] not in seen:
            unique_articles.append(art)
            seen.add(art["url"])

    # Sort newest first
    sorted_articles = sorted(
        unique_articles,
        key=lambda x: x.get("publishedAt", ""),
        reverse=True
    )

    # Display results
    for article in sorted_articles:
        title = article["title"]
        description = article.get("description", "")
        source = article["source"]["name"]
        link = article["url"]
        published = article.get("publishedAt", "")

        text = (title + " " + description).lower()

        if any(kw.lower() in text for kw in filters.get("Registry News", [])):
            prompt = f"Summarize this registry/methodology-related news in 2 sentences:\n\nTitle: {title}\nDescription: {description}"
            try:
                summary = client.responses.create(
                    model="gpt-4o-mini",
                    input=prompt
                ).output_text
            except Exception:
                summary = "⚠️ Summary unavailable."

            st.subheader(title)
            if published:
                published_fmt = datetime.fromisoformat(
                    published.replace("Z", "+00:00")
                ).strftime("%Y-%m-%d %H:%M")
                st.caption(f"{source} • Published: {published_fmt}")
            else:
                st.caption(f"{source}")
            st.write(summary)
            st.markdown(f"[Read full article]({link})")
            st.divider()
