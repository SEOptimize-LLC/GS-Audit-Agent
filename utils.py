"""
Utility functions for GSC Audit Tool
Helper functions for data processing and formatting
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Union, Optional, Tuple
from datetime import datetime, timedelta
import re
import json


def format_number(num: Union[int, float], decimals: int = 0) -> str:
    """
    Format number with thousands separator
    
    Args:
        num: Number to format
        decimals: Decimal places to show
        
    Returns:
        Formatted string
    """
    if pd.isna(num):
        return "N/A"
    
    if decimals > 0:
        return f"{num:,.{decimals}f}"
    else:
        return f"{int(num):,}"


def format_percentage(num: float, decimals: int = 1) -> str:
    """
    Format number as percentage
    
    Args:
        num: Number to format (0.15 = 15%)
        decimals: Decimal places
        
    Returns:
        Formatted percentage string
    """
    if pd.isna(num):
        return "N/A"
    
    return f"{num * 100:.{decimals}f}%"


def format_change(old_value: float, new_value: float, as_percentage: bool = True) -> str:
    """
    Format change between two values
    
    Args:
        old_value: Previous value
        new_value: Current value
        as_percentage: Show as percentage
        
    Returns:
        Formatted change string with emoji
    """
    if pd.isna(old_value) or pd.isna(new_value) or old_value == 0:
        return "N/A"
    
    change = ((new_value - old_value) / old_value) * 100
    
    if change > 5:
        emoji = "📈"
    elif change < -5:
        emoji = "📉"
    else:
        emoji = "➡️"
    
    if as_percentage:
        return f"{emoji} {change:+.1f}%"
    else:
        diff = new_value - old_value
        return f"{emoji} {diff:+,.0f}"


def clean_url(url: str, max_length: int = 50) -> str:
    """
    Clean and truncate URL for display
    
    Args:
        url: Full URL
        max_length: Maximum length
        
    Returns:
        Cleaned URL string
    """
    # Remove protocol
    url = re.sub(r'^https?://', '', url)
    
    # Remove www
    url = re.sub(r'^www\.', '', url)
    
    # Remove trailing slash
    url = url.rstrip('/')
    
    # Truncate if needed
    if len(url) > max_length:
        return url[:max_length-3] + "..."
    
    return url


def get_domain_from_url(url: str) -> str:
    """
    Extract domain from URL
    
    Args:
        url: Full URL
        
    Returns:
        Domain name
    """
    import urllib.parse
    
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc or parsed.path
        return domain.replace('www.', '')
    except:
        return url


def categorize_query(query: str) -> str:
    """
    Categorize search query by intent
    
    Args:
        query: Search query
        
    Returns:
        Category name
    """
    query_lower = query.lower()
    
    # Navigational (brand)
    brand_terms = ['your brand', 'company name']  # Add actual brand terms
    if any(term in query_lower for term in brand_terms):
        return "Navigational"
    
    # Transactional
    trans_terms = ['buy', 'price', 'cost', 'cheap', 'deal', 'discount', 'order']
    if any(term in query_lower for term in trans_terms):
        return "Transactional"
    
    # Informational
    info_terms = ['how', 'what', 'why', 'when', 'where', 'who', 'guide', 'tutorial']
    if any(term in query_lower for term in info_terms):
        return "Informational"
    
    # Commercial
    comm_terms = ['best', 'top', 'review', 'comparison', 'vs', 'versus']
    if any(term in query_lower for term in comm_terms):
        return "Commercial"
    
    return "Other"


def estimate_traffic_value(clicks: int, avg_cpc: float = 2.50) -> float:
    """
    Estimate monetary value of organic traffic
    
    Args:
        clicks: Number of clicks
        avg_cpc: Average cost per click
        
    Returns:
        Estimated value
    """
    return clicks * avg_cpc


def get_date_ranges() -> Dict[str, tuple]:
    """
    Get common date ranges for analysis
    
    Returns:
        Dictionary of date range tuples
    """
    today = datetime.now().date()
    
    ranges = {
        'last_7_days': (
            today - timedelta(days=7),
            today - timedelta(days=1)
        ),
        'last_30_days': (
            today - timedelta(days=30),
            today - timedelta(days=1)
        ),
        'last_90_days': (
            today - timedelta(days=90),
            today - timedelta(days=1)
        ),
        'last_6_months': (
            today - timedelta(days=180),
            today - timedelta(days=1)
        ),
        'last_12_months': (
            today - timedelta(days=365),
            today - timedelta(days=1)
        ),
        'previous_30_days': (
            today - timedelta(days=60),
            today - timedelta(days=31)
        ),
        'previous_90_days': (
            today - timedelta(days=180),
            today - timedelta(days=91)
        )
    }
    
    return ranges


def calculate_period_change(df: pd.DataFrame, date_col: str, metric_col: str, 
                          period_days: int = 30) -> Dict[str, float]:
    """
    Calculate change between two periods
    
    Args:
        df: DataFrame with date and metric columns
        date_col: Name of date column
        metric_col: Name of metric column
        period_days: Days in each period
        
    Returns:
        Dictionary with current, previous, and change values
    """
    df[date_col] = pd.to_datetime(df[date_col])
    
    latest_date = df[date_col].max()
    period_start = latest_date - timedelta(days=period_days)
    prev_period_start = period_start - timedelta(days=period_days)
    
    current = df[df[date_col] > period_start][metric_col].sum()
    previous = df[(df[date_col] > prev_period_start) & 
                  (df[date_col] <= period_start)][metric_col].sum()
    
    if previous > 0:
        change_pct = ((current - previous) / previous) * 100
    else:
        change_pct = 0
    
    return {
        'current': current,
        'previous': previous,
        'change': current - previous,
        'change_pct': change_pct
    }


def identify_seasonality(df: pd.DataFrame, date_col: str, metric_col: str) -> Dict[str, any]:
    """
    Identify seasonal patterns in data
    
    Args:
        df: DataFrame with time series data
        date_col: Date column name
        metric_col: Metric column name
        
    Returns:
        Dictionary with seasonality insights
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    
    # Add time components
    df['month'] = df[date_col].dt.month
    df['day_of_week'] = df[date_col].dt.dayofweek
    df['week_of_year'] = df[date_col].dt.isocalendar().week
    
    # Monthly patterns
    monthly_avg = df.groupby('month')[metric_col].mean()
    monthly_std = df.groupby('month')[metric_col].std()
    
    # Day of week patterns
    dow_avg = df.groupby('day_of_week')[metric_col].mean()
    
    # Identify peaks and valleys
    peak_month = monthly_avg.idxmax()
    valley_month = monthly_avg.idxmin()
    peak_dow = dow_avg.idxmax()
    valley_dow = dow_avg.idxmin()
    
    dow_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    return {
        'peak_month': month_names[peak_month - 1],
        'valley_month': month_names[valley_month - 1],
        'peak_day': dow_names[peak_dow],
        'valley_day': dow_names[valley_dow],
        'monthly_variation': monthly_std.mean() / monthly_avg.mean() if monthly_avg.mean() > 0 else 0,
        'weekly_variation': dow_avg.std() / dow_avg.mean() if dow_avg.mean() > 0 else 0,
        'has_strong_seasonality': (monthly_std.mean() / monthly_avg.mean() > 0.2) if monthly_avg.mean() > 0 else False
    }


