import os
import time
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from dotenv import load_dotenv
from rapidfuzz import fuzz
from openai import OpenAI

# -------------------- Setup --------------------
load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="🌍 Earthly News Monitor", layout="wide")
st.title("🌍 Earthly News Monitor")
st.write("AI-powered news tracking with keyword + developer AND logic, quota management, and comprehensive diagnostics.")

# Cache OpenAI client
@st.cache_resource
def _client():
    return OpenAI(api_key=OPENAI_API_KEY)

client = _client()

# -------------------- Sidebar Controls --------------------
st.sidebar.header("⚙️ Settings")

# Dates
default_start = datetime.utcnow() - timedelta(days=365)
start_date = st.sidebar.date_input("Start date", default_start).strftime("%Y-%m-%d")
end_date = st.sidebar.date_input("End date", datetime.utcnow()).strftime("%Y-%m-%d")

# Data types
st.sidebar.subheader("Content types")
include_news = st.sidebar.checkbox("News", value=True)
include_pr = st.sidebar.checkbox("Press Releases", value=True)
include_blog = st.sidebar.checkbox("Blogs", value=True)
data_types = [t for t, on in (("news", include_news), ("pr", include_pr), ("blog", include_blog)) if on]
if not data_types:
    st.sidebar.warning("Select at least one content type.")
    data_types = ["news"]

# Summaries
summary_sentences = st.sidebar.slider("Summary length (sentences)", 1, 5, 2)

# API quota management
st.sidebar.subheader("API Quota Management")
max_articles_per_call = st.sidebar.slider("Articles per API call", 10, 100, 30)
max_pages_per_item = st.sidebar.slider("Pages per keyword item", 1, 5, 2)
max_keywords_per_run = st.sidebar.number_input("Max keywords per run", 1, 200, 50, 
    help="Limit keywords to preserve quota")
request_delay = st.sidebar.slider("Delay between calls (s)", 0.0, 2.0, 0.5, 0.1)

# Relevance
fuzzy_threshold = st.sidebar.slider("Relevance sensitivity (%)", 50, 90, 60)

# Debug
debug_mode = st.sidebar.checkbox("🔍 Debug mode", value=False)

# Show API usage estimate
if st.sidebar.button("📊 Estimate API Usage"):
    from collections import Counter
    total_items = sum(len(items) for items in filters.values())
    estimated_items = min(total_items, max_keywords_per_run * 2)
    estimated_calls = estimated_items * max_pages_per_item
    st.sidebar.info(f"Estimated API calls: {estimated_calls}\n({estimated_items} items × {max_pages_per_item} pages)")

# -------------------- Load keywords --------------------
@st.cache_data(ttl=86400)
def load_keywords():
    """Loads keywords and developers from CSV into structured list of dicts."""
    try:
        df = pd.read_csv("keywords.csv")
        if "Keyword" not in df.columns or "Category" not in df.columns:
            st.error("Error: 'keywords.csv' must contain 'Category' and 'Keyword' columns.")
            return {}
        
        if "Developer" not in df.columns:
            df["Developer"] = ""
        df["Developer"] = df["Developer"].fillna("")

        filters = {}
        for cat, group in df.groupby("Category"):
            keyword_list = []
            for _, row in group.iterrows():
                keyword = str(row["Keyword"]).strip()
                developer = str(row["Developer"]).strip()
                if keyword:
                    keyword_list.append({
                        "keyword": keyword,
                        "developer": developer if developer else None
                    })
            filters[cat] = keyword_list
        return filters
    except FileNotFoundError:
        st.error("Missing 'keywords.csv'. Create it with columns: Category, Keyword, Developer (optional)")
        return {}
    except Exception as e:
        st.error(f"Error loading keywords.csv: {e}")
        return {}

filters = load_keywords()

if debug_mode:
    st.sidebar.subheader("📋 Loaded Keywords")
    for cat, items in filters.items():
        st.sidebar.write(f"**{cat}**: {len(items)} items")
        with st.sidebar.expander(f"Show {cat} items"):
            for idx, item in enumerate(items[:5], 1):
                if item["developer"]:
                    st.sidebar.write(f"{idx}. {item['keyword']} AND {item['developer']}")
                else:
                    st.sidebar.write(f"{idx}. {item['keyword']}")

# -------------------- Helpers --------------------
def fuzzy_match(text, keyword, threshold=65):
    """Multi-strategy fuzzy matching for robust relevance detection."""
    text_lower = text.lower()
    key_lower = keyword.lower()
    if key_lower in text_lower:
        return True
    return (
        fuzz.ratio(key_lower, text_lower) >= threshold or
        fuzz.partial_ratio(key_lower, text_lower) >= threshold or
        fuzz.token_set_ratio(key_lower, text_lower) >= threshold
    )

