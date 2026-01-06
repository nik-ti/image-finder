import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def main():
    api_key = os.getenv("PERPLEXITY_API_KEY")
    print(f"Checking key: {api_key[:10]}...")
    
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "sonar",
        "messages": [{"role": "user", "content": "ping"}]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")

if __name__ == "__main__":
    asyncio.run(main())
