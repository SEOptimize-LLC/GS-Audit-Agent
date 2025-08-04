"""
GSC Audit Tool - Main Streamlit Application
Comprehensive Google Search Console audit with AI-powered insights
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import base64
from io import BytesIO
import validators

# Import all modules
from config import (
    DEFAULT_DATE_RANGE, MAX_DATE_RANGE, DATA_FRESHNESS_DELAY,
    ERROR_MESSAGES, SUCCESS_MESSAGES, REPORT_SECTIONS
)
from auth import handle_authentication, GSCAuthenticator
from data_collector import collect_all_data
from analyzer import GSCAnalyzer
from ai_insights import get_ai_provider_selector, generate_all_insights
from visualizations import create_audit_visualizations

# Page configuration
st.set_page_config(
    page_title="GSC Audit Tool - Comprehensive SEO Analysis",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding-top: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
        background-color: #f0f2f6;
        border-radius: 5px 5px 0px 0px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f77b4;
        color: white;
    }
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #cccccc;
        padding: 5px 15px;
        border-radius: 5px;
        margin: 5px 0;
    }
    </style>
    """, unsafe_allow_html=True)


def main():
    """Main application function"""
    
    # Initialize session state
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 'authentication'
    
    # Sidebar
    with st.sidebar:
        st.title("🔍 GSC Audit Tool")
        st.markdown("---")
        
        # Authentication
        authenticated = handle_authentication()
        
        if authenticated:
            st.markdown("---")
            
            # Property selection
            st.subheader("📊 Audit Configuration")
            
            authenticator = GSCAuthenticator()
            properties = authenticator.list_properties()
            
            if properties:
                selected_property = st.selectbox(
                    "Select Property",
                    properties,
                    help="Choose the Search Console property to audit"
                )
                
                # Date range selection
                date_option = st.radio(
                    "Date Range",
                    ["Last 30 days", "Last 90 days", "Last 6 months", "Last 12 months", "Custom"]
                )
                
                if date_option == "Custom":
                    col1, col2 = st.columns(2)
                    with col1:
                        start_date = st.date_input(
                            "Start Date",
                            datetime.now() - timedelta(days=90)
                        )
                    with col2:
                        end_date = st.date_input(
                            "End Date",
                            datetime.now() - timedelta(days=DATA_FRESHNESS_DELAY)
                        )
                    days = (end_date - start_date).days
                else:
                    days_map = {
                        "Last 30 days": 30,
                        "Last 90 days": 90,
                        "Last 6 months": 180,
                        "Last 12 months": 365
                    }
                    days = days_map[date_option]
                
                # AI provider selection
                st.markdown("---")
                ai_provider, ai_model = get_ai_provider_selector()
                
                # Run audit button
                st.markdown("---")
                if st.button("🚀 Run Comprehensive Audit", type="primary", use_container_width=True):
                    if selected_property:
                        st.session_state.current_step = 'collecting'
                        st.session_state.property_url = selected_property
                        st.session_state.date_range_days = days
                        st.session_state.ai_provider = ai_provider
                        st.session_state.ai_model = ai_model
                        st.rerun()
                    else:
                        st.error("Please select a property")
                        
            else:
                st.warning("No Search Console properties found. Please ensure you have access to at least one property.")
    
    # Main area
    if not authenticated:
        show_welcome_screen()
    else:
        if st.session_state.current_step == 'authentication':
            show_welcome_screen()
        elif st.session_state.current_step == 'collecting':
            collect_and_analyze_data()
        elif st.session_state.current_step == 'complete':
            show_audit_report()