def do_request(payload, retry=0):
    """POST request with exponential backoff and enhanced error handling."""
    url = "https://eventregistry.org/api/v1/article/getArticles"
    headers = {"Content-Type": "application/json"}
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if r.status_code in (429, 503) and retry < 3:
            wait = 2 ** (retry + 1)
            if debug_mode:
                st.sidebar.warning(f"Rate limited (HTTP {r.status_code}). Retrying in {wait}s...")
            time.sleep(wait)
            return do_request(payload, retry + 1)
        
        if r.status_code == 403:
            st.sidebar.error("API quota exceeded. Check your Event Registry dashboard.")
            return None
            
        r.raise_for_status()
        return r.json()
        
    except requests.HTTPError as e:
        st.sidebar.error(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
        return None
    except requests.RequestException as e:
        st.sidebar.error(f"Request failed: {e}")
        return None

# -------------------- Diagnostic Tests --------------------
def test_kasigau_diagnostic():
    """Quick diagnostic test for Kasigau keyword."""
    if debug_mode:
        st.sidebar.subheader("🎯 Kasigau Diagnostic")
        
        payload = {
            "action": "getArticles",
            "keyword": "Kasigau",
            "keywordLoc": "body,title",
            "articlesSortBy": "date",
            "articlesSortByAsc": False,
            "articlesCount": 10,
            "dataType": ["news", "pr", "blog"],
            "lang": ["eng"],
            "resultType": "articles",
            "dateStart": "2023-11-01",
            "dateEnd": "2023-11-30",
            "apiKey": NEWS_API_KEY,
        }
        
        data = do_request(payload)
        
        if data and "articles" in data:
            results = data["articles"].get("results", [])
            total = data["articles"].get("totalResults", 0)
            st.sidebar.success(f"Kasigau test: {len(results)}/{total} results")
        else:
            st.sidebar.error("Kasigau test failed")

# -------------------- Main Fetching Logic --------------------
def fetch_articles_for_items(keyword_items, start_date, end_date, label):
    """Fetch articles with proper AND logic and quota management."""
    if not keyword_items:
        return []

    # Limit items to preserve quota
    limited_items = keyword_items[:max_keywords_per_run]
    if len(keyword_items) > max_keywords_per_run:
        st.warning(f"Limiting to first {max_keywords_per_run} {label} items to preserve quota.")

    all_results = []
    total_calls = 0
    successful_items = 0
    failed_items = 0

    # Test Kasigau if present
    if debug_mode and any(item["keyword"].lower() == "kasigau" for item in limited_items):
        test_kasigau_diagnostic()

    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, item in enumerate(limited_items):
        keyword, developer = item["keyword"], item["developer"]
        
        status_text.text(f"Fetching {label}: {keyword}" + (f" + {developer}" if developer else ""))
        progress_bar.progress((idx + 1) / len(limited_items))
        
        base_payload = {
            "action": "getArticles",
            "keywordLoc": "body,title",
            "articlesSortBy": "date",
            "articlesSortByAsc": False,
            "articlesCount": max_articles_per_call,
            "dataType": data_types,
            "lang": ["eng"],
            "resultType": "articles",
            "dateStart": start_date,
            "dateEnd": end_date,
            "isDuplicateFilter": "skipDuplicates",
            "startSourceRankPercentile": 0,
            "endSourceRankPercentile": 100,
            "apiKey": NEWS_API_KEY,
        }
        
        # API response optimization
        optimization_params = {
            "includeArticleTitle": True,
            "includeArticleBasicInfo": True,
            "includeArticleBody": True,
            "includeArticleEventUri": False,
            "includeArticleSocialScore": False,
            "includeArticleSentiment": False,
            "includeArticleConcepts": False,
            "includeArticleCategories": False,
            "includeArticleLocation": False,
            "includeArticleImage": False,
            "includeArticleAuthors": True,
            "includeArticleVideos": False,
            "includeArticleLinks": False,
            "includeArticleExtractedDates": False,
            "includeArticleDuplicateList": False,
            "includeArticleOriginalArticle": False,
            "includeSourceTitle": True,
            "includeSourceDescription": False,
            "includeSourceLocation": False,
            "includeSourceRanking": False,
        }
        base_payload.update(optimization_params)

        if developer:
            base_payload["keyword"] = [keyword, developer]
            base_payload["keywordOper"] = "and"
            if debug_mode:
                st.sidebar.write(f"🔄 '{keyword}' AND '{developer}'")
        else:
            base_payload["keyword"] = keyword
            if debug_mode:
                st.sidebar.write(f"🔄 '{keyword}'")

        item_had_results = False
        for page in range(1, max_pages_per_item + 1):
            payload = {**base_payload, "articlesPage": page}
            total_calls += 1
            
            data = do_request(payload)
            
            if request_delay > 0:
                time.sleep(request_delay)
            
            if not data:
                break
            
            results = data.get("articles", {}).get("results", [])
            
            if debug_mode:
                total_available = data.get("articles", {}).get("totalResults", 0)
                st.sidebar.write(f"  Page {page}: {len(results)}/{total_available}")
            
            if not results:
                break
            
            item_had_results = True
            all_results.extend(results)
            
            if len(results) < max_articles_per_call:
                break
        
        if item_had_results:
            successful_items += 1
        else:
            failed_items += 1

    progress_bar.empty()
    status_text.empty()

    # Deduplicate
    seen_urls = set()
    unique_articles = [
        art for art in all_results 
        if art.get("url") and (url := art.get("url")) not in seen_urls and not seen_urls.add(url)
    ]

    if debug_mode:
        st.sidebar.success(
            f"Fetched {len(all_results)} raw → {len(unique_articles)} unique\n"
            f"({successful_items} successful, {failed_items} failed, {total_calls} API calls)"
        )

    return unique_articles

# -------------------- Summarization --------------------
def batch_summarize(articles, sentences=2):
    """Batch summarize articles using OpenAI with robust parsing."""
    if not articles:
        return []
    
    out = []
    batch_size = 5
    
    for i in range(0, len(articles), batch_size):
        group = articles[i:i+batch_size]
        prompt = [
            f"Summarize each article below in exactly {sentences} sentences.",
            "Respond ONLY in this format:",
            *(f"SUMMARY {j+1}: <summary>" for j in range(len(group))),
            "",
            "ARTICLES:",
        ]
        for idx, art in enumerate(group, start=1):
            title = art.get("title", "Untitled")
            body = (art.get("body") or "")[:800]
            prompt.append(f"Article {idx} — Title: {title}\nBody: {body}\n")
        
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "\n".join(prompt)}],
                max_tokens=800,
                temperature=0.2,
            )
            txt = resp.choices[0].message.content or ""
            lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
            summaries, cur = [], None
            
            for ln in lines:
                if ln.upper().startswith("SUMMARY"):
                    if cur is not None:
                        summaries.append(cur.strip())
                    cur = ln.split(":", 1)[1].strip() if ":" in ln else ""
                elif cur is not None:
                    cur += " " + ln
            
            if cur:
                summaries.append(cur.strip())
            
            if not summaries:
                summaries = [s.strip() for s in txt.split("\n\n") if s.strip()]
            
            while len(summaries) < len(group):
                summaries.append("Summary not available.")
            
            out.extend(summaries[:len(group)])
            
        except Exception as e:
            out.extend([f"Summary unavailable: {str(e)[:50]}" for _ in group])
    
    return out