def export_audit_summary(analysis_results: Dict, insights: Dict, filename: str = None) -> str:
    """
    Export audit summary as JSON
    
    Args:
        analysis_results: Analysis results dictionary
        insights: AI insights dictionary
        filename: Optional filename
        
    Returns:
        Filename of exported file
    """
    if not filename:
        filename = f"gsc_audit_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    summary = {
        'audit_date': datetime.now().isoformat(),
        'key_metrics': {
            'cannibalization_issues': len(analysis_results.get('cannibalization', [])),
            'striking_distance_keywords': len(analysis_results.get('opportunities', {}).get('striking_distance', [])),
            'quality_score': analysis_results.get('content_quality', {}).get('summary', {}).get('quality_score', 0),
            'technical_issues': len(analysis_results.get('technical', {}).get('indexing_issues', [])),
            'cwv_status': analysis_results.get('cwv', {}).get('overall_status', 'unknown')
        },
        'top_opportunities': analysis_results.get('opportunities', {}).get('striking_distance', [])[:5],
        'critical_issues': {
            'cannibalization': [c['query'] for c in analysis_results.get('cannibalization', [])[:5]],
            'technical': analysis_results.get('technical', {}).get('indexing_issues', [])[:5]
        },
        'ai_summary': insights.get('executive_summary', 'No AI summary available')
    }
    
    with open(filename, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    return filename


def validate_gsc_property_url(url: str) -> bool:
    """
    Validate GSC property URL format
    
    Args:
        url: Property URL
        
    Returns:
        True if valid
    """
    # Domain property
    if url.startswith('sc-domain:'):
        return True
    
    # URL prefix property
    if url.startswith(('http://', 'https://')):
        return True
    
    return False


def parse_gsc_property_url(url: str) -> Dict[str, str]:
    """
    Parse GSC property URL into components
    
    Args:
        url: Property URL
        
    Returns:
        Dictionary with property type and domain
    """
    if url.startswith('sc-domain:'):
        return {
            'type': 'domain',
            'domain': url.replace('sc-domain:', ''),
            'protocol': 'all',
            'subdomain': 'all'
        }
    elif url.startswith('https://'):
        domain = get_domain_from_url(url)
        return {
            'type': 'url-prefix',
            'domain': domain,
            'protocol': 'https',
            'subdomain': 'www' if 'www.' in url else 'none'
        }
    elif url.startswith('http://'):
        domain = get_domain_from_url(url)
        return {
            'type': 'url-prefix',
            'domain': domain,
            'protocol': 'http',
            'subdomain': 'www' if 'www.' in url else 'none'
        }
    
    return {'type': 'unknown', 'domain': url}