import requests
import os

# 🔑 Your NewsAPI key
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# Search for environment/climate/EU news (sorted by newest)
url = f"https://newsapi.org/v2/everything?q=environment+climate+EU&sortBy=publishedAt&language=en&apiKey={API_KEY}"

response = requests.get(url)
data = response.json()

# Print the first 5 headlines
print("\n🌍 Latest Environment & Climate News:\n")
for i, article in enumerate(data.get("articles", [])[:5], start=1):
    print(f"{i}. {article['title']} ({article['source']['name']})")
    print(article["url"])
    print()