# -------------------- Filtering & Rendering --------------------
def filter_relevant(articles, keyword_items, threshold):
    """Post-filter articles with fuzzy matching for AND logic verification."""
    if not articles:
        return []
    
    relevant = []
    for art in articles:
        text = (art.get("title", "") + " " + art.get("body", "")).lower()
        
        is_match = False
        for item in keyword_items:
            keyword, developer = item["keyword"], item["developer"]
            keyword_match = fuzzy_match(text, keyword, threshold)
            
            if developer:
                if keyword_match and fuzzy_match(text, developer, threshold):
                    is_match = True
                    break
            elif keyword_match:
                is_match = True
                break
        
        if is_match:
            relevant.append(art)
    
    return relevant

def render_articles(articles, keyword_items, label):
    """Render filtered and summarized articles."""
    if not articles:
        st.info(f"No {label.lower()} articles found.")
        return

    articles = sorted(articles, key=lambda x: x.get("dateTimePub", ""), reverse=True)
    relevant = filter_relevant(articles, keyword_items, fuzzy_threshold)

    if debug_mode:
        st.write(f"📊 **{label}**: {len(articles)} fetched → {len(relevant)} relevant")

    if not relevant:
        st.warning(f"No relevant {label.lower()} articles after filtering. Try lowering relevance sensitivity.")
        return

    with st.spinner(f"Summarizing {len(relevant)} articles..."):
        summaries = batch_summarize(relevant, sentences=summary_sentences)

    for i, art in enumerate(relevant):
        title = art.get("title", "Untitled")
        url = art.get("url", "#")
        pub = art.get("dateTimePub", "")
        src = (art.get("source") or {}).get("title", "Unknown")

        st.subheader(title)
        st.caption(f"{src} • {pub}")
        st.write(summaries[i] if i < len(summaries) else (art.get("body", "")[:300] + "..."))
        if url != "#":
            st.markdown(f"[Read full article]({url})")
        st.divider()

# -------------------- Main UI --------------------
def run_tab_logic(category_name):
    """Execute search and rendering logic for a category."""
    keyword_items = filters.get(category_name, [])
    if not keyword_items:
        st.warning(f"No '{category_name}' keywords found in keywords.csv.")
        return
    
    with st.spinner(f"Fetching {category_name} articles..."):
        fetched_articles = fetch_articles_for_items(keyword_items, start_date, end_date, category_name)
    
    render_articles(fetched_articles, keyword_items, category_name)

tab1, tab2 = st.tabs(["🌱 Earthly Projects", "🏛 Registry & Methodologies"])

with tab1:
    st.subheader("🌱 Earthly Project News")
    run_tab_logic("Earthly Project")

with tab2:
    st.subheader("🏛 Registry & Methodology News")
    run_tab_logic("Registry News")
    