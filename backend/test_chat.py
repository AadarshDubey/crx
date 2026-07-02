import urllib.request
import json
import time

BASE_URL = "http://localhost:8000"

PROMPTS = [
    "What is the latest news about Ethereum?",
    "What are people tweeting about Bitcoin? Specifically @cz_binance",
    "Summarize the sentiment for Solana based on recent news.",
    "What did @saylor say about Bitcoin recently?",
    "Can you summarize the recent news about XRP?"
]

def test_chat_stream():
    for prompt in PROMPTS:
        print(f"\n{'='*50}")
        print(f"Prompt: {prompt}")
        print(f"{'='*50}\n")
        
        payload = json.dumps({
            "message": prompt,
            "conversation_history": [],
            "use_context": True
        }).encode('utf-8')
        
        req = urllib.request.Request(
            f"{BASE_URL}/api/chat/stream",
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            },
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                for line in response:
                    line = line.decode('utf-8').strip()
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "status":
                                print(f"[STATUS] {data['message']}")
                            elif data.get("type") == "chunk":
                                print(data["content"], end="", flush=True)
                            elif data.get("type") == "sources":
                                print("\n\n[SOURCES]")
                                for s in data["sources"]:
                                    print(f"  - {s.get('source_type', 'unknown')} | {s.get('id', 'no id')} | {s.get('url', 'no url')}")
                            elif data.get("type") == "error":
                                print(f"\n[ERROR] {data['message']}")
                            elif data.get("type") == "done":
                                print("\n[DONE]")
                        except json.JSONDecodeError:
                            pass
            print("\n")
        except Exception as e:
            print(f"Failed to query: {e}")

if __name__ == "__main__":
    test_chat_stream()
