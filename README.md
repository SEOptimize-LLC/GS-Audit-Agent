# GSC Audit Tool - Comprehensive SEO Analysis Platform

A powerful Streamlit-based application that performs comprehensive Google Search Console audits with AI-powered insights. This tool analyzes your website's search performance, identifies issues and opportunities, and provides actionable recommendations.

## 🚀 Features

- **Comprehensive Data Collection**: Pulls all available data from Google Search Console API
- **Advanced Pattern Detection**: Identifies keyword cannibalization, content quality issues, and opportunities
- **AI-Powered Insights**: Generates actionable recommendations using OpenAI, Anthropic, or Google AI
- **Interactive Visualizations**: Beautiful charts and graphs for easy data interpretation
- **Core Web Vitals Analysis**: Integrates with PageSpeed Insights API
- **Export Capabilities**: Download reports in Excel format
- **90-Day Action Plan**: AI-generated roadmap for SEO improvements

## 📋 Prerequisites

- Python 3.9 or higher
- Google Search Console property access
- At least one AI provider API key (OpenAI, Anthropic, or Google AI)
- Google Cloud project with Search Console API enabled

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/gsc-audit-tool.git
cd gsc-audit-tool
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
- At least one AI provider key (OpenAI, Anthropic, or Google AI)
- (Optional) PageSpeed Insights API key
- (Optional) OAuth credentials if not using Service Account

### 5. Google Cloud Setup

#### Option A: Service Account (Recommended)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable the Google Search Console API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Search Console API"
   - Click "Enable"
4. Create Service Account:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in details and create
   - Click on the created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create New Key" > "JSON"
   - Download the JSON file
5. Add Service Account to GSC:
   - Go to [Google Search Console](https://search.google.com/search-console)
   - Select your property
   - Go to Settings > Users and permissions
   - Click "Add user"
   - Add the service account email (found in JSON file)
   - Give "Full" or "Restricted" permission

#### Option B: OAuth 2.0

1. In Google Cloud Console, create OAuth 2.0 credentials
2. Add authorized redirect URI: `http://localhost:8501`
3. Download credentials and add to `.env`

## 🚀 Running the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## 📖 Usage Guide

### 1. Authentication

- **Service Account**: Upload your JSON key file in the sidebar
- **OAuth**: Follow the authentication flow

### 2. Configure Audit

- Select your Search Console property
- Choose date range (30 days to 16 months)
- Select AI provider and model
- Click "Run Comprehensive Audit"

### 3. Review Results

The audit provides multiple sections:

- **Executive Summary**: AI-generated overview of findings
- **Performance**: Traffic trends and top content
- **Indexing**: Coverage status and issues
- **Opportunities**: Keywords to target for quick wins
- **Issues**: Cannibalization and quality problems
- **Technical**: Core Web Vitals and mobile/desktop gaps
- **Action Plan**: Prioritized 90-day roadmap

### 4. Export Results

- Download Excel report with all raw data
- PDF export (coming soon)

## 📁 Project Structure

```
gsc-audit-tool/
├── app.py                 # Main Streamlit application
├── config.py             # Configuration and constants
├── auth.py               # Authentication handling
├── data_collector.py     # GSC and PageSpeed API integration
├── analyzer.py           # Data analysis and pattern detection
├── ai_insights.py        # AI-powered insights generation
├── visualizations.py     # Chart and graph creation
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## 🔧 Configuration

### Adjusting Analysis Thresholds

Edit `config.py` to customize:

- Cannibalization detection sensitivity
- Content quality thresholds
- Performance decline percentages
- Striking distance ranges

### AI Model Selection

The tool supports multiple models from each provider:

**OpenAI**: GPT-4 Turbo, GPT-4, GPT-3.5 Turbo
**Anthropic**: Claude 3 Opus, Sonnet, Haiku
**Google**: Gemini Pro

## 🐛 Troubleshooting

### Common Issues

1. **"No data available"**
   - Verify Search Console property access
   - Check date range (GSC data has 3-day delay)
   - Ensure property has sufficient data

2. **Authentication errors**
   - Verify service account has GSC access
   - Check API is enabled in Google Cloud
   - Ensure JSON key file is valid

3. **Rate limit errors**
   - Tool implements automatic retry logic
   - Consider using service account for higher limits
   - Add PageSpeed API key for better CWV limits

4. **AI insights not generating**
   - Verify API key is correct
   - Check API credit balance
   - Try different AI model

### Debug Mode

Set in Streamlit:
```bash
streamlit run app.py --logger.level=debug
```

## 📊 API Limits

- **GSC API**: 1,200 requests/minute, 50,000/day
- **URL Inspection**: 2,000/day, 600/minute
- **PageSpeed**: 25,000/day with key, 1/sec without

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Google Search Console API documentation
- Streamlit for the amazing framework
- OpenAI, Anthropic, and Google for AI capabilities

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Refer to API documentation for specific errors

---

**Note**: This tool is not affiliated with Google. Use responsibly and in accordance with Google's Terms of Service.