def show_welcome_screen():
    """Show welcome screen with instructions"""
    st.title("Welcome to GSC Audit Tool")
    st.markdown("""
    ### 🎯 Comprehensive Google Search Console Audit with AI-Powered Insights
    
    This tool provides a complete SEO audit of your website using data from Google Search Console, including:
    
    - **🔍 Search Performance Analysis**: Identify trends, opportunities, and issues
    - **🕷️ Indexing & Crawlability**: Ensure Google can properly access your content
    - **📱 Mobile vs Desktop**: Compare performance across devices
    - **⚡ Core Web Vitals**: Analyze page experience metrics
    - **🎯 Keyword Opportunities**: Find quick wins and growth potential
    - **🤖 AI-Powered Insights**: Get actionable recommendations from leading AI models
    
    ### Getting Started
    
    1. **Authenticate** with Google Search Console (see sidebar)
    2. **Select** your website property
    3. **Choose** your date range and AI provider
    4. **Run** the comprehensive audit
    5. **Review** your detailed report with actionable insights
    
    ### Requirements
    
    - Access to a Google Search Console property
    - Service Account JSON key (recommended) or OAuth credentials
    - API keys for AI insights (OpenAI, Anthropic, or Google AI)
    """)


def collect_and_analyze_data():
    """Collect data and run analysis"""
    st.title(f"Analyzing {st.session_state.property_url}")
    
    progress_container = st.container()
    
    with progress_container:
        st.info("Running comprehensive audit... This may take a few minutes.")
        
        # Step 1: Collect data
        with st.spinner("Collecting data from Google Search Console..."):
            data = collect_all_data(
                st.session_state.property_url,
                st.session_state.date_range_days
            )
        
        if not data or 'search_analytics' not in data:
            st.error("Failed to collect data. Please check your permissions and try again.")
            st.session_state.current_step = 'authentication'
            return
        
        st.success(SUCCESS_MESSAGES['data_loaded'])
        
        # Step 2: Run analysis
        with st.spinner("Analyzing data patterns..."):
            analyzer = GSCAnalyzer(data)
            analysis_results = analyzer.run_full_analysis()
            st.session_state.analysis_results = analysis_results
        
        st.success(SUCCESS_MESSAGES['analysis_complete'])
        
        # Step 3: Generate visualizations
        with st.spinner("Creating visualizations..."):
            charts = create_audit_visualizations(data, analysis_results)
            st.session_state.charts = charts
        
        # Step 4: Generate AI insights
        if st.session_state.get('ai_provider') and st.session_state.get('ai_model'):
            with st.spinner("Generating AI-powered insights..."):
                insights = generate_all_insights(
                    analysis_results,
                    st.session_state.ai_provider,
                    st.session_state.ai_model
                )
                st.session_state.ai_insights = insights
        else:
            st.warning("No AI provider configured. Insights will be limited.")
            st.session_state.ai_insights = {}
        
        st.success(SUCCESS_MESSAGES['report_generated'])
        
        # Update state
        st.session_state.current_step = 'complete'
        st.rerun()


