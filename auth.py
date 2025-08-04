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
                st.sidebar.success(SUCCESS_MESSAGES['auth_success'])
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