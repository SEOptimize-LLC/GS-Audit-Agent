"""
Authentication module for Google Search Console API
Fixed OAuth 2.0 implementation with proper error handling
"""

import streamlit as st
import json
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from config import GSC_SCOPES, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, ERROR_MESSAGES, SUCCESS_MESSAGES


class GSCAuthenticator:
    """Handles authentication for Google Search Console API"""
    
    def __init__(self):
        self.credentials = None
        self.service = None
        self.token_file = Path('.token/gsc_token.pickle')
        self.token_file.parent.mkdir(exist_ok=True)
        
    def authenticate_with_service_account(self, service_account_file):
        """Service Account auth - blocked for this organization"""
        st.error(
            "Service Account authentication is blocked by your organization policy. "
            "Please use OAuth 2.0 authentication instead."
        )
        return False
    
    def create_oauth_flow(self, redirect_uri=None):
        """Create OAuth flow with proper configuration"""
        if not redirect_uri:
            redirect_uri = "http://localhost:8501/"
        
        client_config = {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": [redirect_uri]
            }
        }
        
        flow = Flow.from_client_config(
            client_config,
            scopes=GSC_SCOPES,
            redirect_uri=redirect_uri
        )
        
        return flow
    
    def get_auth_url(self, flow):
        """Generate authorization URL"""
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        st.session_state.oauth_state = state
        return auth_url
    
    def handle_oauth_callback(self, code, state=None):
        """Handle OAuth callback with authorization code"""
        try:
            flow = self.create_oauth_flow()
            flow.fetch_token(code=code)
            
            self.credentials = flow.credentials
            
            with open(self.token_file, 'wb') as token:
                pickle.dump(self.credentials, token)
            
            self.service = build('searchconsole', 'v1', credentials=self.credentials)
            
            st.session_state.credentials = self.credentials
            st.session_state.gsc_service = self.service
            st.session_state.authenticated = True
            st.session_state.auth_method = 'oauth'
            
            return True
            
        except Exception as e:
            st.error(f"Error during OAuth callback: {str(e)}")
            return False
    
    def authenticate_with_oauth(self):
        """Authenticate using OAuth 2.0 flow"""
        try:
            if self.token_file.exists():
                try:
                    with open(self.token_file, 'rb') as token:
                        self.credentials = pickle.load(token)
                except Exception as e:
                    st.warning(f"Could not load saved credentials: {str(e)}")
                    self.credentials = None
            
            if self.credentials and self.credentials.valid:
                self.service = build('searchconsole', 'v1', credentials=self.credentials)
                st.session_state.credentials = self.credentials
                st.session_state.gsc_service = self.service
                st.session_state.authenticated = True
                st.session_state.auth_method = 'oauth'
                return True
            
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                try:
                    self.credentials.refresh(Request())
                    self.service = build('searchconsole', 'v1', credentials=self.credentials)
                    
                    with open(self.token_file, 'wb') as token:
                        pickle.dump(self.credentials, token)
                    
                    st.session_state.credentials = self.credentials
                    st.session_state.gsc_service = self.service
                    st.session_state.authenticated = True
                    st.session_state.auth_method = 'oauth'
                    return True
                except Exception as e:
                    st.warning(f"Could not refresh credentials: {str(e)}")
                    self.credentials = None
            
            return False
            
        except Exception as e:
            st.error(f"OAuth authentication error: {str(e)}")
            return False
    
    def authenticate_with_pickle_file(self, pickle_file):
        """Authenticate using uploaded pickle file (Colab workaround)"""
        try:
            credentials = pickle.loads(pickle_file.read())
            
            if credentials and credentials.valid:
                service = build('searchconsole', 'v1', credentials=credentials)
                service.sites().list().execute()
                
                st.session_state.credentials = credentials
                st.session_state.gsc_service = service
                st.session_state.authenticated = True
                st.session_state.auth_method = 'pickle_file'
                
                self.token_file.parent.mkdir(exist_ok=True)
                pickle_file.seek(0)
                with open(self.token_file, 'wb') as f:
                    f.write(pickle_file.read())
                
                return True
            else:
                st.error("Invalid or expired credentials in pickle file")
                return False
                
        except Exception as e:
            st.error(f"Error loading credentials: {str(e)}")
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