def show_audit_report():
    """Display the complete audit report"""
    st.title(f"GSC Audit Report: {st.session_state.property_url}")
    st.caption(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Get data from session state
    data = st.session_state.get('gsc_data', {})
    analysis_results = st.session_state.get('analysis_results', {})
    charts = st.session_state.get('charts', {})
    ai_insights = st.session_state.get('ai_insights', {})
    
    # Executive Summary
    if ai_insights.get('executive_summary'):
        st.header("📋 Executive Summary")
        st.markdown(ai_insights['executive_summary'])
        st.markdown("---")
    
    # Key Metrics
    show_key_metrics(data, analysis_results)
    
    # Create tabs for different sections
    tabs = st.tabs([
        "📊 Performance",
        "🔍 Indexing",
        "🎯 Opportunities",
        "⚠️ Issues",
        "📱 Technical",
        "📈 Visualizations",
        "💡 AI Insights",
        "📋 Action Plan"
    ])
    
    with tabs[0]:
        show_performance_section(data, analysis_results, charts, ai_insights)
    
    with tabs[1]:
        show_indexing_section(data, analysis_results, ai_insights)
    
    with tabs[2]:
        show_opportunities_section(analysis_results, charts, ai_insights)
    
    with tabs[3]:
        show_issues_section(analysis_results, ai_insights)
    
    with tabs[4]:
        show_technical_section(data, analysis_results, charts, ai_insights)
    
    with tabs[5]:
        show_all_visualizations(charts)
    
    with tabs[6]:
        show_all_ai_insights(ai_insights)
    
    with tabs[7]:
        show_action_plan(ai_insights)
    
    # Export options
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 Export Report (PDF)", use_container_width=True):
            st.info("PDF export coming soon!")
    
    with col2:
        if st.button("📊 Export Data (Excel)", use_container_width=True):
            export_to_excel(data, analysis_results)
    
    with col3:
        if st.button("🔄 Run New Audit", use_container_width=True):
            st.session_state.current_step = 'authentication'
            st.rerun()


def show_key_metrics(data: dict, analysis_results: dict):
    """Display key metrics dashboard"""
    st.header("🎯 Key Metrics")
    
    # Calculate metrics
    search_data = data.get('search_analytics', {})
    
    total_clicks = 0
    total_impressions = 0
    
    if 'pages' in search_data and not search_data['pages'].empty:
        total_clicks = search_data['pages']['clicks'].sum()
        total_impressions = search_data['pages']['impressions'].sum()
    
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Clicks",
            f"{total_clicks:,}",
            help="Total clicks from Google Search"
        )
    
    with col2:
        st.metric(
            "Total Impressions",
            f"{total_impressions:,}",
            help="Total times your site appeared in search"
        )
    
    with col3:
        st.metric(
            "Average CTR",
            f"{avg_ctr:.2f}%",
            help="Click-through rate"
        )
    
    with col4:
        quality_score = analysis_results.get('content_quality', {}).get('summary', {}).get('quality_score', 0)
        st.metric(
            "Content Quality Score",
            f"{quality_score:.0f}/100",
            help="Overall content quality based on Google signals"
        )
    
    # Additional metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        cannibalization_count = len(analysis_results.get('cannibalization', []))
        st.metric(
            "Cannibalization Issues",
            cannibalization_count,
            help="Keywords with multiple competing pages"
        )
    
    with col2:
        opportunity_count = len(analysis_results.get('opportunities', {}).get('striking_distance', []))
        st.metric(
            "Quick Win Keywords",
            opportunity_count,
            help="Keywords ranking 11-20"
        )
    
    with col3:
        technical_issues = len(analysis_results.get('technical', {}).get('indexing_issues', []))
        st.metric(
            "Technical Issues",
            technical_issues,
            help="Indexing and crawl issues"
        )
    
    with col4:
        cwv_status = analysis_results.get('cwv', {}).get('overall_status', 'unknown')
        status_emoji = {'good': '✅', 'needs_improvement': '⚠️', 'poor': '❌', 'unknown': '❓'}
        st.metric(
            "Core Web Vitals",
            status_emoji.get(cwv_status, '❓') + ' ' + cwv_status.replace('_', ' ').title(),
            help="Overall Core Web Vitals status"
        )


