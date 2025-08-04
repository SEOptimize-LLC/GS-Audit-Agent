"""
Enhanced authentication module for GSC Audit Tool
Supports both Service Account and OAuth authentication with Streamlit Cloud compatibility
"""

import streamlit as st
import pickle
import json
import os
from pathlib import Path
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from config import GSC_SCOPES, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

# Streamlit Cloud app URL - update this to match your deployment
REDIRECT_URI = os.getenv('STREAMLIT_URL', "https://gsc-audit-agent.streamlit.app/")


class GSCAuthenticator:
    def __init__(self):
        self.token_file = Path('.token/gsc_token.pickle')
        self.token_file.parent.mkdir(exist_ok=True)
    
    def authenticate_with_service_account(self, service_account_info=None, service_account_file=None):
        """
        Authenticate using Google Service Account
        
        Args:
            service_account_info: Dictionary with service account credentials (for Streamlit Cloud)
            service_account_file: Path to service account JSON file (for local development)
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            # Try Streamlit secrets first (for cloud deployment)
            if service_account_info is None and hasattr(st, 'secrets'):
                try:
                    service_account_info = dict(st.secrets["google_service_account"])
                    st.success("✅ Using service account from Streamlit secrets")
                except Exception:
                    pass
            
            # Try uploaded file
            if service_account_info is None and service_account_file is not None:
                if hasattr(service_account_file, 'read'):
                    # It's a file upload object
                    service_account_info = json.loads(service_account_file.read())
                else:
                    # It's a file path
                    with open(service_account_file, 'r') as f:
                        service_account_info = json.load(f)
            
            if service_account_info is None:
                st.error("❌ No service account credentials provided")
                return False
            
            # Create credentials from service account info
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=GSC_SCOPES
            )
            
            # Test the credentials by building the service
            service = build('searchconsole', 'v1', credentials=credentials)
            
            # Test API access by trying to list sites
            try:
                response = service.sites().list().execute()
                st.session_state.gsc_service = service
                st.session_state.authenticated = True
                st.session_state.auth_method = 'service_account'
                
                # Store credentials for future use
                st.session_state.service_account_credentials = credentials
                
                return True
                
            except Exception as api_error:
                st.error(f"❌ Service account has no access to Search Console properties: {str(api_error)}")
                st.error("Make sure to add the service account email to your Search Console property permissions")
                return False
                
        except Exception as e:
            st.error(f"❌ Service account authentication failed: {str(e)}")
            st.error("Please check your service account credentials and ensure the Search Console API is enabled")
            return False
    
    def authenticate_with_oauth(self):
        """
        Authenticate using OAuth 2.0 flow
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            # Check if we have valid stored credentials
            if self.token_file.exists():
                try:
                    with open(self.token_file, 'rb') as f:
                        creds = pickle.load(f)
                    
                    if creds and creds.valid:
                        service = build('searchconsole', 'v1', credentials=creds)
                        st.session_state.gsc_service = service
                        st.session_state.authenticated = True
                        st.session_state.auth_method = 'oauth'
                        return True
                    
                    elif creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                        with open(self.token_file, 'wb') as f:
                            pickle.dump(creds, f)
                        service = build('searchconsole', 'v1', credentials=creds)
                        st.session_state.gsc_service = service
                        st.session_state.authenticated = True
                        st.session_state.auth_method = 'oauth'
                        return True
                        
                except Exception as e:
                    st.warning(f"Stored credentials invalid: {str(e)}")
                    # Continue to OAuth flow
            
            # Check for OAuth credentials
            if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
                st.error("❌ OAuth credentials not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET")
                return False
            
            # Handle OAuth callback
            query_params = st.experimental_get_query_params()
            
            if 'code' in query_params:
                return self._handle_oauth_callback(query_params['code'][0])
            else:
                return self._start_oauth_flow()
                
        except Exception as e:
            st.error(f"❌ OAuth authentication failed: {str(e)}")
            return False
    
    def _start_oauth_flow(self):
        """Start the OAuth authorization flow"""
        try:
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
                redirect_uri=REDIRECT_URI
            )
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                prompt='consent',
                include_granted_scopes='true'
            )
            
            st.markdown(
                f'<meta http-equiv="refresh" content="0; url={auth_url}">',
                unsafe_allow_html=True
            )
            
            st.info("🔄 Redirecting to Google for authentication...")
            st.markdown(f"If you're not redirected automatically, [click here]({auth_url})")
            
            return False  # Will be True after redirect
            
        except Exception as e:
            st.error(f"❌ Failed to start OAuth flow: {str(e)}")
            return False
    
    def _handle_oauth_callback(self, auth_code):
        """Handle the OAuth callback and exchange code for token"""
        try:
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
                redirect_uri=REDIRECT_URI
            )
            
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
            
            # Save credentials
            with open(self.token_file, 'wb') as f:
                pickle.dump(creds, f)
            
            # Test the credentials
            service = build('searchconsole', 'v1', credentials=creds)
            response = service.sites().list().execute()
            
            st.session_state.gsc_service = service
            st.session_state.authenticated = True
            st.session_state.auth_method = 'oauth'
            
            # Clear query parameters
            st.experimental_set_query_params()
            st.rerun()
            
            return True
            
        except Exception as e:
            st.error(f"❌ Failed to exchange OAuth code: {str(e)}")
            st.experimental_set_query_params()
            return False
    
    def list_properties(self):
        """Get list of available Search Console properties"""
        if not st.session_state.get('gsc_service'):
            return []
        
        try:
            response = st.session_state.gsc_service.sites().list().execute()
            properties = []
            
            for prop in response.get('siteEntry', []):
                site_url = prop['siteUrl']
                permission_level = prop.get('permissionLevel', 'unknown')
                properties.append({
                    'url': site_url,
                    'permission': permission_level
                })
            
            return properties
            
        except Exception as e:
            st.error(f"❌ Failed to fetch properties: {str(e)}")
            return []
    
    def verify_property_access(self, property_url):
        """Verify access to a specific property"""
        properties = self.list_properties()
        return any(prop['url'] == property_url for prop in properties)
    
    def disconnect(self):
        """Disconnect and clear all authentication data"""
        # Clear session state
        for key in ['gsc_service', 'authenticated', 'auth_method', 'service_account_credentials']:
            if key in st.session_state:
                del st.session_state[key]
        
        # Remove stored token file
        if self.token_file.exists():
            try:
                self.token_file.unlink()
            except Exception:
                pass
        
        # Clear query parameters
        st.experimental_set_query_params()


