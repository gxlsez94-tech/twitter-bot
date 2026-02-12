from fastapi import FastAPI
import feedparser
import httpx
from typing import Optional, Dict
import asyncio
import json
from pathlib import Path

app = FastAPI()

# Reddit subreddits to monitor
SUBREDDITS = ["conspiracy", "HighStrangeness", "occult", "UFOs", "aliens"]

# Make.com webhook URL
MAKE_WEBHOOK_URL = "PASTE_YOUR_WEBHOOK_URL_HERE"  # Update this!

# Track sent posts to avoid duplicates
SENT_POSTS_FILE = Path("sent_posts.json")

def load_sent_posts():
    if SENT_POSTS_FILE.exists():
        return json.loads(SENT_POSTS_FILE.read_text())
    return {}

def save_sent_post(subreddit: str, post_url: str):
    sent = load_sent_posts()
    sent[subreddit] = post_url
    SENT_POSTS_FILE.write_text(json.dumps(sent, indent=2))

def is_already_sent(subreddit: str, post_url: str) -> bool:
    sent = load_sent_posts()
    return sent.get(subreddit) == post_url

async def fetch_latest_reddit_post(subreddit: str) -> Dict:
    """Fetch the latest post from a subreddit using RSS"""
    print(f"Fetching latest post from r/{subreddit}...")
    
    try:
        # Reddit RSS URL format
        rss_url = f"https://www.reddit.com/r/{subreddit}/.rss"
        
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            # Reddit requires a user agent
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = await client.get(rss_url, headers=headers)
            
            if response.status_code == 200:
                feed = feedparser.parse(response.text)
                
                if feed.entries:
                    entry = feed.entries[0]  # Get the latest post
                    
                    # Clean up the text (Reddit RSS includes HTML)
                    post_text = entry.get("summary", "")
                    if len(post_text) > 500:
                        post_text = post_text[:500] + "..."
                    
                    print(f"SUCCESS: Got latest post from r/{subreddit}")
                    
                    return {
                        "subreddit": subreddit,
                        "title": entry.get("title", ""),
                        "text": post_text,
                        "url": entry.get("link", ""),
                        "author": entry.get("author", ""),
                        "published": entry.get("published", ""),
                        "source": "reddit"
                    }
                else:
                    print(f"No posts found in r/{subreddit}")
                    return {"subreddit": subreddit, "error": "No posts found"}
            else:
                print(f"Failed to fetch r/{subreddit}: Status {response.status_code}")
                return {"subreddit": subreddit, "error": f"HTTP {response.status_code}"}
                
    except Exception as e:
        print(f"Error fetching r/{subreddit}: {e}")
        return {"subreddit": subreddit, "error": str(e)}

async def send_to_make(post_data: Dict):
    """Send post data to Make.com webhook"""
    if "error" in post_data:
        return {"status": "skipped", "reason": "error"}
    
    subreddit = post_data["subreddit"]
    post_url = post_data["url"]
    
    # Check if already sent
    if is_already_sent(subreddit, post_url):
        print(f"Already sent: r/{subreddit}")
        return {"status": "skipped", "reason": "duplicate"}
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                MAKE_WEBHOOK_URL,
                json=post_data
            )
            
            if response.status_code == 200:
                save_sent_post(subreddit, post_url)
                print(f"Sent to Make.com: r/{subreddit}")
                return {"status": "sent"}
            else:
                print(f"Failed to send: {response.status_code}")
                return {"status": "failed", "code": response.status_code}
                
    except Exception as e:
        print(f"Error sending to Make.com: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/latest")
async def get_latest_posts():
    """Fetch latest posts from all subreddits"""
    tasks = [fetch_latest_reddit_post(sub) for sub in SUBREDDITS]
    results_list = await asyncio.gather(*tasks)
    
    return {sub: result for sub, result in zip(SUBREDDITS, results_list)}

@app.get("/check-and-send")
async def check_and_send_to_make():
    """Fetch latest posts and send NEW ones to Make.com"""
    tasks = [fetch_latest_reddit_post(sub) for sub in SUBREDDITS]
    results_list = await asyncio.gather(*tasks)
    
    # Send each NEW post to Make.com
    send_results = []
    for post_data in results_list:
        result = await send_to_make(post_data)
        send_results.append(result)
    
    sent_count = len([r for r in send_results if r.get("status") == "sent"])
    skipped_count = len([r for r in send_results if r.get("status") == "skipped"])
    error_count = len([r for r in send_results if r.get("status") in ["error", "failed"]])
    
    return {
        "status": "Complete",
        "sent": sent_count,
        "skipped": skipped_count,
        "errors": error_count,
        "details": send_results
    }

@app.get("/test-make")
async def test_make_webhook():
    """Send fake test data to Make.com"""
    test_post = {
        "subreddit": "conspiracy",
        "title": "BREAKING: Newly declassified documents reveal shocking connection between...",
        "text": "This is a test post to verify the Make.com integration is working properly. The full story unfolds as we examine the evidence that has been hidden for decades.",
        "url": "https://www.reddit.com/r/conspiracy/comments/test123",
        "author": "test_user",
        "published": "Thu, 13 Feb 2025 12:00:00 GMT",
        "source": "reddit_test"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                MAKE_WEBHOOK_URL,
                json=test_post
            )
            return {
                "status": "Test sent",
                "response_code": response.status_code,
                "data_sent": test_post
            }
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
def home():
    return {
        "status": "Online - Reddit RSS Bot",
        "subreddits": SUBREDDITS,
        "endpoints": {
            "/latest": "Get latest posts from all subreddits",
            "/check-and-send": "Check for new posts and send to Make.com",
            "/test-make": "Send test data to Make.com"
        }
    }