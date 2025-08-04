"""
Authentication for GSC - Forces correct redirect URI
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
    
    def verify_property_access(self, property_url):
        """Verify property access"""
        properties = self.list_properties()
        return property_url in properties


def handle_authentication():
    """Authentication handler that forces correct redirect URI"""
    
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
    
    # FORCE the correct redirect URI based on where we're running
    # Check if we're on Streamlit Cloud by looking for the Streamlit Cloud domain
    query_params = st.experimental_get_query_params()
    
    # Get the current page URL to determine environment
    # If we have a 'code' parameter, we're in a callback and can see our URL
    if 'code' in query_params:
        # We're in OAuth callback - determine redirect URI from error or context
        # For now, try both URLs
        possible_urls = [
            "https://gsc-audit-agent.streamlit.app/",
            "http://localhost:8501/"
        ]
        
        st.sidebar.info("Completing authentication...")
        code = query_params['code'][0]
        
        # Try each possible redirect URI
        success = False
        last_error = None
        
        for redirect_uri in possible_urls:
            try:
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
                
                flow.fetch_token(code=code)
                creds = flow.credentials
                
                # Success! Save credentials
                with open(token_file, 'wb') as f:
                    pickle.dump(creds, f)
                
                service = build('searchconsole', 'v1', credentials=creds)
                st.session_state.gsc_service = service
                st.session_state.authenticated = True
                
                st.experimental_set_query_params()
                st.success("✅ Connected successfully!")
                success = True
                st.rerun()
                break
                
            except Exception as e:
                last_error = str(e)
                continue
        
        if not success:
            st.sidebar.error(f"Authentication failed: {last_error}")
            st.experimental_set_query_params()
    
    else:
        # Determine redirect URI for auth URL
        # Simple logic: if running in a Streamlit Cloud environment, use the cloud URL
        
        # Check multiple indicators
        is_cloud = any([
            os.getenv('STREAMLIT_SHARING_MODE'),  # Streamlit Cloud env var
            os.getenv('STREAMLIT_RUNTIME_ENV') == 'cloud',  # Another possible env var
            not os.path.exists('/home/adminuser/venv'),  # Local dev usually doesn't have this
        ])
        
        # Let user override if detection is wrong
        environment = st.sidebar.radio(
            "Where are you running this app?",
            ["Streamlit Cloud", "Local Development"],
            index=0 if is_cloud else 1,
            help="Select where you're currently running the app"
        )
        
        if environment == "Streamlit Cloud":
            redirect_uri = "https://gsc-audit-agent.streamlit.app/"
        else:
            redirect_uri = "http://localhost:8501/"
        
        st.sidebar.info(f"Using redirect URI: `{redirect_uri}`")
        
        # Show connect button
        if st.sidebar.button("Connect to Google", type="primary", use_container_width=True):
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
            
            # Use a meta refresh to redirect
            st.markdown(
                f'<meta http-equiv="refresh" content="0;url={auth_url}">',
                unsafe_allow_html=True
            )
            st.info("Redirecting to Google for authorization...")
    
    return False