def handle_authentication():
    """
    Main authentication handler for the Streamlit sidebar
    Returns:
        bool: True if authenticated, False otherwise
    """
    st.sidebar.header("🔐 Google Search Console Authentication")
    
    # Initialize authenticator
    if 'authenticator' not in st.session_state:
        st.session_state.authenticator = GSCAuthenticator()
    
    authenticator = st.session_state.authenticator
    
    # Check if already authenticated
    if st.session_state.get('authenticated'):
        auth_method = st.session_state.get('auth_method', 'unknown')
        st.sidebar.success(f"✅ Connected via {auth_method}")
        
        # Show current properties
        properties = authenticator.list_properties()
        if properties:
            st.sidebar.write(f"📊 Access to {len(properties)} properties")
        
        # Disconnect button
        if st.sidebar.button("🔌 Disconnect", type="secondary"):
            authenticator.disconnect()
            st.rerun()
        
        return True
    
    # Authentication options
    st.sidebar.markdown("---")
    auth_option = st.sidebar.radio(
        "Choose Authentication Method:",
        ["Service Account (Recommended)", "OAuth 2.0"],
        help="Service Account is more reliable for production deployment"
    )
    
    if auth_option == "Service Account (Recommended)":
        return handle_service_account_auth(authenticator)
    else:
        return handle_oauth_auth(authenticator)


def handle_service_account_auth(authenticator):
    """Handle service account authentication UI"""
    st.sidebar.subheader("🔑 Service Account Authentication")
    
    # Check for Streamlit secrets first
    has_secrets = False
    if hasattr(st, 'secrets'):
        try:
            _ = st.secrets["google_service_account"]
            has_secrets = True
            st.sidebar.success("✅ Service account found in secrets")
        except Exception:
            pass
    
    if has_secrets:
        if st.sidebar.button("🚀 Connect with Service Account", type="primary"):
            if authenticator.authenticate_with_service_account():
                st.rerun()
            return False
    else:
        st.sidebar.info("💡 Upload your service account JSON file")
        
        uploaded_file = st.sidebar.file_uploader(
            "Choose service account JSON file",
            type=['json'],
            help="Download from Google Cloud Console > APIs & Services > Credentials"
        )
        
        if uploaded_file is not None:
            if st.sidebar.button("🚀 Connect with Service Account", type="primary"):
                if authenticator.authenticate_with_service_account(service_account_file=uploaded_file):
                    st.rerun()
                return False
        
        # Instructions
        with st.sidebar.expander("📋 Setup Instructions"):
            st.markdown("""
            **Step 1:** Create Service Account
            1. Go to [Google Cloud Console](https://console.cloud.google.com/)
            2. Navigate to APIs & Services > Credentials
            3. Create Credentials > Service Account
            4. Download JSON key file
            
            **Step 2:** Enable API
            1. Go to APIs & Services > Library
            2. Search "Google Search Console API"
            3. Click Enable
            
            **Step 3:** Grant Access
            1. Go to [Search Console](https://search.google.com/search-console/)
            2. Select your property
            3. Settings > Users and permissions
            4. Add service account email with Full access
            """)
    
    return False


def handle_oauth_auth(authenticator):
    """Handle OAuth authentication UI"""
    st.sidebar.subheader("🔐 OAuth 2.0 Authentication")
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        st.sidebar.error("❌ OAuth credentials not configured")
        st.sidebar.info("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in environment variables")
        return False
    
    st.sidebar.info("🔄 OAuth requires user interaction")
    
    if st.sidebar.button("🚀 Connect with Google OAuth", type="primary"):
        return authenticator.authenticate_with_oauth()
    
    # Instructions
    with st.sidebar.expander("📋 OAuth Setup Instructions"):
        st.markdown(f"""
        **Step 1:** Configure OAuth in Google Cloud Console
        1. Go to APIs & Services > Credentials
        2. Create OAuth 2.0 Client ID
        3. Add redirect URI: `{REDIRECT_URI}`
        4. Download credentials
        
        **Step 2:** Set Environment Variables
        - GOOGLE_CLIENT_ID
        - GOOGLE_CLIENT_SECRET
        
        **Step 3:** Configure OAuth Consent Screen
        - Add authorized domain: `streamlit.app`
        - Add your app URL to authorized domains
        """)
    
    return False
