import os
import json
import urllib.request
import urllib.error

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

def call_gemini(prompt: str) -> str:
    # Get API key from env var (preferred) or hard-code as a fallback
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    # Optionally: api_key = "YOUR_API_KEY_HERE"   # for quick testing only

    if not api_key:
        return "Gemini API key is not configured."

    url = f"{GEMINI_ENDPOINT}?key={api_key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json"
    }

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            resp_data = resp.read().decode("utf-8")
        resp_json = json.loads(resp_data)

        # Gemini responses look like: { "candidates": [ { "content": { "parts": [ { "text": "..." } ] } } ] }
        candidates = resp_json.get("candidates", [])
        if not candidates:
            return "Gemini did not return any candidates."

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            return "Gemini returned an empty message."

        text = parts[0].get("text", "").strip()
        return text or "Gemini returned no text."

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        print("Gemini HTTP error:", e.code, body)
        return "Gemini returned an error."
    except Exception as e:
        print("Gemini error:", repr(e))
        return "I couldn’t reach Gemini."