def get_query_params():
    """Get query parameters in a version-safe way"""
    try:
        # Try new API (Streamlit >= 1.28)
        return dict(st.query_params)
    except AttributeError:
        try:
            # Try experimental API (older versions)
            params = st.experimental_get_query_params()
            return {k: v[0] if isinstance(v, list) and v else v for k, v in params.items()}
        except:
            return {}


def clear_query_params():
    """Clear query parameters in a version-safe way"""
    try:
        # Try new API
        st.query_params.clear()
    except AttributeError:
        try:
            # Try experimental API
            st.experimental_set_query_params()
        except:
            pass


def handle_authentication():
    """Streamlit UI component for handling authentication"""
    st.sidebar.header("🔐 Authentication")
    
    if st.session_state.get('authenticated'):
        st.sidebar.success("✅ Authenticated")
        st.sidebar.caption("Connected to Google Search Console")
        
        if st.sidebar.button("Logout"):
            for key in ['credentials', 'gsc_service', 'authenticated', 'auth_method', 'oauth_state']:
                if key in st.session_state:
                    del st.session_state[key]
            
            token_file = Path('.token/gsc_token.pickle')
            if token_file.exists():
                token_file.unlink()
            
            st.rerun()
            
        return True
    
    authenticator = GSCAuthenticator()
    
    if authenticator.authenticate_with_oauth():
        st.sidebar.success(SUCCESS_MESSAGES['auth_success'])
        st.rerun()
        return True
    
    # OAuth setup instructions
    st.sidebar.info(
        "### Setup Required\n"
        "1. Configure OAuth in Google Cloud Console\n"
        "2. Enable Search Console API\n"
        "3. Add redirect URIs\n"
        "4. Click 'Start OAuth Flow'"
    )
    
    # Check for OAuth callback
    query_params = get_query_params()
    if 'code' in query_params:
        st.sidebar.info("Processing authentication...")
        code = query_params.get('code')
        state = query_params.get('state')
        
        if authenticator.handle_oauth_callback(code, state):
            clear_query_params()
            st.sidebar.success(SUCCESS_MESSAGES['auth_success'])
            st.rerun()
        else:
            st.sidebar.error(ERROR_MESSAGES['auth_failed'])
    
    # OAuth flow section
    st.sidebar.subheader("OAuth 2.0 Authentication")
    
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        if st.button("🚀 Start OAuth Flow", type="primary", use_container_width=True):
            redirect_uri = "http://localhost:8501/"
            
            if os.getenv('STREAMLIT_SHARING_MODE') or st.sidebar.checkbox("Using Streamlit Cloud?"):
                redirect_uri = st.sidebar.text_input(
                    "Enter your app's URL:",
                    placeholder="https://your-app.streamlit.app/",
                    help="Include the trailing slash"
                )
                if not redirect_uri:
                    st.sidebar.error("Please enter your app's URL")
                    return False
            
            try:
                flow = authenticator.create_oauth_flow(redirect_uri)
                auth_url = authenticator.get_auth_url(flow)
                
                st.sidebar.markdown("### Click to authorize:")
                st.sidebar.markdown(f"[🔗 Authorize with Google]({auth_url})")
                
                with st.sidebar.expander("Can't click the link?"):
                    st.text_area("Copy this URL:", auth_url, height=100)
                
            except Exception as e:
                st.sidebar.error(f"Error creating auth URL: {str(e)}")
    
    # Alternative: Upload credentials
    with st.sidebar.expander("🔑 Alternative: Upload Credentials"):
        st.info(
            "If OAuth is blocked, generate credentials "
            "in Google Colab and upload the pickle file."
        )
        
        pickle_file = st.file_uploader(
            "Upload credentials.pickle",
            type=['pickle', 'pkl']
        )
        
        if pickle_file:
            if authenticator.authenticate_with_pickle_file(pickle_file):
                st.success("Authenticated successfully!")
                st.rerun()
    
    # Troubleshooting
    with st.sidebar.expander("🔧 Troubleshooting"):
        st.markdown(
            """
            **OAuth Issues:**
            - Ensure redirect URI matches exactly
            - Check OAuth consent screen setup
            - Verify API is enabled
            - Try incognito mode
            
            **Missing credentials:**
            - Check .env file
            - Verify client ID/secret
            """
        )
    
    return False
