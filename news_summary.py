import requests
import os
from openai import OpenAI

# 🔑 Keys
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
            

client = OpenAI(api_key=OPENAI_API_KEY)

# Fetch environment/climate/EU news
url = f"https://newsapi.org/v2/everything?q=environment+climate+EU&sortBy=publishedAt&language=en&apiKey={NEWS_API_KEY}"
response = requests.get(url)
data = response.json()

print("\n🌍 Latest Environment & Climate News with AI Summaries:\n")

for i, article in enumerate(data.get("articles", [])[:5], start=1):
    title = article["title"]
    description = article.get("description", "")
    source = article["source"]["name"]
    link = article["url"]

    # 🧠 Summarize headline + description
    prompt = f"Summarize this news in 2 sentences for a business audience:\n\nTitle: {title}\nDescription: {description}"

    summary = client.responses.create(
        model="gpt-4o-mini",
        input=prompt
    ).output_text

    print(f"{i}. {title} ({source})")
    print(f"   Summary: {summary}")
    print(f"   {link}\n")
