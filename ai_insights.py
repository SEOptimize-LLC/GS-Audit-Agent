"""
AI-Powered Insights Generation Module
Integrates with OpenAI, Anthropic, and Google AI to generate insights
"""

import streamlit as st
import json
from typing import Dict, List, Optional, Tuple
import openai
import anthropic
import google.generativeai as genai

from config import (
    OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_AI_API_KEY,
    AI_MODELS, INSIGHT_PROMPTS
)


class AIInsightsGenerator:
    """Generates insights using various AI providers"""
    
    def __init__(self, provider: str = 'openai', model: Optional[str] = None):
        self.provider = provider
        self.model = model or AI_MODELS[provider]['default']
        self.client = None
        
        # Initialize the appropriate client
        if provider == 'openai' and OPENAI_API_KEY:
            openai.api_key = OPENAI_API_KEY
            self.client = openai
        elif provider == 'anthropic' and ANTHROPIC_API_KEY:
            self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        elif provider == 'google' and GOOGLE_AI_API_KEY:
            genai.configure(api_key=GOOGLE_AI_API_KEY)
            self.client = genai.GenerativeModel(self.model)
        else:
            st.error(f"No API key configured for {provider}")
    
    def generate_insight(self, prompt: str, data: Dict) -> str:
        """
        Generate an insight based on prompt and data
        
        Args:
            prompt: The prompt template
            data: Data to analyze
            
        Returns:
            Generated insight text
        """
        if not self.client:
            return "AI insights unavailable - no API key configured"
        
        # Format the prompt with data
        formatted_prompt = prompt.format(data=json.dumps(data, indent=2))
        
        try:
            if self.provider == 'openai':
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are an expert SEO analyst providing actionable insights based on Google Search Console data. Be specific, data-driven, and focus on business impact."
                        },
                        {"role": "user", "content": formatted_prompt}
                    ],
                    max_tokens=AI_MODELS['openai']['max_tokens'],
                    temperature=AI_MODELS['openai']['temperature']
                )
                return response.choices[0].message.content
                
            elif self.provider == 'anthropic':
                response = self.client.messages.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": formatted_prompt}
                    ],
                    max_tokens=AI_MODELS['anthropic']['max_tokens'],
                    temperature=AI_MODELS['anthropic']['temperature'],
                    system="You are an expert SEO analyst providing actionable insights based on Google Search Console data. Be specific, data-driven, and focus on business impact."
                )
                return response.content[0].text
                
            elif self.provider == 'google':
                response = self.client.generate_content(formatted_prompt)
                return response.text
                
        except Exception as e:
            return f"Error generating insight: {str(e)}"
    
    def generate_executive_summary(self, analysis_results: Dict) -> str:
        """
        Generate an executive summary of the audit
        
        Args:
            analysis_results: Complete analysis results
            
        Returns:
            Executive summary text
        """
        summary_data = {
            'total_clicks': sum(analysis_results.get('search_analytics', {}).get('pages', {}).get('clicks', [])),
            'total_impressions': sum(analysis_results.get('search_analytics', {}).get('pages', {}).get('impressions', [])),
            'cannibalization_count': len(analysis_results.get('cannibalization', [])),
            'opportunity_count': len(analysis_results.get('opportunities', {}).get('striking_distance', [])),
            'quality_issues': analysis_results.get('content_quality', {}).get('summary', {}),
            'technical_issues': len(analysis_results.get('technical', {}).get('indexing_issues', [])),
            'trend': analysis_results.get('trends', {}).get('overall_trend', 'stable')
        }
        
        prompt = """
        Based on this Google Search Console audit data, provide a concise executive summary (3-4 paragraphs) that:
        1. Summarizes the overall health and performance of the website
        2. Highlights the most critical issues that need immediate attention
        3. Identifies the biggest opportunities for growth
        4. Provides a clear action priority
        
        Data: {data}
        
        Format the response in a professional, client-friendly manner with specific numbers and percentages.
        """
        
        return self.generate_insight(prompt, summary_data)
    
    def generate_cannibalization_insights(self, cannibalization_data: List[Dict]) -> List[Dict]:
        """
        Generate insights for keyword cannibalization issues
        
        Args:
            cannibalization_data: List of cannibalization cases
            
        Returns:
            List of insights with recommendations
        """
        insights = []
        
        # Analyze top 5 cannibalization cases
        for case in cannibalization_data[:5]:
            insight = self.generate_insight(
                INSIGHT_PROMPTS['cannibalization'],
                case
            )
            
            insights.append({
                'query': case['query'],
                'severity': case['priority'],
                'insight': insight,
                'data': case
            })
        
        return insights
    
    def generate_opportunity_insights(self, opportunities: Dict) -> Dict:
        """
        Generate insights for opportunities
        
        Args:
            opportunities: Dictionary of opportunity types
            
        Returns:
            Dictionary of insights by opportunity type
        """
        insights = {}
        
        # Striking distance keywords
        if opportunities.get('striking_distance'):
            insights['striking_distance'] = self.generate_insight(
                INSIGHT_PROMPTS['opportunities'],
                {
                    'type': 'striking_distance',
                    'opportunities': opportunities['striking_distance'][:10],
                    'total_count': len(opportunities['striking_distance']),
                    'total_potential_clicks': sum(opp['click_increase'] for opp in opportunities['striking_distance'])
                }
            )
        
        # Featured snippet opportunities
        if opportunities.get('featured_snippet_opportunities'):
            prompt = """
            Analyze these featured snippet opportunities and provide:
            1. Which queries are most likely to earn featured snippets
            2. Specific content optimization tactics for each
            3. Expected traffic increase from capturing these snippets
            
            Data: {data}
            """
            
            insights['featured_snippets'] = self.generate_insight(
                prompt,
                opportunities['featured_snippet_opportunities'][:5]
            )
        
        return insights
    
    def generate_technical_recommendations(self, technical_issues: Dict) -> str:
        """
        Generate technical SEO recommendations
        
        Args:
            technical_issues: Dictionary of technical issues
            
        Returns:
            Technical recommendations text
        """
        prompt = """
        Based on these technical SEO issues, provide:
        1. A prioritized list of technical fixes
        2. The impact of each issue on search performance
        3. Step-by-step resolution guidance for the top 3 issues
        4. Estimated effort and timeline for fixes
        
        Technical issues data: {data}
        
        Be specific and actionable, assuming the reader has basic technical knowledge.
        """
        
        return self.generate_insight(prompt, technical_issues)
    
    def generate_action_plan(self, full_analysis: Dict) -> Dict:
        """
        Generate a comprehensive action plan
        
        Args:
            full_analysis: Complete analysis results
            
        Returns:
            Structured action plan
        """
        # Summarize key findings for the AI
        summary = {
            'critical_issues': {
                'cannibalization': len(full_analysis.get('cannibalization', [])),
                'technical_errors': len(full_analysis.get('technical', {}).get('indexing_issues', [])),
                'quality_issues': full_analysis.get('content_quality', {}).get('summary', {})
            },
            'opportunities': {
                'striking_distance': len(full_analysis.get('opportunities', {}).get('striking_distance', [])),
                'quick_wins': len(full_analysis.get('opportunities', {}).get('quick_wins', [])),
                'content_gaps': len(full_analysis.get('opportunities', {}).get('content_gaps', []))
            },
            'performance': full_analysis.get('trends', {})
        }
        
        prompt = """
        Create a detailed 90-day action plan based on this SEO audit data:
        
        {data}
        
        Structure the plan as:
        
        Week 1-2 (Immediate Actions):
        - List 3-5 high-impact, low-effort fixes
        - Include specific pages/queries to target
        - Estimate hours needed
        
        Week 3-4 (Quick Wins):
        - List optimization tasks that can show results quickly
        - Focus on striking distance keywords and CTR improvements
        
        Month 2 (Strategic Improvements):
        - Content consolidation and cannibalization fixes
        - Technical SEO improvements
        - Content quality enhancements
        
        Month 3 (Growth Initiatives):
        - New content opportunities
        - Link building priorities
        - Advanced optimizations
        
        For each item, include:
        - Specific action to take
        - Expected impact (with numbers where possible)
        - Resources needed
        - Success metrics
        """
        
        action_plan_text = self.generate_insight(prompt, summary)
        
        return {
            'full_plan': action_plan_text,
            'summary': summary
        }
    
    def generate_insight_for_pattern(self, pattern_type: str, data: Dict) -> str:
        """
        Generate insights for specific patterns detected
        
        Args:
            pattern_type: Type of pattern (e.g., 'mobile_gap', 'content_decay')
            data: Pattern data
            
        Returns:
            Insight text
        """
        pattern_prompts = {
            'mobile_gap': """
            Analyze this mobile vs desktop performance gap:
            {data}
            
            Provide:
            1. Root cause analysis of why mobile is underperforming
            2. Specific technical fixes needed
            3. Expected impact of fixing the gap
            4. Priority level based on mobile traffic share
            """,
            
            'content_decay': """
            Analyze these pages with declining performance:
            {data}
            
            Provide:
            1. Common patterns among declining pages
            2. Likely causes of the decline
            3. Refresh strategy for each page type
            4. Whether to update, consolidate, or remove
            """,
            
            'quality_signals': """
            Analyze these content quality signals from Google:
            {data}
            
            Provide:
            1. What Google's behavior indicates about content quality
            2. Specific improvements needed for different page types
            3. Priority order for content improvements
            4. Expected impact on overall domain authority
            """
        }
        
        prompt = pattern_prompts.get(pattern_type, INSIGHT_PROMPTS.get('opportunities'))
        return self.generate_insight(prompt, data)


