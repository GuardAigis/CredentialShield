# 🤖 GuardAigis - API Exposure Analysis Tool

A comprehensive security analysis tool that discovers and analyzes exposed secrets in web applications using Katana web crawler, SecretFinder, and AI-powered classification.

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** installed and running
- **Git** for cloning the repository
- **Python 3.8+** (for local development)

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd GA_Deployment

# Verify Docker is running
docker info
```

### 2. Environment Setup

```bash
# Create environment file (if not exists)
cd backend
cp .env.example .env  # or create .env manually

# Edit .env file with your OpenAI API key
# OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Run Analysis

#### Option A: Using Docker (Recommended)

```bash
# From the root directory (GA_Deployment/)
docker-compose build exposure-analysis

# Run analysis on a target website
docker-compose run --rm exposure-analysis python run_complete_exposure_analysis.py https://example.com

# With custom parameters
docker-compose run --rm exposure-analysis python run_complete_exposure_analysis.py https://example.com 100 3
# Parameters: URL, max_pages (100), depth (3)
```

#### Option B: Local Development

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run analysis locally
python run_complete_exposure_analysis.py https://example.com
```

### 4. View Results

After analysis completes, check the `backend/` directory for generated reports:

```bash
# List generated reports
ls -la backend/*_api_exposure_report_*.{json,md,pdf}

# View JSON report
cat backend/example_com_api_exposure_report_20241201_143022.json

# View Markdown report
cat backend/example_com_api_exposure_report_20241201_143022.md
```

## 📋 Complete Command Reference

### Docker Commands

```bash
# Build the Docker image
docker-compose build exposure-analysis

# Run analysis with default settings
docker-compose run --rm exposure-analysis python run_complete_exposure_analysis.py <target_url>

# Run with custom parameters
docker-compose run --rm exposure-analysis python run_complete_exposure_analysis.py <target_url> <max_pages> <depth>

# Examples:
docker-compose run --rm exposure-analysis python run_complete_exposure_analysis.py https://smartspooler.com/landing
docker-compose run --rm exposure-analysis python run_complete_exposure_analysis.py https://example.com 50 2
docker-compose run --rm exposure-analysis python run_complete_exposure_analysis.py https://test.com 200 3

# Interactive mode (for debugging)
docker-compose run --rm exposure-analysis /bin/bash

# Clean up Docker resources
docker system prune -f
docker-compose down
```

### Local Development Commands

```bash
# Install Python dependencies
cd backend
pip install -r requirements.txt

# Run analysis locally
python run_complete_exposure_analysis.py <target_url>

# Run with custom parameters
python run_complete_exposure_analysis.py <target_url> <max_pages> <depth>

# Run individual components
python -m app.services.agents.Api_Exposure_classifier <secrets_file> --target-url <url>

# Test secret verification
python -m app.services.agents.secret_verifier --evidence "curl -X GET -H 'X-TrackerToken: $TOKEN' https://api.example.com" --token "your_token_here"
```

### File Management Commands

```bash
# Clean up generated files
rm backend/*_api_exposure_report_*.{json,md,pdf}
rm -rf backend/katana_output/

# View analysis logs
docker-compose logs exposure-analysis

# Check Docker container status
docker ps -a
docker-compose ps
```

## 📊 Understanding the Output

### Generated Files

1. **JSON Report** (`*_api_exposure_report_*.json`)

   - Structured data with all findings
   - Risk classifications and scores
   - Verification results
   - Evidence data

2. **Markdown Report** (`*_api_exposure_report_*.md`)

   - Human-readable format
   - Detailed findings with descriptions
   - Remediation steps
   - Verification details

3. **PDF Report** (`*_api_exposure_report_*.pdf`)
   - Professional security report
   - GuardAigis branding
   - Severity summaries
   - Formatted evidence

### Report Structure

```json
{
  "overall_risk": "HIGH",
  "summary": {
    "total_findings": 5,
    "critical_findings": 1,
    "high_findings": 2,
    "medium_findings": 1,
    "low_findings": 1
  },
  "findings": [
    {
      "title": "API Exposure - API Key",
      "severity": "CRITICAL",
      "description": "...",
      "impact": "...",
      "remediation_steps": [...],
      "evidence": [...],
      "verification": {...}
    }
  ]
}
```

## 🔧 Troubleshooting

### Common Issues

1. **Docker not running**

   ```bash
   # Start Docker Desktop
   # Then verify:
   docker info
   ```

2. **Permission errors**

   ```bash
   # Clean Docker system
   docker system prune -f
   docker-compose build --no-cache exposure-analysis
   ```

3. **Missing OpenAI API key**

   ```bash
   # Check .env file
   cat backend/.env
   # Ensure OPENAI_API_KEY is set
   ```

4. **Analysis fails with no JavaScript files**
   ```bash
   # Try different depth/max_pages
   docker-compose run --rm exposure-analysis python run_complete_exposure_analysis.py <url> 500 4
   ```

### Debug Commands

```bash
# Check if Katana is available
docker-compose run --rm exposure-analysis which katana

# Test SecretFinder
docker-compose run --rm exposure-analysis secretfinder -h

# View container logs
docker-compose logs exposure-analysis

# Enter container for debugging
docker-compose run --rm exposure-analysis /bin/bash
```

## 🏗️ Architecture

```
GA_Deployment/
├── backend/
│   ├── app/services/
│   │   ├── agents/           # Core analysis logic
│   │   │   ├── Api_Exposure_classifier.py
│   │   │   ├── secret_verifier.py
│   │   │   └── Exposure_Discovery.py
│   │   └── tools/            # Report generation
│   │       ├── pdf_report.py
│   │       ├── md_report.py
│   │       ├── json_report.py
│   │       └── katana_tools.py
│   ├── requirements.txt
│   └── run_complete_exposure_analysis.py
├── docker-compose.yml
└── README.md
```

## 📝 Configuration

### Environment Variables

Create `backend/.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
PYTHONPATH=/app
PYTHONUNBUFFERED=1
```

### Docker Configuration

The `docker-compose.yml` mounts:

- `./backend:/app` - Source code
- `tmp_data:/tmp` - Temporary data

## 🚨 Security Notes

- **API Keys**: Never commit real API keys to version control
- **Target URLs**: Only analyze websites you own or have permission to test
- **Rate Limiting**: Be respectful of target websites' resources
- **Legal Compliance**: Ensure compliance with local laws and terms of service

## 📞 Support

- **Email**: guardaigis@gmail.com
- **Issues**: Create GitHub issues for bugs or feature requests
- **Documentation**: Check inline code comments for detailed explanations

## 🔄 Pipeline Flow

1. **Katana Discovery** → Crawls target website for JavaScript files
2. **SecretFinder Analysis** → Scans JS files for exposed secrets
3. **AI Classification** → Uses GPT-4o-mini to classify risks
4. **Verification** → Attempts to verify found secrets
5. **Report Generation** → Creates JSON, Markdown, and PDF reports

## 📈 Performance Tips

- **Small sites**: Use `max_pages=50, depth=2`
- **Large sites**: Use `max_pages=200, depth=3`
- **Deep analysis**: Use `max_pages=500, depth=4`
- **Quick scan**: Use `max_pages=20, depth=1`

---

**GuardAigis** - Your reliable partner security analysis partner in the Agentic AI Era 🤖
