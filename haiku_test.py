import os
from openai import OpenAI

client = OpenAI(
  OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
)

response = client.responses.create(
  model="gpt-4o-mini",
  input="write a haiku about AI",
)

print(response.output_text)
