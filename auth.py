"""
Simplified OAuth Authentication for GSC
This version focuses on direct OAuth connection without workarounds
"""

import streamlit as st
import os
import pickle
from pathlib import Path
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Import config
try:
    from config import GSC_SCOPES, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, ERROR_MESSAGES, SUCCESS_MESSAGES
except ImportError:
    # Fallback if config is not properly set
    GSC_SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    ERROR_MESSAGES = {'auth_failed': 'Authentication failed'}
    SUCCESS_MESSAGES = {'auth_success': 'Authentication successful'}


def handle_authentication():
    """Simple, direct OAuth authentication"""
    
    st.sidebar.header("🔐 Google Search Console Authentication")
    
    # Check if already authenticated
    if st.session_state.get('authenticated'):
        st.sidebar.success("✅ Connected to Google Search Console")
        if st.sidebar.button("Disconnect"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        return True
    
    # Check for saved credentials
    token_file = Path('.token/gsc_token.pickle')
    if token_file.exists():
        try:
            with open(token_file, 'rb') as f:
                creds = pickle.load(f)
            
            # If valid, use them
            if creds and creds.valid:
                service = build('searchconsole', 'v1', credentials=creds)
                st.session_state.gsc_service = service
                st.session_state.authenticated = True
                return True
            
            # If expired, refresh
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_file, 'wb') as f:
                    pickle.dump(creds, f)
                service = build('searchconsole', 'v1', credentials=creds)
                st.session_state.gsc_service = service
                st.session_state.authenticated = True
                return True
        except:
            pass
    
    # Need to authenticate
    st.sidebar.markdown("### Connect to Google Search Console")
    
    # Determine redirect URI
    if st.sidebar.checkbox("I'm using Streamlit Cloud"):
        redirect_uri = st.sidebar.text_input(
            "Your app URL (EXACT match required):",
            placeholder="https://yourapp.streamlit.app/",
            help="⚠️ Must match EXACTLY what's in Google Cloud Console"
        )
    else:
        redirect_uri = "http://localhost:8501/"
        st.sidebar.info(f"Using redirect URI: {redirect_uri}")
    
    # Check for OAuth callback
    try:
        # Try modern Streamlit API first
        params = dict(st.query_params)
    except (AttributeError, Exception):
        try:
            # Fall back to experimental API
            params_raw = st.experimental_get_query_params()
            params = {k: v[0] if isinstance(v, list) else v for k, v in params_raw.items()}
        except (AttributeError, Exception):
            params = {}
    
    if 'code' in params:
        # We have an auth code!
        code = params['code']
        
        # Create flow to exchange code for credentials
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
            # Exchange code for token
            flow.fetch_token(code=code)
            creds = flow.credentials
            
            # Save credentials
            token_file.parent.mkdir(exist_ok=True)
            with open(token_file, 'wb') as f:
                pickle.dump(creds, f)
            
            # Build service
            service = build('searchconsole', 'v1', credentials=creds)
            
            # Test it works
            sites = service.sites().list().execute()
            
            # Success!
            st.session_state.gsc_service = service
            st.session_state.authenticated = True
            
            # Clear URL parameters
            try:
                st.query_params.clear()
            except AttributeError:
                try:
                    st.experimental_set_query_params()
                except:
                    pass
            
            st.success("✅ Successfully connected!")
            st.balloons()
            st.rerun()
            
        except Exception as e:
            st.sidebar.error(f"Authentication failed: {str(e)}")
            st.sidebar.error("Check that your redirect URI matches EXACTLY")
    
    else:
        # Show connect button
        if redirect_uri and st.sidebar.button("🔗 Connect to Google", type="primary", use_container_width=True):
            # Create OAuth flow
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
            
            # Generate auth URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            # Redirect to Google
            st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_url}">', unsafe_allow_html=True)
    
    return False


class GSCAuthenticator:
    """Simple authenticator class for compatibility"""
    
    def list_properties(self):
        """List GSC properties"""
        if not st.session_state.get('gsc_service'):
            return []
        
        try:
            response = st.session_state.gsc_service.sites().list().execute()
            return [site['siteUrl'] for site in response.get('siteEntry', [])]
        except:
            return []
