"""
Data Collection Module for GSC Audit Tool
Handles all API calls to Google Search Console and PageSpeed Insights
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional, Tuple
import json
from googleapiclient.errors import HttpError
import requests

from config import (
    ROWS_PER_REQUEST, DEFAULT_ROW_LIMIT, GSC_API_QUOTA,
    DATA_FRESHNESS_DELAY, PAGESPEED_API_KEY
)


class GSCDataCollector:
    """Handles all data collection from Google Search Console API"""
    
    def __init__(self, service, property_url: str):
        self.service = service
        self.property_url = property_url
        self.rate_limit_delay = 60 / GSC_API_QUOTA['requests_per_minute']  # Delay between requests
        
    def get_date_range(self, days: int = 90) -> Tuple[str, str]:
        """
        Calculate date range for data collection
        
        Args:
            days: Number of days to look back
            
        Returns:
            Tuple of (start_date, end_date) as strings
        """
        end_date = datetime.now() - timedelta(days=DATA_FRESHNESS_DELAY)
        start_date = end_date - timedelta(days=days)
        
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    def execute_with_retry(self, request, max_retries: int = 3):
        """
        Execute API request with retry logic
        
        Args:
            request: API request object
            max_retries: Maximum number of retries
            
        Returns:
            API response
        """
        for attempt in range(max_retries):
            try:
                time.sleep(self.rate_limit_delay)  # Rate limiting
                return request.execute()
            except HttpError as e:
                if e.resp.status == 429:  # Rate limit exceeded
                    wait_time = (attempt + 1) * 10
                    st.warning(f"Rate limit hit. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                elif e.resp.status >= 500:  # Server error
                    wait_time = (attempt + 1) * 5
                    time.sleep(wait_time)
                else:
                    raise e
        
        raise Exception("Max retries exceeded")
    
    def get_search_analytics(
        self,
        start_date: str,
        end_date: str,
        dimensions: List[str] = ['query', 'page'],
        row_limit: int = DEFAULT_ROW_LIMIT,
        filters: Optional[List[Dict]] = None
    ) -> pd.DataFrame:
        """
        Get search analytics data with pagination
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            dimensions: List of dimensions to query
            row_limit: Maximum rows to retrieve
            filters: Optional dimension filters
            
        Returns:
            DataFrame with search analytics data
        """
        all_rows = []
        start_row = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        while True:
            status_text.text(f"Fetching search data... {len(all_rows)} rows retrieved")
            
            # Build request body
            body = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': dimensions,
                'rowLimit': min(ROWS_PER_REQUEST, row_limit - len(all_rows)),
                'startRow': start_row
            }
            
            if filters:
                body['dimensionFilterGroups'] = [{'filters': filters}]
            
            # Execute request
            response = self.execute_with_retry(
                self.service.searchanalytics().query(
                    siteUrl=self.property_url,
                    body=body
                )
            )
            
            # Process response
            rows = response.get('rows', [])
            if not rows:
                break
                
            all_rows.extend(rows)
            
            # Update progress
            progress = min(len(all_rows) / row_limit, 1.0)
            progress_bar.progress(progress)
            
            # Check if we have all data or hit the limit
            if len(rows) < ROWS_PER_REQUEST or len(all_rows) >= row_limit:
                break
                
            start_row += len(rows)
        
        progress_bar.empty()
        status_text.empty()
        
        # Convert to DataFrame
        if all_rows:
            df = pd.DataFrame(all_rows)
            
            # Extract dimension values
            for i, dim in enumerate(dimensions):
                df[dim] = df['keys'].apply(lambda x: x[i])
            
            # Drop the keys column
            df = df.drop('keys', axis=1)
            
            return df
        else:
            return pd.DataFrame()
    
    def get_all_search_data(self, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        Get comprehensive search analytics data
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary of DataFrames by dimension combination
        """
        st.info("Collecting search analytics data...")
        
        data = {}
        
        # Different dimension combinations for different analyses
        dimension_sets = [
            (['query'], 'queries'),
            (['page'], 'pages'),
            (['query', 'page'], 'query_page'),
            (['page', 'device'], 'page_device'),
            (['page', 'country'], 'page_country'),
            (['date', 'page'], 'page_trends'),
            (['date', 'query'], 'query_trends')
        ]
        
        for dimensions, name in dimension_sets:
            with st.spinner(f"Fetching {name} data..."):
                data[name] = self.get_search_analytics(
                    start_date, end_date, 
                    dimensions=dimensions,
                    row_limit=25000
                )
        
        return data
    
    def get_url_inspection_batch(self, urls: List[str]) -> Dict[str, Dict]:
        """
        Inspect multiple URLs using URL Inspection API
        
        Args:
            urls: List of URLs to inspect
            
        Returns:
            Dictionary of inspection results by URL
        """
        results = {}
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, url in enumerate(urls):
            status_text.text(f"Inspecting URL {i+1}/{len(urls)}")
            
            try:
                response = self.execute_with_retry(
                    self.service.urlInspection().index().inspect(
                        body={
                            'inspectionUrl': url,
                            'siteUrl': self.property_url
                        }
                    )
                )
                results[url] = response.get('inspectionResult', {})
                
            except HttpError as e:
                results[url] = {'error': str(e)}
            
            progress_bar.progress((i + 1) / len(urls))
        
        progress_bar.empty()
        status_text.empty()
        
        return results
    
    def get_index_coverage(self) -> pd.DataFrame:
        """
        Get index coverage data by page indexing status
        
        Returns:
            DataFrame with indexing status counts
        """
        # Note: Index coverage detailed API is not available in v1
        # We simulate this by inspecting a sample of URLs
        st.info("Note: Detailed index coverage requires URL inspection of sample pages")
        
        # Get all pages from search analytics
        pages_df = self.get_search_analytics(
            *self.get_date_range(30),
            dimensions=['page'],
            row_limit=1000
        )
        
        if pages_df.empty:
            return pd.DataFrame()
        
        # Sample top pages for inspection
        sample_size = min(100, len(pages_df))
        sample_urls = pages_df.nlargest(sample_size, 'clicks')['page'].tolist()
        
        # Inspect URLs
        inspection_results = self.get_url_inspection_batch(sample_urls)
        
        # Categorize results
        status_counts = {}
        for url, result in inspection_results.items():
            if 'error' in result:
                status = 'Error'
            else:
                coverage = result.get('indexStatusResult', {})
                status = coverage.get('coverageState', 'Unknown')
            
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return pd.DataFrame(
            list(status_counts.items()),
            columns=['Status', 'Count']
        )
    
    def get_sitemaps(self) -> pd.DataFrame:
        """
        Get submitted sitemaps information
        
        Returns:
            DataFrame with sitemap details
        """
        try:
            response = self.execute_with_retry(
                self.service.sitemaps().list(siteUrl=self.property_url)
            )
            
            sitemaps = response.get('sitemap', [])
            
            if sitemaps:
                return pd.DataFrame(sitemaps)
            else:
                return pd.DataFrame()
                
        except HttpError as e:
            st.error(f"Error fetching sitemaps: {str(e)}")
            return pd.DataFrame()
    
    def get_crawl_stats(self) -> Dict:
        """
        Get crawl stats data
        
        Returns:
            Dictionary with crawl statistics
        """
        # Note: Crawl stats API is not available in v1
        # This would need to be scraped from the web interface or estimated
        return {
            'note': 'Detailed crawl stats require web interface access',
            'recommendation': 'Check crawl stats in GSC web interface'
        }