def get_ai_provider_selector() -> Tuple[str, str]:
    """
    Streamlit UI component for selecting AI provider and model
    
    Returns:
        Tuple of (provider, model)
    """
    st.sidebar.subheader("🤖 AI Settings")
    
    # Check which providers have API keys
    available_providers = []
    if OPENAI_API_KEY:
        available_providers.append("OpenAI")
    if ANTHROPIC_API_KEY:
        available_providers.append("Anthropic")
    if GOOGLE_AI_API_KEY:
        available_providers.append("Google")
    
    if not available_providers:
        st.sidebar.warning("No AI API keys configured. Add keys in .env file.")
        return None, None
    
    # Provider selection
    provider_map = {
        "OpenAI": "openai",
        "Anthropic": "anthropic",
        "Google": "google"
    }
    
    selected_provider_name = st.sidebar.selectbox(
        "Select AI Provider",
        available_providers,
        help="Choose which AI provider to use for generating insights"
    )
    
    selected_provider = provider_map[selected_provider_name]
    
    # Model selection
    available_models = AI_MODELS[selected_provider]['models']
    selected_model = st.sidebar.selectbox(
        "Select Model",
        available_models,
        index=available_models.index(AI_MODELS[selected_provider]['default']),
        help="Choose the specific model to use"
    )
    
    return selected_provider, selected_model


