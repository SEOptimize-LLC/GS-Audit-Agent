"""
Configuration file for GSC Audit Tool
Contains all constants, settings, and configuration parameters
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys and Authentication
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
GOOGLE_AI_API_KEY = os.getenv('GOOGLE_AI_API_KEY')

# Google API Settings
GSC_SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
PAGESPEED_API_KEY = os.getenv('PAGESPEED_API_KEY')  # Optional, works without key but with limits

# API Rate Limits
GSC_API_QUOTA = {
    'requests_per_minute': 1200,
    'requests_per_day': 50000,
    'url_inspection_per_minute': 600,
    'url_inspection_per_day': 2000
}

# Data Collection Settings
DEFAULT_DATE_RANGE = 90  # days
MAX_DATE_RANGE = 16 * 30  # 16 months in days
DATA_FRESHNESS_DELAY = 3  # GSC data is typically 3 days behind

# Pagination Settings
ROWS_PER_REQUEST = 25000  # Maximum allowed by GSC API
DEFAULT_ROW_LIMIT = 10000  # Default for initial requests

# Analysis Thresholds
CANNIBALIZATION_THRESHOLD = {
    'min_impressions': 100,
    'min_pages': 2,
    'position_variance': 5
}

STRIKING_DISTANCE = {
    'min_position': 11,
    'max_position': 20,
    'min_impressions': 50
}

LOW_CTR_THRESHOLD = {
    'min_impressions': 500,
    'max_ctr': 0.02  # 2%
}

CONTENT_QUALITY_SIGNALS = {
    'thin_content_words': 300,
    'outdated_months': 24,
    'low_traffic_threshold': 10
}

# Performance Thresholds
PERFORMANCE_DECLINE_THRESHOLD = -20  # 20% decline
MOBILE_DESKTOP_GAP_THRESHOLD = 5  # positions

# Core Web Vitals Thresholds
CWV_THRESHOLDS = {
    'LCP': {'good': 2500, 'needs_improvement': 4000},  # milliseconds
    'INP': {'good': 200, 'needs_improvement': 500},    # milliseconds  
    'CLS': {'good': 0.1, 'needs_improvement': 0.25}    # score
}

# Report Settings
REPORT_SECTIONS = [
    'executive_summary',
    'foundation_security',
    'indexing_analysis',
    'performance_analysis',
    'technical_health',
    'opportunities',
    'action_plan'
]

# Visualization Settings
CHART_COLORS = {
    'primary': '#1f77b4',
    'secondary': '#ff7f0e',
    'success': '#2ca02c',
    'warning': '#ff9800',
    'danger': '#d62728',
    'info': '#17a2b8'
}

# Cache Settings
CACHE_EXPIRY = {
    'search_analytics': 24,  # hours
    'url_inspection': 72,    # hours
    'sitemaps': 168,         # hours (1 week)
    'crawl_stats': 24        # hours
}

# AI Model Settings
AI_MODELS = {
    'openai': {
        'models': ['gpt-4-turbo-preview', 'gpt-4', 'gpt-3.5-turbo'],
        'default': 'gpt-4-turbo-preview',
        'max_tokens': 4000,
        'temperature': 0.7
    },
    'anthropic': {
        'models': ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307'],
        'default': 'claude-3-sonnet-20240229',
        'max_tokens': 4000,
        'temperature': 0.7
    },
    'google': {
        'models': ['gemini-pro', 'gemini-pro-vision'],
        'default': 'gemini-pro',
        'max_tokens': 4000,
        'temperature': 0.7
    }
}

# Insight Generation Prompts
INSIGHT_PROMPTS = {
    'cannibalization': """
    Analyze this keyword cannibalization data and provide specific, actionable recommendations:
    {data}
    
    Include:
    1. The severity of the issue
    2. Which page should be the primary target
    3. Specific consolidation steps
    4. Expected impact in terms of ranking improvement and traffic
    5. Priority level and timeline
    """,
    
    'content_quality': """
    Analyze these content quality signals from Google Search Console:
    {data}
    
    Provide:
    1. Root cause analysis of why Google isn't indexing these pages
    2. Specific patterns identified
    3. Prioritized recommendations for improvement
    4. Whether to improve or remove content
    5. Expected impact on overall site quality
    """,
    
    'opportunities': """
    Analyze these ranking opportunities:
    {data}
    
    Provide:
    1. Quick wins vs long-term opportunities
    2. Specific optimization tactics for each opportunity type
    3. Resource requirements
    4. Expected ROI and timeline
    5. Priority order for implementation
    """
}

# Error Messages
ERROR_MESSAGES = {
    'auth_failed': "Authentication failed. Please check your credentials.",
    'api_quota': "API quota exceeded. Please try again later.",
    'no_data': "No data available for the selected date range.",
    'invalid_url': "Please enter a valid website URL.",
    'no_access': "You don't have access to this Search Console property."
}

# Success Messages
SUCCESS_MESSAGES = {
    'auth_success': "Successfully authenticated with Google Search Console!",
    'data_loaded': "Data successfully loaded from Search Console.",
    'analysis_complete': "Analysis completed successfully!",
    'report_generated': "Report generated successfully!"
}