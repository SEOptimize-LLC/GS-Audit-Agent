"""
Simple Authentication for Streamlit Cloud
No auto-detection, just straightforward OAuth
"""

import streamlit as st
import os
import pickle
from pathlib import Path
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

from config import (
    GSC_SCOPES, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    ERROR_MESSAGES, SUCCESS_MESSAGES
)

# CHANGE THIS TO YOUR ACTUAL STREAMLIT APP URL
STREAMLIT_APP_URL = "https://gsc-audit-agent.streamlit.app/"  # <-- PUT YOUR URL HERE!


class GSCAuthenticator:
    """Simple authenticator for GSC"""
    
    def __init__(self):
        self.token_file = Path('.token/gsc_token.pickle')
        self.token_file.parent.mkdir(exist_ok=True)
    
    def authenticate_with_service_account(self, service_account_file):
        st.error("Service Account authentication is blocked by your organization.")
        return False
    
    def list_properties(self):
        if not st.session_state.get('gsc_service'):
            return []
        try:
            response = st.session_state.gsc_service.sites().list().execute()
            return [prop['siteUrl'] for prop in response.get('siteEntry', [])]
        except:
            return []


def handle_authentication():
    """Simple authentication handler"""
    
    st.sidebar.header("🔐 Google Search Console")
    
    # Already authenticated?
    if st.session_state.get('authenticated'):
        st.sidebar.success("✅ Connected")
        if st.sidebar.button("Disconnect"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            token_file = Path('.token/gsc_token.pickle')
            if token_file.exists():
                token_file.unlink()
            st.rerun()
        return True
    
    # Check saved credentials
    token_file = Path('.token/gsc_token.pickle')
    if token_file.exists():
        try:
            with open(token_file, 'rb') as f:
                creds = pickle.load(f)
            if creds and creds.valid:
                service = build('searchconsole', 'v1', credentials=creds)
                st.session_state.gsc_service = service
                st.session_state.authenticated = True
                return True
            elif creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_file, 'wb') as f:
                    pickle.dump(creds, f)
                service = build('searchconsole', 'v1', credentials=creds)
                st.session_state.gsc_service = service
                st.session_state.authenticated = True
                return True
        except:
            pass
    
    # Determine redirect URI
    if os.getenv('STREAMLIT_SHARING_MODE') or st.sidebar.checkbox("Using Streamlit Cloud"):
        redirect_uri = STREAMLIT_APP_URL
        st.sidebar.info(f"Using redirect URI: {redirect_uri}")
    else:
        redirect_uri = "http://localhost:8501/"
        st.sidebar.info("Using local redirect URI")
    
    # Check for OAuth callback
    query_params = st.experimental_get_query_params()
    
    if 'code' in query_params:
        st.sidebar.info("Completing authentication...")
        
        code = query_params['code'][0]
        
        # Create flow and exchange code
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=GSC_SCOPES,
            redirect_uri=redirect_uri
        )
        
        try:
            flow.fetch_token(code=code)
            creds = flow.credentials
            
            # Save and use
            with open(token_file, 'wb') as f:
                pickle.dump(creds, f)
            
            service = build('searchconsole', 'v1', credentials=creds)
            st.session_state.gsc_service = service
            st.session_state.authenticated = True
            
            st.experimental_set_query_params()
            st.success("✅ Connected successfully!")
            st.rerun()
            
        except Exception as e:
            st.sidebar.error(f"Failed: {str(e)}")
            st.sidebar.error(f"Make sure this EXACT URL is in Google Cloud Console: {redirect_uri}")
            st.experimental_set_query_params()
    
    else:
        # Show connect button
        st.sidebar.markdown("### Connect to Google")
        
        with st.sidebar.expander("⚠️ Before connecting"):
            st.markdown(f"""
            **Add this EXACT URL to Google Cloud Console:**
            ```
            {redirect_uri}
            ```
            
            Go to APIs & Services → Credentials → Your OAuth Client → Authorized redirect URIs
            """)
        
        if st.sidebar.button("Connect", type="primary", use_container_width=True):
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": GOOGLE_CLIENT_ID,
                        "client_secret": GOOGLE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [redirect_uri]
                    }
                },
                scopes=GSC_SCOPES,
                redirect_uri=redirect_uri
            )
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                prompt='consent'
            )
            
            st.sidebar.markdown(f"[Click here to authorize]({auth_url})")
    
    return False