class PageSpeedDataCollector:
    """Handles data collection from PageSpeed Insights API"""
    
    def __init__(self):
        self.api_key = PAGESPEED_API_KEY
        self.base_url = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
    
    def analyze_url(self, url: str, strategy: str = 'mobile') -> Dict:
        """
        Analyze a URL using PageSpeed Insights
        
        Args:
            url: URL to analyze
            strategy: 'mobile' or 'desktop'
            
        Returns:
            Dictionary with PageSpeed data
        """
        params = {
            'url': url,
            'strategy': strategy,
            'category': ['performance', 'accessibility', 'best-practices', 'seo']
        }
        
        if self.api_key:
            params['key'] = self.api_key
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}
    
    def analyze_urls_batch(self, urls: List[str], strategies: List[str] = ['mobile']) -> Dict[str, Dict]:
        """
        Analyze multiple URLs
        
        Args:
            urls: List of URLs to analyze
            strategies: List of strategies to test
            
        Returns:
            Dictionary of results by URL and strategy
        """
        results = {}
        total = len(urls) * len(strategies)
        current = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for url in urls:
            results[url] = {}
            
            for strategy in strategies:
                current += 1
                status_text.text(f"Analyzing {url} ({strategy})... {current}/{total}")
                
                result = self.analyze_url(url, strategy)
                results[url][strategy] = result
                
                progress_bar.progress(current / total)
                
                # Rate limiting (without API key: 1 request per second)
                if not self.api_key:
                    time.sleep(1)
        
        progress_bar.empty()
        status_text.empty()
        
        return results
    
    def extract_metrics(self, result: Dict) -> Dict:
        """
        Extract key metrics from PageSpeed result
        
        Args:
            result: PageSpeed API response
            
        Returns:
            Dictionary of extracted metrics
        """
        if 'error' in result:
            return {'error': result['error']}
        
        metrics = {}
        
        # Lighthouse scores
        categories = result.get('lighthouseResult', {}).get('categories', {})
        for category, data in categories.items():
            metrics[f'{category}_score'] = data.get('score', 0) * 100
        
        # Core Web Vitals
        metrics_data = result.get('loadingExperience', {}).get('metrics', {})
        
        if 'LARGEST_CONTENTFUL_PAINT_MS' in metrics_data:
            metrics['lcp'] = metrics_data['LARGEST_CONTENTFUL_PAINT_MS']['percentile']
            
        if 'INTERACTION_TO_NEXT_PAINT' in metrics_data:
            metrics['inp'] = metrics_data['INTERACTION_TO_NEXT_PAINT']['percentile']
            
        if 'CUMULATIVE_LAYOUT_SHIFT_SCORE' in metrics_data:
            metrics['cls'] = metrics_data['CUMULATIVE_LAYOUT_SHIFT_SCORE']['percentile'] / 100
        
        # Overall CWV assessment
        metrics['cwv_passed'] = result.get('loadingExperience', {}).get('overall_category', 'SLOW') == 'FAST'
        
        return metrics


