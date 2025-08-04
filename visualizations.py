"""
Data Visualization Module for GSC Audit Tool
Creates charts and visualizations for the audit report
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from config import CHART_COLORS, CWV_THRESHOLDS


class GSCVisualizer:
    """Creates visualizations for GSC audit data"""
    
    def __init__(self):
        self.colors = CHART_COLORS
        
    def create_performance_overview(self, search_data: Dict) -> go.Figure:
        """
        Create performance overview chart with clicks and impressions
        
        Args:
            search_data: Search analytics data
            
        Returns:
            Plotly figure
        """
        if 'page_trends' not in search_data or search_data['page_trends'].empty:
            return None
        
        # Aggregate by date
        df = search_data['page_trends'].groupby('date').agg({
            'clicks': 'sum',
            'impressions': 'sum'
        }).reset_index()
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Create figure with secondary y-axis
        fig = make_subplots(
            rows=1, cols=1,
            specs=[[{"secondary_y": True}]],
            subplot_titles=['Search Performance Over Time']
        )
        
        # Add clicks trace
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['clicks'],
                mode='lines',
                name='Clicks',
                line=dict(color=self.colors['primary'], width=3)
            ),
            secondary_y=False
        )
        
        # Add impressions trace
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['impressions'],
                mode='lines',
                name='Impressions',
                line=dict(color=self.colors['secondary'], width=2, dash='dot')
            ),
            secondary_y=True
        )
        
        # Update layout
        fig.update_xaxes(title_text="Date")
        fig.update_yaxes(title_text="Clicks", secondary_y=False)
        fig.update_yaxes(title_text="Impressions", secondary_y=True)
        
        fig.update_layout(
            height=400,
            hovermode='x unified',
            showlegend=True,
            legend=dict(x=0, y=1.1, orientation='h')
        )
        
        return fig
    
    def create_cannibalization_chart(self, cannibalization_data: List[Dict]) -> go.Figure:
        """
        Create visualization for keyword cannibalization
        
        Args:
            cannibalization_data: List of cannibalization cases
            
        Returns:
            Plotly figure
        """
        if not cannibalization_data:
            return None
        
        # Get top 10 cases by opportunity
        top_cases = sorted(
            cannibalization_data,
            key=lambda x: x['potential_additional_clicks'],
            reverse=True
        )[:10]
        
        # Prepare data
        queries = []
        current_clicks = []
        potential_clicks = []
        
        for case in top_cases:
            queries.append(case['query'][:30] + '...' if len(case['query']) > 30 else case['query'])
            current_clicks.append(case['total_clicks'])
            potential_clicks.append(case['total_clicks'] + case['potential_additional_clicks'])
        
        # Create grouped bar chart
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Current Clicks',
            y=queries,
            x=current_clicks,
            orientation='h',
            marker_color=self.colors['warning']
        ))
        
        fig.add_trace(go.Bar(
            name='Potential Clicks',
            y=queries,
            x=[p - c for p, c in zip(potential_clicks, current_clicks)],
            orientation='h',
            marker_color=self.colors['success']
        ))
        
        fig.update_layout(
            title='Top Keyword Cannibalization Opportunities',
            xaxis_title='Monthly Clicks',
            yaxis_title='Query',
            barmode='stack',
            height=400,
            showlegend=True,
            legend=dict(x=0.5, y=-0.15, orientation='h')
        )
        
        return fig
    
    def create_device_comparison_chart(self, device_data: Dict) -> go.Figure:
        """
        Create device performance comparison chart
        
        Args:
            device_data: Device comparison data
            
        Returns:
            Plotly figure
        """
        if not device_data.get('device_summary'):
            return None
        
        summary = device_data['device_summary']
        
        # Create pie chart for traffic distribution
        devices = list(summary.keys())
        clicks = [summary[d]['clicks'] for d in devices]
        
        fig = make_subplots(
            rows=1, cols=2,
            specs=[[{'type': 'pie'}, {'type': 'bar'}]],
            subplot_titles=['Traffic Distribution by Device', 'Top Pages with Mobile/Desktop Gap']
        )
        
        # Pie chart
        fig.add_trace(
            go.Pie(
                labels=devices,
                values=clicks,
                hole=0.4,
                marker_colors=[self.colors['primary'], self.colors['secondary'], self.colors['info']]
            ),
            row=1, col=1
        )
        
        # Bar chart for problematic pages
        if device_data.get('problematic_pages'):
            pages = []
            gaps = []
            
            for page in device_data['problematic_pages'][:5]:
                page_name = page['page'].split('/')[-1] or 'Homepage'
                if len(page_name) > 20:
                    page_name = page_name[:20] + '...'
                pages.append(page_name)
                gaps.append(page['position_gap'])
            
            fig.add_trace(
                go.Bar(
                    x=pages,
                    y=gaps,
                    marker_color=[self.colors['danger'] if g > 0 else self.colors['success'] for g in gaps],
                    text=[f"{g:+.1f}" for g in gaps],
                    textposition='auto'
                ),
                row=1, col=2
            )
        
        fig.update_layout(height=400, showlegend=False)
        fig.update_xaxes(title_text="Page", row=1, col=2)
        fig.update_yaxes(title_text="Position Gap (Mobile - Desktop)", row=1, col=2)
        
        return fig
    
    def create_opportunities_chart(self, opportunities: Dict) -> go.Figure:
        """
        Create opportunities visualization
        
        Args:
            opportunities: Opportunities data
            
        Returns:
            Plotly figure
        """
        if not opportunities.get('striking_distance'):
            return None
        
        # Get top opportunities
        top_opps = opportunities['striking_distance'][:15]
        
        df = pd.DataFrame(top_opps)
        
        # Create scatter plot
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['position'],
            y=df['impressions'],
            mode='markers',
            marker=dict(
                size=df['click_increase'] / 10,  # Size by opportunity
                color=df['click_increase'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Potential<br>Clicks")
            ),
            text=[f"Query: {q}<br>Current Pos: {p:.1f}<br>Potential Clicks: +{c:.0f}" 
                  for q, p, c in zip(df['query'], df['position'], df['click_increase'])],
            hovertemplate='%{text}<extra></extra>'
        ))
        
        # Add striking distance zone
        fig.add_vrect(
            x0=11, x1=20,
            fillcolor=self.colors['info'],
            opacity=0.1,
            line_width=0,
            annotation_text="Striking Distance Zone",
            annotation_position="top"
        )
        
        fig.update_layout(
            title='Keyword Opportunities by Position and Potential',
            xaxis_title='Current Position',
            yaxis_title='Monthly Impressions',
            height=400
        )
        
        fig.update_xaxes(range=[10, 21])
        
        return fig
    
    def create_cwv_summary_chart(self, cwv_data: Dict) -> go.Figure:
        """
        Create Core Web Vitals summary chart
        
        Args:
            cwv_data: CWV analysis data
            
        Returns:
            Plotly figure
        """
        if not cwv_data.get('metric_summary'):
            return None
        
        metrics = ['LCP', 'INP', 'CLS']
        values = []
        colors = []
        
        for metric in metrics:
            if metric.lower() in cwv_data['metric_summary']:
                value = cwv_data['metric_summary'][metric.lower()]['average']
                values.append(value)
                
                # Determine color based on thresholds
                if metric == 'CLS':
                    if value <= CWV_THRESHOLDS[metric]['good']:
                        colors.append(self.colors['success'])
                    elif value <= CWV_THRESHOLDS[metric]['needs_improvement']:
                        colors.append(self.colors['warning'])
                    else:
                        colors.append(self.colors['danger'])
                else:
                    if value <= CWV_THRESHOLDS[metric]['good']:
                        colors.append(self.colors['success'])
                    elif value <= CWV_THRESHOLDS[metric]['needs_improvement']:
                        colors.append(self.colors['warning'])
                    else:
                        colors.append(self.colors['danger'])
            else:
                values.append(0)
                colors.append(self.colors['info'])
        
        # Create gauge charts
        fig = make_subplots(
            rows=1, cols=3,
            specs=[[{'type': 'indicator'}, {'type': 'indicator'}, {'type': 'indicator'}]],
            subplot_titles=['LCP (Loading)', 'INP (Interactivity)', 'CLS (Stability)']
        )
        
        # LCP gauge
        if values[0] > 0:
            fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=values[0] / 1000,  # Convert to seconds
                number={'suffix': 's'},
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={
                    'axis': {'range': [None, 6]},
                    'bar': {'color': colors[0]},
                    'steps': [
                        {'range': [0, 2.5], 'color': "lightgray"},
                        {'range': [2.5, 4], 'color': "gray"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 4
                    }
                }
            ), row=1, col=1)
        
        # INP gauge
        if values[1] > 0:
            fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=values[1],
                number={'suffix': 'ms'},
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={
                    'axis': {'range': [None, 800]},
                    'bar': {'color': colors[1]},
                    'steps': [
                        {'range': [0, 200], 'color': "lightgray"},
                        {'range': [200, 500], 'color': "gray"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 500
                    }
                }
            ), row=1, col=2)
        
        # CLS gauge
        if values[2] > 0:
            fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=values[2],
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={
                    'axis': {'range': [None, 0.5]},
                    'bar': {'color': colors[2]},
                    'steps': [
                        {'range': [0, 0.1], 'color': "lightgray"},
                        {'range': [0.1, 0.25], 'color': "gray"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 0.25
                    }
                }
            ), row=1, col=3)
        
        fig.update_layout(height=300, showlegend=False)
        
        return fig
    
    def create_query_distribution_chart(self, search_data: Dict) -> go.Figure:
        """
        Create query performance distribution chart
        
        Args:
            search_data: Search analytics data
            
        Returns:
            Plotly figure
        """
        if 'queries' not in search_data or search_data['queries'].empty:
            return None
        
        df = search_data['queries'].copy()
        
        # Create position buckets
        df['position_bucket'] = pd.cut(
            df['position'],
            bins=[0, 3, 10, 20, 50, 100],
            labels=['1-3', '4-10', '11-20', '21-50', '50+']
        )
        
        # Aggregate by bucket
        bucket_stats = df.groupby('position_bucket').agg({
            'clicks': 'sum',
            'impressions': 'sum',
            'query': 'count'
        }).reset_index()
        
        bucket_stats['ctr'] = bucket_stats['clicks'] / bucket_stats['impressions'] * 100
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=[
                'Queries by Position Range',
                'Clicks by Position Range',
                'CTR by Position Range',
                'Top Queries Performance'
            ]
        )
        
        # Queries count
        fig.add_trace(
            go.Bar(
                x=bucket_stats['position_bucket'],
                y=bucket_stats['query'],
                marker_color=self.colors['primary']
            ),
            row=1, col=1
        )
        
        # Clicks
        fig.add_trace(
            go.Bar(
                x=bucket_stats['position_bucket'],
                y=bucket_stats['clicks'],
                marker_color=self.colors['success']
            ),
            row=1, col=2
        )
        
        # CTR
        fig.add_trace(
            go.Bar(
                x=bucket_stats['position_bucket'],
                y=bucket_stats['ctr'],
                marker_color=self.colors['info']
            ),
            row=2, col=1
        )
        
        # Top queries bubble chart
        top_queries = df.nlargest(20, 'impressions')
        fig.add_trace(
            go.Scatter(
                x=top_queries['impressions'],
                y=top_queries['clicks'],
                mode='markers',
                marker=dict(
                    size=10,
                    color=top_queries['position'],
                    colorscale='RdYlGn_r',
                    showscale=True,
                    colorbar=dict(title="Position")
                ),
                text=top_queries['query'],
                hovertemplate='Query: %{text}<br>Impressions: %{x}<br>Clicks: %{y}<extra></extra>'
            ),
            row=2, col=2
        )
        
        # Update axes
        fig.update_xaxes(title_text="Position Range", row=1, col=1)
        fig.update_xaxes(title_text="Position Range", row=1, col=2)
        fig.update_xaxes(title_text="Position Range", row=2, col=1)
        fig.update_xaxes(title_text="Impressions", row=2, col=2)
        
        fig.update_yaxes(title_text="Query Count", row=1, col=1)
        fig.update_yaxes(title_text="Clicks", row=1, col=2)
        fig.update_yaxes(title_text="CTR (%)", row=2, col=1)
        fig.update_yaxes(title_text="Clicks", row=2, col=2)
        
        fig.update_layout(height=800, showlegend=False)
        
        return fig
    
    def create_content_quality_chart(self, quality_data: Dict) -> go.Figure:
        """
        Create content quality visualization
        
        Args:
            quality_data: Content quality analysis data
            
        Returns:
            Plotly figure
        """
        if not quality_data.get('summary'):
            return None
        
        summary = quality_data['summary']
        
        # Create donut chart for issue distribution
        labels = ['Good Pages', 'Low CTR', 'Zero Clicks', 'Declining']
        
        total_pages = summary.get('total_pages_analyzed', 1)
        low_ctr = summary.get('low_ctr_count', 0)
        zero_click = summary.get('zero_click_count', 0)
        declining = summary.get('declining_count', 0)
        
        good_pages = max(0, total_pages - low_ctr - zero_click - declining)
        
        values = [good_pages, low_ctr, zero_click, declining]
        
        fig = go.Figure()
        
        fig.add_trace(go.Pie(
            labels=labels,
            values=values,
            hole=0.6,
            marker=dict(
                colors=[
                    self.colors['success'],
                    self.colors['warning'],
                    self.colors['danger'],
                    self.colors['info']
                ]
            ),
            textinfo='label+percent',
            textposition='outside'
        ))
        
        # Add quality score in the center
        quality_score = summary.get('quality_score', 0)
        fig.add_annotation(
            text=f"Quality Score<br><b>{quality_score:.0f}/100</b>",
            x=0.5, y=0.5,
            font=dict(size=20),
            showarrow=False
        )
        
        fig.update_layout(
            title='Content Quality Distribution',
            height=400,
            showlegend=True,
            legend=dict(x=1, y=0.5)
        )
        
        return fig


def create_audit_visualizations(data: Dict, analysis_results: Dict) -> Dict[str, go.Figure]:
    """
    Create all visualizations for the audit report
    
    Args:
        data: Raw GSC data
        analysis_results: Analysis results
        
    Returns:
        Dictionary of Plotly figures
    """
    visualizer = GSCVisualizer()
    charts = {}
    
    # Performance overview
    if 'search_analytics' in data:
        charts['performance_overview'] = visualizer.create_performance_overview(
            data['search_analytics']
        )
    
    # Cannibalization
    if analysis_results.get('cannibalization'):
        charts['cannibalization'] = visualizer.create_cannibalization_chart(
            analysis_results['cannibalization']
        )
    
    # Device comparison
    if analysis_results.get('device_comparison'):
        charts['device_comparison'] = visualizer.create_device_comparison_chart(
            analysis_results['device_comparison']
        )
    
    # Opportunities
    if analysis_results.get('opportunities'):
        charts['opportunities'] = visualizer.create_opportunities_chart(
            analysis_results['opportunities']
        )
    
    # Core Web Vitals
    if analysis_results.get('cwv'):
        charts['cwv_summary'] = visualizer.create_cwv_summary_chart(
            analysis_results['cwv']
        )
    
    # Query distribution
    if 'search_analytics' in data:
        charts['query_distribution'] = visualizer.create_query_distribution_chart(
            data['search_analytics']
        )
    
    # Content quality
    if analysis_results.get('content_quality'):
        charts['content_quality'] = visualizer.create_content_quality_chart(
            analysis_results['content_quality']
        )
    
    return {k: v for k, v in charts.items() if v is not None}