def show_performance_section(data, analysis_results, charts, ai_insights):
    """Show performance analysis section"""
    st.header("Search Performance Analysis")
    
    # Performance chart
    if 'performance_overview' in charts:
        st.plotly_chart(charts['performance_overview'], use_container_width=True)
    
    # Trend analysis
    trends = analysis_results.get('trends', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Performance Trend")
        trend = trends.get('overall_trend', 'stable')
        growth_rate = trends.get('growth_rate', 0)
        
        if trend == 'growing':
            st.success(f"📈 Growing: +{growth_rate:.1f}% over last 30 days")
        elif trend == 'declining':
            st.error(f"📉 Declining: {growth_rate:.1f}% over last 30 days")
        else:
            st.info(f"➡️ Stable: {growth_rate:+.1f}% change over last 30 days")
    
    with col2:
        st.subheader("Traffic Volatility")
        volatility = trends.get('volatility', 'low')
        
        if volatility == 'high':
            st.warning("⚠️ High volatility detected - investigate causes")
        elif volatility == 'medium':
            st.info("📊 Moderate volatility - monitor closely")
        else:
            st.success("✅ Low volatility - stable traffic patterns")
    
    # Top performing content
    if 'pages' in data.get('search_analytics', {}):
        st.subheader("Top Performing Pages")
        
        pages_df = data['search_analytics']['pages'].copy()
        pages_df['ctr'] = (pages_df['clicks'] / pages_df['impressions'] * 100).round(2)
        
        top_pages = pages_df.nlargest(10, 'clicks')[['page', 'clicks', 'impressions', 'ctr', 'position']]
        top_pages.columns = ['Page', 'Clicks', 'Impressions', 'CTR %', 'Avg Position']
        
        st.dataframe(
            top_pages,
            use_container_width=True,
            hide_index=True
        )


def show_indexing_section(data, analysis_results, ai_insights):
    """Show indexing analysis section"""
    st.header("Indexing & Crawlability")
    
    # Index coverage
    if 'index_coverage' in data and not data['index_coverage'].empty:
        st.subheader("Index Coverage Status")
        
        coverage_df = data['index_coverage']
        
        # Create bar chart
        import plotly.express as px
        fig = px.bar(
            coverage_df,
            x='Status',
            y='Count',
            color='Status',
            title='Page Indexing Status Distribution'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Indexing issues
    indexing_issues = analysis_results.get('technical', {}).get('indexing_issues', [])
    
    if indexing_issues:
        st.subheader("⚠️ Indexing Issues Found")
        
        for issue in indexing_issues:
            severity_color = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
            st.write(f"{severity_color.get(issue['severity'], '⚪')} **{issue['issue']}**: {issue['affected_urls']} URLs affected")
    else:
        st.success("✅ No critical indexing issues found")
    
    # AI recommendations
    if ai_insights.get('technical'):
        st.subheader("🤖 AI Recommendations")
        st.markdown(ai_insights['technical'])


def show_opportunities_section(analysis_results, charts, ai_insights):
    """Show opportunities section"""
    st.header("Growth Opportunities")
    
    opportunities = analysis_results.get('opportunities', {})
    
    # Striking distance keywords
    if opportunities.get('striking_distance'):
        st.subheader("🎯 Striking Distance Keywords (Position 11-20)")
        
        if 'opportunities' in charts:
            st.plotly_chart(charts['opportunities'], use_container_width=True)
        
        # Table of top opportunities
        striking_df = pd.DataFrame(opportunities['striking_distance'][:10])
        striking_df['potential_clicks'] = striking_df['potential_clicks'].round(0).astype(int)
        striking_df['click_increase'] = striking_df['click_increase'].round(0).astype(int)
        
        st.dataframe(
            striking_df[['query', 'position', 'impressions', 'clicks', 'potential_clicks', 'click_increase']],
            use_container_width=True,
            hide_index=True
        )
    
    # Featured snippet opportunities
    if opportunities.get('featured_snippet_opportunities'):
        st.subheader("💡 Featured Snippet Opportunities")
        
        snippet_df = pd.DataFrame(opportunities['featured_snippet_opportunities'])
        st.dataframe(snippet_df, use_container_width=True, hide_index=True)
    
    # AI insights
    if ai_insights.get('opportunities'):
        st.subheader("🤖 AI-Powered Opportunity Analysis")
        
        for key, insight in ai_insights['opportunities'].items():
            st.markdown(f"### {key.replace('_', ' ').title()}")
            st.markdown(insight)


def show_issues_section(analysis_results, ai_insights):
    """Show issues section"""
    st.header("Issues & Warnings")
    
    # Keyword cannibalization
    cannibalization = analysis_results.get('cannibalization', [])
    
    if cannibalization:
        st.subheader("🔄 Keyword Cannibalization")
        
        if 'cannibalization' in st.session_state.get('charts', {}):
            st.plotly_chart(st.session_state.charts['cannibalization'], use_container_width=True)
        
        # Details for top cases
        if ai_insights.get('cannibalization'):
            for case_insight in ai_insights['cannibalization'][:3]:
                with st.expander(f"📍 {case_insight['query']}"):
                    st.markdown(case_insight['insight'])
    
    # Content quality issues
    quality_issues = analysis_results.get('content_quality', {})
    
    if quality_issues.get('low_ctr_pages'):
        st.subheader("📉 Low CTR Pages")
        st.write(f"Found {len(quality_issues['low_ctr_pages'])} pages with CTR below 2% despite high impressions")
        
        with st.expander("View affected pages"):
            low_ctr_df = pd.DataFrame(quality_issues['low_ctr_pages'][:10])
            low_ctr_df['ctr'] = (low_ctr_df['ctr'] * 100).round(2)
            st.dataframe(low_ctr_df, use_container_width=True, hide_index=True)


def show_technical_section(data, analysis_results, charts, ai_insights):
    """Show technical SEO section"""
    st.header("Technical SEO Analysis")
    
    # Core Web Vitals
    if 'cwv_summary' in charts:
        st.subheader("⚡ Core Web Vitals")
        st.plotly_chart(charts['cwv_summary'], use_container_width=True)
    
    # Mobile vs Desktop
    if 'device_comparison' in charts:
        st.subheader("📱 Mobile vs Desktop Performance")
        st.plotly_chart(charts['device_comparison'], use_container_width=True)
    
    # Problematic pages
    device_comparison = analysis_results.get('device_comparison', {})
    if device_comparison.get('problematic_pages'):
        st.subheader("⚠️ Pages with Mobile/Desktop Gap")
        
        problematic_df = pd.DataFrame(device_comparison['problematic_pages'][:5])
        st.dataframe(problematic_df, use_container_width=True, hide_index=True)
    
    # Sitemap status
    if 'sitemaps' in data and not data['sitemaps'].empty:
        st.subheader("🗺️ Sitemap Status")
        
        sitemaps_df = data['sitemaps'][['path', 'lastSubmitted', 'isPending', 'isSitemapsIndex']].copy()
        st.dataframe(sitemaps_df, use_container_width=True, hide_index=True)


def show_all_visualizations(charts):
    """Show all visualizations in one place"""
    st.header("All Visualizations")
    
    for chart_name, chart in charts.items():
        st.subheader(chart_name.replace('_', ' ').title())
        st.plotly_chart(chart, use_container_width=True)


def show_all_ai_insights(ai_insights):
    """Show all AI insights"""
    st.header("AI-Generated Insights")
    
    if not ai_insights:
        st.warning("No AI insights available. Configure an AI provider to enable this feature.")
        return
    
    # Pattern insights
    if ai_insights.get('patterns'):
        for pattern_type, insight in ai_insights['patterns'].items():
            st.subheader(f"Pattern Analysis: {pattern_type.replace('_', ' ').title()}")
            st.markdown(insight)
            st.markdown("---")
    
    # Other insights
    for section in ['executive_summary', 'technical', 'opportunities']:
        if section in ai_insights and isinstance(ai_insights[section], str):
            st.subheader(section.replace('_', ' ').title())
            st.markdown(ai_insights[section])
            st.markdown("---")


def show_action_plan(ai_insights):
    """Show the action plan section"""
    st.header("📋 90-Day Action Plan")
    
    if ai_insights.get('action_plan'):
        action_plan = ai_insights['action_plan']
        
        if isinstance(action_plan, dict) and 'full_plan' in action_plan:
            st.markdown(action_plan['full_plan'])
        else:
            st.markdown(action_plan)
    else:
        st.info("Configure an AI provider to generate a customized action plan based on your audit results.")


def export_to_excel(data, analysis_results):
    """Export audit data to Excel"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Search analytics data
        if 'search_analytics' in data:
            for key, df in data['search_analytics'].items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    df.to_excel(writer, sheet_name=f"search_{key}", index=False)
        
        # Analysis results
        if analysis_results.get('cannibalization'):
            cannibal_df = pd.DataFrame(analysis_results['cannibalization'])
            cannibal_df.to_excel(writer, sheet_name='cannibalization', index=False)
        
        if analysis_results.get('opportunities', {}).get('striking_distance'):
            striking_df = pd.DataFrame(analysis_results['opportunities']['striking_distance'])
            striking_df.to_excel(writer, sheet_name='opportunities', index=False)
    
    output.seek(0)
    
    st.download_button(
        label="📥 Download Excel Report",
        data=output,
        file_name=f"gsc_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


if __name__ == "__main__":
    main()