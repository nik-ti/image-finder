import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test_perplexity():
    key = os.getenv("PERPLEXITY_API_KEY")
    if not key:
        print("❌ PERPLEXITY_API_KEY not found")
        return

    print(f"Testing Perplexity Key: {key[:10]}...")
    
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar",
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 5
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                print("✅ Perplexity API is working")
            else:
                print(f"❌ Perplexity API failed: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_perplexity())
