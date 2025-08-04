"""
Authentication module for Google Search Console API
Handles both OAuth 2.0 and Service Account authentication
"""

import streamlit as st
import json
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
from pathlib import Path

from config import GSC_SCOPES, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, ERROR_MESSAGES, SUCCESS_MESSAGES


class GSCAuthenticator:
    """Handles authentication for Google Search Console API"""
    
    def __init__(self):
        self.credentials = None
        self.service = None
        self.token_file = Path('.token/gsc_token.pickle')
        self.token_file.parent.mkdir(exist_ok=True)
        
    def authenticate_with_service_account(self, service_account_file):
        """
        Authenticate using a service account JSON file
        
        Args:
            service_account_file: Uploaded service account JSON file
            
        Returns:
            bool: Success status
        """
        try:
            # Parse the service account file
            service_account_info = json.loads(service_account_file.read())
            
            # Create credentials
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=GSC_SCOPES
            )
            
            # Build the service
            self.service = build('searchconsole', 'v1', credentials=self.credentials)
            
            # Test the connection by listing sites
            self.service.sites().list().execute()
            
            # Store in session state
            st.session_state.credentials = self.credentials
            st.session_state.gsc_service = self.service
            st.session_state.authenticated = True
            st.session_state.auth_method = 'service_account'
            
            return True
            
        except Exception as e:
            st.error(f"Authentication failed: {str(e)}")
            return False
    
    def authenticate_with_oauth(self):
        """
        Authenticate using OAuth 2.0 flow
        
        Returns:
            bool: Success status
        """
        try:
            # Check if we have stored credentials
            if self.token_file.exists():
                with open(self.token_file, 'rb') as token:
                    self.credentials = pickle.load(token)
            
            # If there are no (valid) credentials available, let the user log in
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    # Create the flow
                    flow = Flow.from_client_config(
                        {
                            "web": {
                                "client_id": GOOGLE_CLIENT_ID,
                                "client_secret": GOOGLE_CLIENT_SECRET,
                                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                                "token_uri": "https://oauth2.googleapis.com/token",
                                "redirect_uris": ["http://localhost:8501"]
                            }
                        },
                        scopes=GSC_SCOPES,
                        redirect_uri="http://localhost:8501"
                    )
                    
                    # Generate authorization URL
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    
                    # Display the authorization URL
                    st.write("Please visit this URL to authorize the application:")
                    st.code(auth_url)
                    
                    # Get the authorization code from user
                    auth_code = st.text_input("Enter the authorization code:")
                    
                    if auth_code:
                        # Exchange code for token
                        flow.fetch_token(code=auth_code)
                        self.credentials = flow.credentials
                        
                        # Save the credentials for the next run
                        with open(self.token_file, 'wb') as token:
                            pickle.dump(self.credentials, token)
            
            if self.credentials and self.credentials.valid:
                # Build the service
                self.service = build('searchconsole', 'v1', credentials=self.credentials)
                
                # Store in session state
                st.session_state.credentials = self.credentials
                st.session_state.gsc_service = self.service
                st.session_state.authenticated = True
                st.session_state.auth_method = 'oauth'
                
                return True
                
        except Exception as e:
            st.error(f"OAuth authentication failed: {str(e)}")
            return False
    
    def list_properties(self):
        """
        List all Search Console properties the user has access to
        
        Returns:
            list: List of property URLs
        """
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
        """
        Verify that the user has access to a specific property
        
        Args:
            property_url: URL of the property to verify
            
        Returns:
            bool: True if user has access
        """
        properties = self.list_properties()
        return property_url in properties
    
    def get_pagespeed_insights_service(self):
        """
        Get PageSpeed Insights API service (no auth required)
        
        Returns:
            service object for PageSpeed Insights
        """
        from config import PAGESPEED_API_KEY
        
        if PAGESPEED_API_KEY:
            return build('pagespeedonline', 'v5', developerKey=PAGESPEED_API_KEY)
        else:
            # Works without API key but with stricter rate limits
            return build('pagespeedonline', 'v5')