def generate_all_insights(analysis_results: Dict, provider: str, model: str) -> Dict:
    """
    Generate all insights for the audit
    
    Args:
        analysis_results: Complete analysis results
        provider: AI provider to use
        model: Specific model to use
        
    Returns:
        Dictionary of all generated insights
    """
    if not provider or not model:
        return {'error': 'No AI provider configured'}
    
    generator = AIInsightsGenerator(provider, model)
    insights = {}
    
    with st.spinner("Generating executive summary..."):
        insights['executive_summary'] = generator.generate_executive_summary(analysis_results)
    
    with st.spinner("Analyzing keyword cannibalization..."):
        if analysis_results.get('cannibalization'):
            insights['cannibalization'] = generator.generate_cannibalization_insights(
                analysis_results['cannibalization']
            )
    
    with st.spinner("Identifying opportunities..."):
        if analysis_results.get('opportunities'):
            insights['opportunities'] = generator.generate_opportunity_insights(
                analysis_results['opportunities']
            )
    
    with st.spinner("Generating technical recommendations..."):
        if analysis_results.get('technical'):
            insights['technical'] = generator.generate_technical_recommendations(
                analysis_results['technical']
            )
    
    with st.spinner("Creating action plan..."):
        insights['action_plan'] = generator.generate_action_plan(analysis_results)
    
    # Pattern-specific insights
    patterns_to_analyze = []
    
    if analysis_results.get('device_comparison', {}).get('problematic_pages'):
        patterns_to_analyze.append(('mobile_gap', {
            'pages': analysis_results['device_comparison']['problematic_pages'][:5],
            'summary': analysis_results['device_comparison']['device_summary']
        }))
    
    if analysis_results.get('content_quality', {}).get('declining_pages'):
        patterns_to_analyze.append(('content_decay', {
            'pages': analysis_results['content_quality']['declining_pages'][:10]
        }))
    
    if analysis_results.get('content_quality', {}).get('summary'):
        patterns_to_analyze.append(('quality_signals', 
            analysis_results['content_quality']['summary']
        ))
    
    insights['patterns'] = {}
    for pattern_type, pattern_data in patterns_to_analyze:
        with st.spinner(f"Analyzing {pattern_type} pattern..."):
            insights['patterns'][pattern_type] = generator.generate_insight_for_pattern(
                pattern_type, pattern_data
            )
    
    return insights