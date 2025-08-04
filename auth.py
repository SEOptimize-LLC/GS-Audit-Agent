"""
OAuth Diagnostic Script
Run this to find EXACTLY what's wrong with your OAuth setup
"""

import os
from dotenv import load_dotenv
import requests
import json
from urllib.parse import urlencode, quote

load_dotenv()

print("=" * 60)
print("GOOGLE OAUTH DIAGNOSTIC")
print("=" * 60)

# 1. Check credentials exist
client_id = os.getenv('GOOGLE_CLIENT_ID', '')
client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '')

print("\n1. CHECKING CREDENTIALS:")
print(f"   Client ID found: {'✅' if client_id else '❌'}")
print(f"   Client Secret found: {'✅' if client_secret else '❌'}")

if not client_id or not client_secret:
    print("\n❌ MISSING CREDENTIALS - Add them to .env file")
    exit(1)

print(f"\n   Client ID: {client_id}")

# 2. Test OAuth endpoint
print("\n2. TESTING OAUTH CONFIGURATION:")

# Build auth URL manually
params = {
    'client_id': client_id,
    'redirect_uri': 'http://localhost:8501/',
    'response_type': 'code',
    'scope': 'https://www.googleapis.com/auth/webmasters.readonly',
    'access_type': 'offline',
    'prompt': 'consent'
}

auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

print(f"\n   Generated Auth URL:")
print(f"   {auth_url}")

# 3. Test if client ID is valid format
print("\n3. VALIDATING CLIENT ID FORMAT:")
if client_id.endswith('.apps.googleusercontent.com'):
    print("   ✅ Client ID format is correct")
else:
    print("   ❌ Client ID format is WRONG!")
    print("   Should end with: .apps.googleusercontent.com")

# 4. Common issues check
print("\n4. COMMON ISSUES TO CHECK IN GOOGLE CLOUD CONSOLE:")
print("\n   OAuth Consent Screen:")
print("   □ Is it configured? (Required!)")
print("   □ Is it in 'Testing' or 'Production' mode?")
print("   □ If Testing: Are test users added?")
print("   □ Is your email in test users?")

print("\n   OAuth 2.0 Client ID:")
print("   □ Type: Must be 'Web application' (not Desktop!)")
print("   □ Authorized redirect URIs must include:")
print("     - http://localhost:8501/")
print("     - http://localhost:8501")
print("     - Your production URL (if using Streamlit Cloud)")

print("\n   APIs:")
print("   □ Is 'Google Search Console API' enabled?")

print("\n5. TESTING AUTH URL:")
print("\n   Copy this URL and paste in your browser:")
print(f"\n   {auth_url}\n")

print("   Expected behavior:")
print("   - You should see Google's sign-in page")
print("   - After signing in, you see consent screen")
print("   - After consent, redirected to localhost:8501/?code=...")

print("\n   If you see 'Access blocked: This app's request is invalid':")
print("   → Your OAuth client is misconfigured in Google Cloud Console")
print("   → Most likely: Wrong client type or missing consent screen")

print("\n6. QUICK FIX STEPS:")
print("   1. Go to: https://console.cloud.google.com")
print("   2. Select your project")
print("   3. Go to 'APIs & Services' > 'OAuth consent screen'")
print("   4. Configure it (if not done)")
print("   5. Go to 'APIs & Services' > 'Credentials'")
print("   6. Click your OAuth 2.0 Client ID")
print("   7. Verify it's type 'Web application'")
print("   8. Add these Authorized redirect URIs:")
print("      - http://localhost:8501/")
print("      - http://localhost:8501")
print("      - https://YOUR-APP.streamlit.app/")
print("      - https://YOUR-APP.streamlit.app")

print("\n" + "=" * 60)
