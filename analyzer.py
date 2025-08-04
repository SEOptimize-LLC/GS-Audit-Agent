"""
Data Analysis Module for GSC Audit Tool
Analyzes collected data to identify patterns, issues, and opportunities
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import streamlit as st

from config import (
    CANNIBALIZATION_THRESHOLD, STRIKING_DISTANCE, LOW_CTR_THRESHOLD,
    CONTENT_QUALITY_SIGNALS, PERFORMANCE_DECLINE_THRESHOLD,
    MOBILE_DESKTOP_GAP_THRESHOLD, CWV_THRESHOLDS
)


class GSCAnalyzer:
    """Main analyzer class for GSC data"""
    
    def __init__(self, data: Dict):
        self.data = data
        self.search_data = data.get('search_analytics', {})
        self.insights = []
        
    def run_full_analysis(self) -> Dict:
        """
        Run all analysis modules
        
        Returns:
            Dictionary with all analysis results
        """
        st.info("Running comprehensive analysis...")
        
        results = {}
        
        # 1. Keyword Cannibalization Analysis
        with st.spinner("Detecting keyword cannibalization..."):
            results['cannibalization'] = self.detect_keyword_cannibalization()
        
        # 2. Content Quality Signals
        with st.spinner("Analyzing content quality signals..."):
            results['content_quality'] = self.analyze_content_quality_signals()
        
        # 3. Opportunity Analysis
        with st.spinner("Identifying opportunities..."):
            results['opportunities'] = self.find_opportunities()
        
        # 4. Performance Trends
        with st.spinner("Analyzing performance trends..."):
            results['trends'] = self.analyze_performance_trends()
        
        # 5. Technical Issues
        with st.spinner("Checking technical issues..."):
            results['technical'] = self.analyze_technical_issues()
        
        # 6. Mobile vs Desktop Analysis
        with st.spinner("Comparing mobile vs desktop performance..."):
            results['device_comparison'] = self.analyze_device_performance()
        
        # 7. Core Web Vitals Analysis
        with st.spinner("Analyzing Core Web Vitals..."):
            results['cwv'] = self.analyze_core_web_vitals()
        
        # Store results
        self.results = results
        return results
    
    def detect_keyword_cannibalization(self) -> List[Dict]:
        """
        Detect multiple pages competing for the same keywords
        
        Returns:
            List of cannibalization cases
        """
        if 'query_page' not in self.search_data or self.search_data['query_page'].empty:
            return []
        
        df = self.search_data['query_page'].copy()
        
        # Group by query to find queries with multiple pages
        query_stats = df.groupby('query').agg({
            'page': 'nunique',
            'impressions': 'sum',
            'clicks': 'sum'
        }).reset_index()
        
        # Filter for queries with multiple pages and sufficient impressions
        cannibalized = query_stats[
            (query_stats['page'] >= CANNIBALIZATION_THRESHOLD['min_pages']) &
            (query_stats['impressions'] >= CANNIBALIZATION_THRESHOLD['min_impressions'])
        ]
        
        cannibalization_cases = []
        
        for _, row in cannibalized.iterrows():
            query = row['query']
            
            # Get all pages for this query
            pages_data = df[df['query'] == query].copy()
            pages_data['ctr'] = pages_data['clicks'] / pages_data['impressions']
            pages_data = pages_data.sort_values('clicks', ascending=False)
            
            # Calculate impact
            total_impressions = pages_data['impressions'].sum()
            total_clicks = pages_data['clicks'].sum()
            avg_position = (pages_data['position'] * pages_data['impressions']).sum() / total_impressions
            
            # Estimate potential if consolidated
            best_position = pages_data['position'].min()
            position_improvement = avg_position - best_position
            
            # CTR improvement estimate (rough calculation)
            current_ctr = total_clicks / total_impressions
            estimated_ctr = self.estimate_ctr_for_position(best_position)
            potential_clicks = total_impressions * estimated_ctr
            
            case = {
                'query': query,
                'pages_affected': len(pages_data),
                'pages': pages_data[['page', 'clicks', 'impressions', 'position', 'ctr']].to_dict('records'),
                'total_impressions': total_impressions,
                'total_clicks': total_clicks,
                'current_avg_position': avg_position,
                'best_position': best_position,
                'position_improvement_potential': position_improvement,
                'current_ctr': current_ctr,
                'potential_ctr': estimated_ctr,
                'potential_additional_clicks': max(0, potential_clicks - total_clicks),
                'priority': 'high' if total_impressions > 1000 else 'medium'
            }
            
            cannibalization_cases.append(case)
        
        # Sort by opportunity size
        cannibalization_cases.sort(key=lambda x: x['potential_additional_clicks'], reverse=True)
        
        return cannibalization_cases
    
    def analyze_content_quality_signals(self) -> Dict:
        """
        Analyze signals that indicate content quality issues
        
        Returns:
            Dictionary with content quality analysis
        """
        quality_issues = {
            'low_ctr_pages': [],
            'zero_click_pages': [],
            'declining_pages': [],
            'low_impression_pages': []
        }
        
        # 1. Low CTR despite high impressions
        if 'pages' in self.search_data and not self.search_data['pages'].empty:
            pages_df = self.search_data['pages'].copy()
            pages_df['ctr'] = pages_df['clicks'] / pages_df['impressions']
            
            low_ctr = pages_df[
                (pages_df['impressions'] >= LOW_CTR_THRESHOLD['min_impressions']) &
                (pages_df['ctr'] <= LOW_CTR_THRESHOLD['max_ctr'])
            ]
            
            quality_issues['low_ctr_pages'] = low_ctr[['page', 'clicks', 'impressions', 'ctr']].to_dict('records')
        
        # 2. Pages with zero clicks despite impressions
        if 'pages' in self.search_data:
            zero_clicks = pages_df[
                (pages_df['impressions'] > 100) &
                (pages_df['clicks'] == 0)
            ]
            quality_issues['zero_click_pages'] = zero_clicks[['page', 'impressions', 'position']].to_dict('records')
        
        # 3. Declining performance (requires trend data)
        if 'page_trends' in self.search_data and not self.search_data['page_trends'].empty:
            declining = self.detect_declining_pages()
            quality_issues['declining_pages'] = declining
        
        # 4. Summary statistics
        quality_issues['summary'] = {
            'total_pages_analyzed': len(pages_df) if 'pages_df' in locals() else 0,
            'low_ctr_count': len(quality_issues['low_ctr_pages']),
            'zero_click_count': len(quality_issues['zero_click_pages']),
            'declining_count': len(quality_issues['declining_pages']),
            'quality_score': self.calculate_quality_score(quality_issues)
        }
        
        return quality_issues
    
    def find_opportunities(self) -> Dict:
        """
        Find optimization opportunities
        
        Returns:
            Dictionary with different opportunity types
        """
        opportunities = {
            'striking_distance': [],
            'featured_snippet_opportunities': [],
            'quick_wins': [],
            'content_gaps': []
        }
        
        # 1. Striking distance keywords
        if 'queries' in self.search_data and not self.search_data['queries'].empty:
            queries_df = self.search_data['queries'].copy()
            
            striking = queries_df[
                (queries_df['position'] >= STRIKING_DISTANCE['min_position']) &
                (queries_df['position'] <= STRIKING_DISTANCE['max_position']) &
                (queries_df['impressions'] >= STRIKING_DISTANCE['min_impressions'])
            ].copy()
            
            striking['potential_clicks'] = striking['impressions'] * self.estimate_ctr_for_position(7)
            striking['click_increase'] = striking['potential_clicks'] - striking['clicks']
            
            opportunities['striking_distance'] = striking.nlargest(
                20, 'click_increase'
            )[['query', 'position', 'impressions', 'clicks', 'potential_clicks', 'click_increase']].to_dict('records')
        
        # 2. Featured snippet opportunities (question queries)
        question_patterns = ['what', 'how', 'why', 'when', 'where', 'who', 'is', 'can', 'does']
        
        if 'queries' in self.search_data:
            question_queries = queries_df[
                queries_df['query'].str.lower().str.startswith(tuple(question_patterns))
            ]
            
            # Focus on position 2-10 (position 1 might already have snippet)
            snippet_opportunities = question_queries[
                (question_queries['position'] >= 2) &
                (question_queries['position'] <= 10) &
                (question_queries['impressions'] > 50)
            ]
            
            opportunities['featured_snippet_opportunities'] = snippet_opportunities.nlargest(
                10, 'impressions'
            )[['query', 'position', 'impressions', 'clicks']].to_dict('records')
        
        # 3. Quick wins (small improvements with big impact)
        quick_wins = []
        
        # Title/meta description optimization opportunities
        for page in opportunities.get('low_ctr_pages', [])[:10]:
            quick_wins.append({
                'type': 'meta_optimization',
                'page': page['page'],
                'current_ctr': page['ctr'],
                'expected_ctr': self.estimate_ctr_for_position(page.get('position', 10)),
                'impressions': page['impressions'],
                'potential_additional_clicks': page['impressions'] * (self.estimate_ctr_for_position(page.get('position', 10)) - page['ctr'])
            })
        
        opportunities['quick_wins'] = quick_wins
        
        return opportunities
    
    def analyze_performance_trends(self) -> Dict:
        """
        Analyze performance trends over time
        
        Returns:
            Dictionary with trend analysis
        """
        trends = {
            'overall_trend': 'stable',
            'growth_rate': 0,
            'volatility': 'low',
            'seasonal_patterns': [],
            'recent_changes': []
        }
        
        if 'page_trends' not in self.search_data or self.search_data['page_trends'].empty:
            return trends
        
        # Aggregate daily data
        daily_data = self.search_data['page_trends'].groupby('date').agg({
            'clicks': 'sum',
            'impressions': 'sum'
        }).reset_index()
        
        daily_data['date'] = pd.to_datetime(daily_data['date'])
        daily_data = daily_data.sort_values('date')
        
        # Calculate trend
        if len(daily_data) > 30:
            # Compare last 30 days to previous 30 days
            last_30 = daily_data.tail(30)['clicks'].sum()
            prev_30 = daily_data.iloc[-60:-30]['clicks'].sum() if len(daily_data) > 60 else last_30
            
            growth_rate = ((last_30 - prev_30) / prev_30 * 100) if prev_30 > 0 else 0
            trends['growth_rate'] = growth_rate
            
            if growth_rate > 10:
                trends['overall_trend'] = 'growing'
            elif growth_rate < -10:
                trends['overall_trend'] = 'declining'
            else:
                trends['overall_trend'] = 'stable'
        
        # Detect volatility
        if len(daily_data) > 7:
            daily_data['clicks_7d_avg'] = daily_data['clicks'].rolling(7).mean()
            daily_data['deviation'] = abs(daily_data['clicks'] - daily_data['clicks_7d_avg'])
            avg_deviation = daily_data['deviation'].mean()
            
            if avg_deviation / daily_data['clicks'].mean() > 0.3:
                trends['volatility'] = 'high'
            elif avg_deviation / daily_data['clicks'].mean() > 0.15:
                trends['volatility'] = 'medium'
            else:
                trends['volatility'] = 'low'
        
        return trends
    
    def analyze_technical_issues(self) -> Dict:
        """
        Analyze technical SEO issues
        
        Returns:
            Dictionary with technical issues
        """
        issues = {
            'indexing_issues': [],
            'sitemap_issues': [],
            'crawl_issues': [],
            'security_issues': []
        }
        
        # 1. Indexing issues from URL inspection
        if 'index_coverage' in self.data and not self.data['index_coverage'].empty:
            coverage_df = self.data['index_coverage']
            
            # Flag concerning statuses
            concerning_statuses = ['Error', 'Excluded by noindex tag', 'Blocked by robots.txt']
            
            for status in concerning_statuses:
                count = coverage_df[coverage_df['Status'] == status]['Count'].sum()
                if count > 0:
                    issues['indexing_issues'].append({
                        'issue': status,
                        'affected_urls': count,
                        'severity': 'high' if 'Error' in status else 'medium'
                    })
        
        # 2. Sitemap issues
        if 'sitemaps' in self.data and not self.data['sitemaps'].empty:
            sitemaps_df = self.data['sitemaps']
            
            for _, sitemap in sitemaps_df.iterrows():
                if sitemap.get('errors', 0) > 0:
                    issues['sitemap_issues'].append({
                        'sitemap': sitemap.get('path', 'Unknown'),
                        'errors': sitemap.get('errors', 0),
                        'warnings': sitemap.get('warnings', 0)
                    })
        
        return issues
    
    def analyze_device_performance(self) -> Dict:
        """
        Compare mobile vs desktop performance
        
        Returns:
            Dictionary with device comparison
        """
        comparison = {
            'mobile_desktop_gap': 0,
            'problematic_pages': [],
            'device_summary': {}
        }
        
        if 'page_device' not in self.search_data or self.search_data['page_device'].empty:
            return comparison
        
        df = self.search_data['page_device'].copy()
        
        # Pivot to compare devices
        device_pivot = df.pivot_table(
            index='page',
            columns='device',
            values=['clicks', 'impressions', 'position'],
            aggfunc='sum'
        )
        
        # Find pages with significant mobile/desktop gaps
        problematic = []
        
        for page in device_pivot.index:
            try:
                mobile_pos = device_pivot.loc[page, ('position', 'MOBILE')]
                desktop_pos = device_pivot.loc[page, ('position', 'DESKTOP')]
                
                gap = mobile_pos - desktop_pos
                
                if abs(gap) >= MOBILE_DESKTOP_GAP_THRESHOLD:
                    problematic.append({
                        'page': page,
                        'mobile_position': mobile_pos,
                        'desktop_position': desktop_pos,
                        'position_gap': gap,
                        'mobile_clicks': device_pivot.loc[page, ('clicks', 'MOBILE')],
                        'desktop_clicks': device_pivot.loc[page, ('clicks', 'DESKTOP')]
                    })
            except:
                continue
        
        comparison['problematic_pages'] = sorted(problematic, key=lambda x: abs(x['position_gap']), reverse=True)[:20]
        
        # Overall device summary
        device_totals = df.groupby('device').agg({
            'clicks': 'sum',
            'impressions': 'sum'
        })
        
        comparison['device_summary'] = device_totals.to_dict('index')
        
        return comparison
    
    def analyze_core_web_vitals(self) -> Dict:
        """
        Analyze Core Web Vitals data
        
        Returns:
            Dictionary with CWV analysis
        """
        cwv_analysis = {
            'overall_status': 'unknown',
            'failing_pages': [],
            'metric_summary': {},
            'recommendations': []
        }
        
        if 'pagespeed' not in self.data or not self.data['pagespeed']:
            return cwv_analysis
        
        # Analyze PageSpeed data
        failing_pages = []
        metric_totals = {'lcp': [], 'inp': [], 'cls': []}
        
        for url, strategies in self.data['pagespeed'].items():
            for strategy, data in strategies.items():
                if 'error' in data:
                    continue
                
                metrics = self.extract_cwv_metrics(data)
                
                # Check against thresholds
                failures = []
                
                if metrics.get('lcp', 0) > CWV_THRESHOLDS['LCP']['needs_improvement']:
                    failures.append('LCP')
                    metric_totals['lcp'].append(metrics.get('lcp', 0))
                
                if metrics.get('inp', 0) > CWV_THRESHOLDS['INP']['needs_improvement']:
                    failures.append('INP')
                    metric_totals['inp'].append(metrics.get('inp', 0))
                
                if metrics.get('cls', 0) > CWV_THRESHOLDS['CLS']['needs_improvement']:
                    failures.append('CLS')
                    metric_totals['cls'].append(metrics.get('cls', 0))
                
                if failures:
                    failing_pages.append({
                        'url': url,
                        'strategy': strategy,
                        'failing_metrics': failures,
                        'metrics': metrics
                    })
        
        cwv_analysis['failing_pages'] = failing_pages
        
        # Calculate summary
        for metric, values in metric_totals.items():
            if values:
                cwv_analysis['metric_summary'][metric] = {
                    'average': np.mean(values),
                    'worst': max(values),
                    'failing_count': len([v for v in values if v > CWV_THRESHOLDS[metric.upper()]['needs_improvement']])
                }
        
        # Overall status
        total_pages = len(self.data['pagespeed'])
        failing_count = len(failing_pages)
        
        if failing_count == 0:
            cwv_analysis['overall_status'] = 'good'
        elif failing_count / total_pages < 0.25:
            cwv_analysis['overall_status'] = 'needs_improvement'
        else:
            cwv_analysis['overall_status'] = 'poor'
        
        return cwv_analysis
    
    # Helper methods
    
    def estimate_ctr_for_position(self, position: float) -> float:
        """
        Estimate CTR based on position
        
        Args:
            position: Average position
            
        Returns:
            Estimated CTR
        """
        # Rough CTR curve based on industry averages
        ctr_curve = {
            1: 0.28, 2: 0.15, 3: 0.11, 4: 0.08, 5: 0.07,
            6: 0.05, 7: 0.04, 8: 0.03, 9: 0.03, 10: 0.03
        }
        
        if position <= 10:
            return ctr_curve.get(int(position), 0.02)
        elif position <= 20:
            return 0.01
        else:
            return 0.005
    
    def detect_declining_pages(self) -> List[Dict]:
        """
        Detect pages with declining performance
        
        Returns:
            List of declining pages
        """
        if 'page_trends' not in self.search_data:
            return []
        
        df = self.search_data['page_trends'].copy()
        df['date'] = pd.to_datetime(df['date'])
        
        # Get last 30 days and previous 30 days
        cutoff_date = df['date'].max() - timedelta(days=30)
        
        recent = df[df['date'] > cutoff_date].groupby('page')['clicks'].sum()
        previous = df[df['date'] <= cutoff_date].groupby('page')['clicks'].sum()
        
        # Calculate change
        declining = []
        
        for page in set(recent.index) & set(previous.index):
            if previous[page] > 10:  # Minimum threshold
                change_pct = ((recent[page] - previous[page]) / previous[page]) * 100
                
                if change_pct < PERFORMANCE_DECLINE_THRESHOLD:
                    declining.append({
                        'page': page,
                        'previous_clicks': previous[page],
                        'recent_clicks': recent[page],
                        'change_percent': change_pct
                    })
        
        return sorted(declining, key=lambda x: x['change_percent'])[:20]
    
    def calculate_quality_score(self, quality_issues: Dict) -> float:
        """
        Calculate overall content quality score
        
        Args:
            quality_issues: Dictionary of quality issues
            
        Returns:
            Quality score (0-100)
        """
        total_pages = quality_issues['summary'].get('total_pages_analyzed', 1)
        
        if total_pages == 0:
            return 0
        
        # Deduct points for issues
        score = 100
        
        # Low CTR pages (max -20 points)
        low_ctr_ratio = len(quality_issues['low_ctr_pages']) / total_pages
        score -= min(20, low_ctr_ratio * 100)
        
        # Zero click pages (max -15 points)
        zero_click_ratio = len(quality_issues['zero_click_pages']) / total_pages
        score -= min(15, zero_click_ratio * 50)
        
        # Declining pages (max -15 points)
        declining_ratio = len(quality_issues['declining_pages']) / total_pages
        score -= min(15, declining_ratio * 50)
        
        return max(0, score)
    
    def extract_cwv_metrics(self, pagespeed_data: Dict) -> Dict:
        """
        Extract Core Web Vitals metrics from PageSpeed data
        
        Args:
            pagespeed_data: PageSpeed API response
            
        Returns:
            Dictionary of CWV metrics
        """
        metrics = {}
        
        loading_experience = pagespeed_data.get('loadingExperience', {}).get('metrics', {})
        
        if 'LARGEST_CONTENTFUL_PAINT_MS' in loading_experience:
            metrics['lcp'] = loading_experience['LARGEST_CONTENTFUL_PAINT_MS']['percentile']
        
        if 'INTERACTION_TO_NEXT_PAINT' in loading_experience:
            metrics['inp'] = loading_experience['INTERACTION_TO_NEXT_PAINT']['percentile']
        
        if 'CUMULATIVE_LAYOUT_SHIFT_SCORE' in loading_experience:
            metrics['cls'] = loading_experience['CUMULATIVE_LAYOUT_SHIFT_SCORE']['percentile'] / 100
        
        return metrics