def collect_all_data(property_url: str, date_range_days: int = 90) -> Dict:
    """
    Main function to collect all data needed for audit
    
    Args:
        property_url: GSC property URL
        date_range_days: Number of days to analyze
        
    Returns:
        Dictionary with all collected data
    """
    if 'gsc_service' not in st.session_state:
        st.error("Not authenticated. Please authenticate first.")
        return {}
    
    # Initialize collectors
    gsc_collector = GSCDataCollector(st.session_state.gsc_service, property_url)
    pagespeed_collector = PageSpeedDataCollector()
    
    # Calculate date range
    start_date, end_date = gsc_collector.get_date_range(date_range_days)
    
    # Collect all data
    data = {
        'property_url': property_url,
        'date_range': {'start': start_date, 'end': end_date},
        'collection_timestamp': datetime.now().isoformat()
    }
    
    # 1. Search Analytics Data
    with st.spinner("Collecting search analytics data..."):
        data['search_analytics'] = gsc_collector.get_all_search_data(start_date, end_date)
    
    # 2. Index Coverage (sample)
    with st.spinner("Checking index coverage..."):
        data['index_coverage'] = gsc_collector.get_index_coverage()
    
    # 3. Sitemaps
    with st.spinner("Fetching sitemap data..."):
        data['sitemaps'] = gsc_collector.get_sitemaps()
    
    # 4. PageSpeed data for top pages
    with st.spinner("Analyzing Core Web Vitals..."):
        if 'pages' in data['search_analytics'] and not data['search_analytics']['pages'].empty:
            top_pages = data['search_analytics']['pages'].nlargest(10, 'clicks')['page'].tolist()
            data['pagespeed'] = pagespeed_collector.analyze_urls_batch(top_pages, ['mobile', 'desktop'])
        else:
            data['pagespeed'] = {}
    
    # 5. Crawl stats (placeholder)
    data['crawl_stats'] = gsc_collector.get_crawl_stats()
    
    # Store in session state
    st.session_state.gsc_data = data
    st.session_state.data_loaded = True
    
    return data