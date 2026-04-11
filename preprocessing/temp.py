import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-reasoner",
    max_tokens=3000,
    temperature=0,
    messages=[{"role": "user", "content": "请推断这本书的书名。书评：读刘墉的文章，总能让我看到一个快乐的父亲。只返回书名，不超过20字。"}]
)

print("content:", response.choices[0].message.content)
print("reasoning长度:", len(getattr(response.choices[0].message, "reasoning_content", "") or ""))