def handle_authentication():
    """
    Streamlit UI component for handling authentication
    
    Returns:
        bool: True if authenticated
    """
    st.sidebar.header("🔐 Authentication")
    
    if st.session_state.get('authenticated'):
        st.sidebar.success("✅ Authenticated")
        
        # Show logout button
        if st.sidebar.button("Logout"):
            # Clear session state
            for key in ['credentials', 'gsc_service', 'authenticated', 'auth_method']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
            
        return True
    
    # Authentication options
    auth_method = st.sidebar.radio(
        "Choose authentication method:",
        ["Service Account (Recommended)", "OAuth 2.0"]
    )
    
    authenticator = GSCAuthenticator()
    
    if auth_method == "Service Account (Recommended)":
        st.sidebar.info(
            "Service Account authentication is recommended for easier setup. "
            "Upload your service account JSON file below."
        )
        
        service_account_file = st.sidebar.file_uploader(
            "Upload Service Account Key",
            type=['json'],
            help="Download from Google Cloud Console > IAM & Admin > Service Accounts"
        )
        
        if service_account_file:
            if authenticator.authenticate_with_service_account(service_account_file):
                st.sidebar.success(SUCCESS_MESSAGES['auth_success'])"""
Authentication module for Google Search Console API
Fixed OAuth 2.0 implementation with proper flow handling
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
        """
        Authenticate using a service account JSON file
        (Kept for compatibility but will show error for your org)
        """
        st.error(
            "Service Account authentication is blocked by your organization policy. "
            "Please use OAuth 2.0 authentication instead."
        )
        return False
    
    def create_oauth_flow(self, redirect_uri: str = None) -> Flow:
        """
        Create OAuth flow with proper configuration
        
        Args:
            redirect_uri: OAuth redirect URI
            
        Returns:
            Configured Flow object
        """
        if not redirect_uri:
            # For local development
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
    
    def get_auth_url(self, flow: Flow) -> str:
        """
        Generate authorization URL with proper parameters
        
        Args:
            flow: OAuth flow object
            
        Returns:
            Authorization URL
        """
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Store state in session
        st.session_state.oauth_state = state
        
        return auth_url
    
    def handle_oauth_callback(self, code: str, state: str = None) -> bool:
        """
        Handle OAuth callback with authorization code
        
        Args:
            code: Authorization code from Google
            state: State parameter for security
            
        Returns:
            Success status
        """
        try:
            # Recreate flow with same parameters
            flow = self.create_oauth_flow()
            
            # Exchange code for token
            flow.fetch_token(code=code)
            
            self.credentials = flow.credentials
            
            # Save credentials
            with open(self.token_file, 'wb') as token:
                pickle.dump(self.credentials, token)
            
            # Build service
            self.service = build('searchconsole', 'v1', credentials=self.credentials)
            
            # Store in session
            st.session_state.credentials = self.credentials
            st.session_state.gsc_service = self.service
            st.session_state.authenticated = True
            st.session_state.auth_method = 'oauth'
            
            return True
            
        except Exception as e:
            st.error(f"Error during OAuth callback: {str(e)}")
            return False
    
    def authenticate_with_oauth(self) -> bool:
        """
        Authenticate using OAuth 2.0 flow
        
        Returns:
            Success status
        """
        try:
            # Check if we have stored credentials
            if self.token_file.exists():
                try:
                    with open(self.token_file, 'rb') as token:
                        self.credentials = pickle.load(token)
                except Exception as e:
                    st.warning(f"Could not load saved credentials: {str(e)}")
                    self.credentials = None
            
            # If credentials exist and are valid
            if self.credentials and self.credentials.valid:
                self.service = build('searchconsole', 'v1', credentials=self.credentials)
                st.session_state.credentials = self.credentials
                st.session_state.gsc_service = self.service
                st.session_state.authenticated = True
                st.session_state.auth_method = 'oauth'
                return True
            
            # If credentials exist but are expired, try to refresh
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                try:
                    self.credentials.refresh(Request())
                    self.service = build('searchconsole', 'v1', credentials=self.credentials)
                    
                    # Save refreshed credentials
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
            
            # No valid credentials - need to authenticate
            return False
            
        except Exception as e:
            st.error(f"OAuth authentication error: {str(e)}")
            return False
    
    def list_properties(self):
        """
        List all Search Console properties the user has access to
        
        Returns:
            list: List of property URLs
        """
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
        """
        Verify that the user has access to a specific property
        
        Args:
            property_url: URL of the property to verify
            
        Returns:
            bool: True if user has access
        """
        properties = self.list_properties()
        return property_url in properties


def handle_authentication():
    """
    Streamlit UI component for handling authentication
    
    Returns:
        bool: True if authenticated
    """
    st.sidebar.header("🔐 Authentication")
    
    # Check if already authenticated
    if st.session_state.get('authenticated'):
        st.sidebar.success("✅ Authenticated")
        
        # Show current user info if available
        if st.session_state.get('credentials'):
            st.sidebar.caption("Connected to Google Search Console")
        
        # Show logout button
        if st.sidebar.button("Logout"):
            # Clear session state
            for key in ['credentials', 'gsc_service', 'authenticated', 'auth_method', 'oauth_state']:
                if key in st.session_state:
                    del st.session_state[key]
            
            # Remove saved token
            token_file = Path('.token/gsc_token.pickle')
            if token_file.exists():
                token_file.unlink()
            
            st.rerun()
            
        return True
    
    # Initialize authenticator
    authenticator = GSCAuthenticator()
    
    # Try to authenticate with existing credentials
    if authenticator.authenticate_with_oauth():
        st.sidebar.success(SUCCESS_MESSAGES['auth_success'])
        st.rerun()
        return True
    
    # Show OAuth setup instructions
    st.sidebar.info(
        "### OAuth Setup Instructions\n"
        "1. Make sure your OAuth consent screen is configured\n"
        "2. Add your redirect URI to authorized redirects\n"
        "3. Enable the Search Console API\n"
        "4. Click 'Start OAuth Flow' below"
    )
    
    # OAuth flow section
    st.sidebar.subheader("OAuth 2.0 Authentication")
    
    # Check if we're handling a callback
    query_params = st.query_params
    if 'code' in query_params:
        st.sidebar.info("Processing authentication...")
        code = query_params['code']
        state = query_params.get('state', [''])[0] if 'state' in query_params else None
        
        if authenticator.handle_oauth_callback(code, state):
            # Clear query params
            st.query_params.clear()
            st.sidebar.success(SUCCESS_MESSAGES['auth_success'])
            st.rerun()
        else:
            st.sidebar.error(ERROR_MESSAGES['auth_failed'])
    
    # Show OAuth flow button
    else:
        if st.sidebar.button("🚀 Start OAuth Flow", type="primary"):
            # Determine redirect URI
            if os.getenv('STREAMLIT_SHARING_MODE'):
                # For Streamlit Cloud deployment
                redirect_uri = st.sidebar.text_input(
                    "Enter your app's full URL:",
                    placeholder="https://your-app.streamlit.app/",
                    help="Enter the complete URL of your Streamlit app"
                )
                if not redirect_uri:
                    st.sidebar.error("Please enter your app's URL")
                    return False
            else:
                # For local development
                redirect_uri = "http://localhost:8501/"
            
            # Create flow and get auth URL
            flow = authenticator.create_oauth_flow(redirect_uri)
            auth_url = authenticator.get_auth_url(flow)
            
            # Display auth URL
            st.sidebar.markdown("### Step 1: Authorize the app")
            st.sidebar.markdown(
                f"Click [here]({auth_url}) to authorize the app with Google"
            )
            
            # Also show the URL for copying
            st.sidebar.text_area(
                "Or copy this URL:",
                auth_url,
                height=100,
                help="Copy and paste this URL in your browser if the link doesn't work"
            )
            
            st.sidebar.markdown("### Step 2: Return here")
            st.sidebar.info(
                "After authorizing, you'll be redirected back to this app automatically."
            )
    
    # Troubleshooting section
    with st.sidebar.expander("🔧 Troubleshooting"):
        st.markdown(
            """
            **Common Issues:**
            
            1. **"Access blocked" error:**
               - Ensure OAuth consent screen is configured
               - Add test users if in testing mode
               - Verify redirect URI matches exactly
            
            2. **"Invalid request" error:**
               - Check that Search Console API is enabled
               - Verify client ID and secret are correct
               - Ensure redirect URI is authorized
            
            3. **No properties showing:**
               - Verify the account has GSC access
               - Check you're using the right Google account
               - Ensure properties are verified in GSC
            """
        )
    
    return False
                st.rerun()
            else:
                st.sidebar.error(ERROR_MESSAGES['auth_failed'])
                
    else:  # OAuth 2.0
        st.sidebar.info(
            "OAuth authentication requires setting up OAuth credentials in Google Cloud Console. "
            "This method is more complex but doesn't require a service account."
        )
        
        if st.sidebar.button("Start OAuth Flow"):
            if authenticator.authenticate_with_oauth():
                st.sidebar.success(SUCCESS_MESSAGES['auth_success'])
                st.rerun()
            else:
                st.sidebar.error(ERROR_MESSAGES['auth_failed'])
    

    return False
