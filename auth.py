"""
Authentication module for Google Search Console API
Compatible with Streamlit 1.29.0
"""

import streamlit as st
import os
import pickle
from pathlib import Path
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

# Import config
from config import (
    GSC_SCOPES, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    ERROR_MESSAGES, SUCCESS_MESSAGES
)


class GSCAuthenticator:
    """Handles authentication for Google Search Console API"""
    
    def __init__(self):
        self.credentials = None
        self.service = None
        self.token_file = Path('.token/gsc_token.pickle')
        self.token_file.parent.mkdir(exist_ok=True)
    
    def authenticate_with_service_account(self, service_account_file):
        """Service accounts are blocked by organization policy"""
        st.error("Service Account authentication is blocked by your organization policy. Please use OAuth 2.0.")
        return False
    
    def list_properties(self):
        """List all Search Console properties"""
        if not st.session_state.get('gsc_service'):
            return []
        
        try:
            response = st.session_state.gsc_service.sites().list().execute()
            properties = response.get('siteEntry', [])
            return [prop['siteUrl'] for prop in properties]
        except HttpError as e:
            st.error(f"Error listing properties: {str(e)}")
            return []
    
    def verify_property_access(self, property_url):
        """Verify property access"""
        properties = self.list_properties()
        return property_url in properties


def handle_authentication():
    """Main authentication handler for Streamlit UI"""
    
    st.sidebar.header("🔐 Authentication")
    
    # Check if already authenticated
    if st.session_state.get('authenticated'):
        st.sidebar.success("✅ Connected to Google Search Console")
        
        if st.sidebar.button("Logout"):
            # Clear session state
            for key in list(st.session_state.keys()):
                if key in ['credentials', 'gsc_service', 'authenticated', 'auth_method']:
                    del st.session_state[key]
            
            # Remove saved token
            token_file = Path('.token/gsc_token.pickle')
            if token_file.exists():
                token_file.unlink()
            
            st.rerun()
        
        return True
    
    # Try to load saved credentials
    token_file = Path('.token/gsc_token.pickle')
    if token_file.exists():
        try:
            with open(token_file, 'rb') as f:
                credentials = pickle.load(f)
            
            # Check if valid
            if credentials and credentials.valid:
                service = build('searchconsole', 'v1', credentials=credentials)
                st.session_state.gsc_service = service
                st.session_state.authenticated = True
                st.session_state.credentials = credentials
                return True
            
            # Try to refresh if expired
            elif credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                with open(token_file, 'wb') as f:
                    pickle.dump(credentials, f)
                
                service = build('searchconsole', 'v1', credentials=credentials)
                st.session_state.gsc_service = service
                st.session_state.authenticated = True
                st.session_state.credentials = credentials
                return True
                
        except Exception as e:
            st.sidebar.warning(f"Could not load saved credentials: {str(e)}")
    
    # Show OAuth authentication
    st.sidebar.subheader("Connect to Google")
    
    # Check if we have OAuth credentials
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        st.sidebar.error(
            "OAuth credentials not found!\n\n"
            "Add to your .env file:\n"
            "```\n"
            "GOOGLE_CLIENT_ID=your-client-id\n"
            "GOOGLE_CLIENT_SECRET=your-secret\n"
            "```"
        )
        return False
    
    # Determine redirect URI
    redirect_uri = "http://localhost:8501/"
    
    # For Streamlit Cloud
    if st.sidebar.checkbox("I'm using Streamlit Cloud", key="cloud_check"):
        redirect_uri = st.sidebar.text_input(
            "Your app URL:",
            placeholder="https://your-app.streamlit.app/",
            help="Must match EXACTLY what's in Google Cloud Console (including trailing slash)"
        )
        if not redirect_uri:
            st.sidebar.error("Please enter your app URL")
            return False
    
    # Check for OAuth callback in URL
    query_params = st.experimental_get_query_params()
    
    if 'code' in query_params:
        # We received an auth code!
        st.sidebar.info("Processing authentication...")
        
        try:
            code = query_params['code'][0]
            
            # Create flow
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": GOOGLE_CLIENT_ID,
                        "client_secret": GOOGLE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "redirect_uris": [redirect_uri]
                    }
                },
                scopes=GSC_SCOPES,
                redirect_uri=redirect_uri
            )
            
            # Exchange code for token
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Save credentials
            token_file.parent.mkdir(exist_ok=True)
            with open(token_file, 'wb') as f:
                pickle.dump(credentials, f)
            
            # Build service and test
            service = build('searchconsole', 'v1', credentials=credentials)
            service.sites().list().execute()  # Test the connection
            
            # Store in session
            st.session_state.gsc_service = service
            st.session_state.authenticated = True
            st.session_state.credentials = credentials
            
            # Clear query params
            st.experimental_set_query_params()
            
            st.sidebar.success("✅ Successfully authenticated!")
            st.rerun()
            
        except Exception as e:
            st.sidebar.error(f"Authentication failed: {str(e)}")
            # Clear the code param
            st.experimental_set_query_params()
    
    else:
        # Show connect button
        if st.sidebar.button("🔗 Connect to Google", type="primary", use_container_width=True):
            try:
                # Create OAuth flow
                flow = Flow.from_client_config(
                    {
                        "web": {
                            "client_id": GOOGLE_CLIENT_ID,
                            "client_secret": GOOGLE_CLIENT_SECRET,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
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
                
                # Show link and instructions
                st.sidebar.markdown("### Click to authorize:")
                st.sidebar.markdown(f"[🔗 Authorize with Google]({auth_url})")
                
                with st.sidebar.expander("Can't click the link?"):
                    st.text_area("Copy this URL:", auth_url, height=100)
                    st.info("Paste in your browser, authorize, then you'll be redirected back here")
                
            except Exception as e:
                st.sidebar.error(f"Error creating auth URL: {str(e)}")
    
    # Show setup instructions
    with st.sidebar.expander("⚙️ Setup Instructions"):
        st.markdown("""
        **In Google Cloud Console:**
        
        1. **OAuth Consent Screen** must be configured
        2. **OAuth 2.0 Client ID** must be "Web application" type
        3. **Authorized redirect URIs** must include:
           - `http://localhost:8501/` (for local)
           - Your Streamlit Cloud URL (if applicable)
        4. **Search Console API** must be enabled
        
        **Common Issues:**
        - "Access blocked" → OAuth consent screen not configured
        - "Invalid request" → Redirect URI mismatch
        - No properties → Wrong Google account
        """)
    
    return False
