"""
Dead simple auth for Streamlit Cloud
No detection, no checkboxes, just your damn app URL
"""

import streamlit as st
import pickle
from pathlib import Path
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

from config import GSC_SCOPES, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

# YOUR APP URL - THAT'S IT
REDIRECT_URI = "https://gsc-audit-agent.streamlit.app/"


class GSCAuthenticator:
    def __init__(self):
        pass
    
    def authenticate_with_service_account(self, service_account_file):
        st.error("Service accounts blocked by your org")
        return False
    
    def list_properties(self):
        if not st.session_state.get('gsc_service'):
            return []
        try:
            response = st.session_state.gsc_service.sites().list().execute()
            return [prop['siteUrl'] for prop in response.get('siteEntry', [])]
        except:
            return []
    
    def verify_property_access(self, property_url):
        properties = self.list_properties()
        return property_url in properties


def handle_authentication():
    st.sidebar.header("🔐 Google Search Console")
    
    # Already authenticated?
    if st.session_state.get('authenticated'):
        st.sidebar.success("✅ Connected")
        if st.sidebar.button("Disconnect"):
            st.session_state.clear()
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
    
    # OAuth flow
    query_params = st.experimental_get_query_params()
    
    if 'code' in query_params:
        # Got auth code - exchange for token
        code = query_params['code'][0]
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [REDIRECT_URI]
                }
            },
            scopes=GSC_SCOPES,
            redirect_uri=REDIRECT_URI  # ALWAYS USE YOUR STREAMLIT URL
        )
        
        try:
            flow.fetch_token(code=code)
            creds = flow.credentials
            
            token_file.parent.mkdir(exist_ok=True)
            with open(token_file, 'wb') as f:
                pickle.dump(creds, f)
            
            service = build('searchconsole', 'v1', credentials=creds)
            st.session_state.gsc_service = service
            st.session_state.authenticated = True
            
            st.experimental_set_query_params()
            st.rerun()
            
        except Exception as e:
            st.sidebar.error(f"Failed: {str(e)}")
            st.experimental_set_query_params()
    
    else:
        # Show connect button
        if st.sidebar.button("Connect to Google", type="primary", use_container_width=True):
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": GOOGLE_CLIENT_ID,
                        "client_secret": GOOGLE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [REDIRECT_URI]
                    }
                },
                scopes=GSC_SCOPES,
                redirect_uri=REDIRECT_URI  # ALWAYS USE YOUR STREAMLIT URL
            )
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                prompt='consent'
            )
            
            st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_url}">', unsafe_allow_html=True)
    
    return False
