import os
import sys
from google import genai

def test_key(name, key):
    if not key:
        print(f"[-] {name} is NOT set.")
        return False
        
    masked = key[:6] + "..." + key[-4:] if len(key) > 10 else "Too short"
    print(f"\n[*] Testing {name}: {masked}")
    
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Say 'Key is valid!'"
        )
        print(f"[+] SUCCESS! Response: {response.text.strip()}")
        return True
    except Exception as e:
        print(f"[x] FAILED! Error: {str(e)}")
        return False

def main():
    print("=== Gemini API Key Diagnostics ===")
    
    gemini_key = os.environ.get("GEMINI_API_KEY")
    google_key = os.environ.get("GOOGLE_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    
    test_key("GEMINI_API_KEY (from env)", gemini_key)
    test_key("GOOGLE_API_KEY (from env)", google_key)
    test_key("OPENROUTER_API_KEY (from env)", openrouter_key)
    
    print("\n" + "="*34)
    print("If all env tests failed, please paste a key directly to test it:")
    user_key = input("Enter API key manually (or press Enter to exit): ").strip()
    if user_key:
        test_key("Manual API Key", user_key)

if __name__ == "__main__":
    main()
