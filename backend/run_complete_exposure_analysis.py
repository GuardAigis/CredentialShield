#!/usr/bin/env python3
"""
Complete Exposure Analysis Script
Combines Katana Discovery + SecretFinder + API Exposure Classification
All intermediate files are temporary, only final output is permanent.
"""

import asyncio
import sys
import os
import tempfile
from pathlib import Path
from datetime import datetime
import uuid
import shutil

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

async def run_complete_exposure_analysis(target_url: str, max_pages: str = "x", depth: int = 2, download_after_upload: bool = False, download_path: str | None = None, keep_local_pdf: bool = False):
    """
    Run complete exposure analysis pipeline:
    1. Katana Discovery (temporary)
    2. SecretFinder Analysis (temporary)
    3. API Exposure Classification (permanent output)
    
    Args:
        target_url: The target website URL
        max_pages: Maximum pages to crawl
        depth: Maximum crawl depth
        
    Returns:
        Path to the final permanent output files
    """
    
    print("🚀 Complete Exposure Analysis Pipeline")
    print("="*50)
    print(f"Target URL: {target_url}")
    print(f"Max pages: {max_pages}, Depth: {depth}")
    print()
    
    temp_files = []  # Track temporary files for cleanup
    
    try:
        # Step 1: Run Katana Discovery
        print("📡 Step 1: Running Katana Discovery...")
        from app.services.tools.katana_tools import katana_tools
        from app.services.agents.Exposure_Discovery import run_secret_analysis, create_secret_dump
        
        # Use actual Katana for discovery
        katana_result = await katana_tools.run_katana_discovery(
            target_url=target_url,
            max_depth=depth,
            max_pages=int(max_pages) if max_pages != "x" else 200
        )
        
        if katana_result.get("status") != "success":
            print(f"❌ Katana discovery failed: {katana_result.get('error', 'Unknown error')}")
            return None
        
        # Extract JavaScript URLs from Katana results
        all_urls = katana_result.get("urls", [])
        js_files = [url for url in all_urls if url.lower().endswith('.js')]
        
        if not js_files:
            print("❌ No JavaScript files discovered")
            return None
        
        print(f"✅ Discovered {len(js_files)} JavaScript files")
        print()
        
        # Step 2: Run SecretFinder Analysis
        print("🔐 Step 2: Running SecretFinder Analysis...")
        secrets = await run_secret_analysis(js_files)
        
        if not secrets:
            print("⚠️ No secrets found in JavaScript files")
            return None
        
        print(f"✅ Found {len(secrets)} secrets")
        print()
        
        # Step 3: Create temporary secret dump
        print("📄 Step 3: Creating temporary secret dump...")
        secret_dump_path = create_secret_dump(secrets)
        
        if not secret_dump_path:
            print("❌ Failed to create secret dump")
            return None
        
        temp_files.append(secret_dump_path)
        print(f"✅ Created temporary secret dump: {secret_dump_path}")
        print()
        
        # Step 4: Run API Exposure Classification
        print("🔍 Step 4: Running API Exposure Classification...")
        
        # Generate output filenames based on domain and timestamp
        from urllib.parse import urlparse
        parsed_url = urlparse(target_url)
        domain = parsed_url.netloc.replace('.', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Debug prints removed
        
        # Write outputs directly into the current backend directory
        chosen_dir = os.getcwd()
        # Debug prints removed

        json_output = os.path.join(chosen_dir, f"{domain}_api_exposure_report_{timestamp}.json")
        md_output = os.path.join(chosen_dir, f"{domain}_api_exposure_report_{timestamp}.md")
        pdf_output = os.path.join(chosen_dir, f"{domain}_api_exposure_report_{timestamp}.pdf")
        
        # Debug prints removed
        
        try:
            from app.services.agents.Api_Exposure_classifier import main as run_classifier
            
            # Set up command line arguments for the classifier
            original_argv = sys.argv.copy()
            sys.argv = [
                'Api_Exposure_classifier.py',
                secret_dump_path,
                '--report-json', json_output,
                '--report-md', md_output,
                '--report-pdf', pdf_output
            ]
            
            # Run the classifier
            await run_classifier()
            
            # Restore original argv
            sys.argv = original_argv
            
        except Exception as classifier_error:
            print(f"⚠️ API Exposure Classifier failed: {classifier_error}")
            print("📄 Creating basic report from secrets...")
            
            # Create a basic JSON report manually
            basic_report = {
                "timestamp": datetime.now().isoformat(),
                "target_url": target_url,
                "analysis_type": "secret_exposure_analysis",
                "javascript_files_analyzed": len(js_files),
                "total_secrets_found": len(secrets),
                "js_files": js_files,
                "secrets": secrets
            }
            
            with open(json_output, 'w') as f:
                import json as json_module
                json_module.dump(basic_report, f, indent=2)
            
            # Create a basic markdown report
            with open(md_output, 'w') as f:
                f.write(f"# Secret Exposure Analysis Report\n\n")
                f.write(f"**Target URL:** {target_url}\n")
                f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**JavaScript Files Analyzed:** {len(js_files)}\n")
                f.write(f"**Total Secrets Found:** {len(secrets)}\n\n")
                
                f.write("## JavaScript Files Analyzed\n\n")
                for i, js_file in enumerate(js_files):
                    f.write(f"{i+1}. {js_file}\n")
                
                f.write("\n## Secrets Found\n\n")
                for i, secret_info in enumerate(secrets):
                    f.write(f"### Secret {i+1}\n")
                    f.write(f"**File:** {secret_info['file']}\n")
                    f.write(f"**Secret:** {secret_info['secret']}\n\n")
            
            print(f"✅ Basic reports created: {json_output}, {md_output}")
        
        print(f"✅ API Exposure Classification completed")
        print(f"📄 JSON Report: {json_output}")
        print(f"📄 Markdown Report: {md_output}")
        print(f"📄 PDF Report: {pdf_output}")

        print()
        
        # Clean up any remaining temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    # os.remove(temp_file)
                    print(f"📝 Keeping temporary file: {temp_file}")
                except Exception as e:
                    print(f"⚠️ Warning: Could not handle temp file {temp_file}: {e}")
        
        print("\n🎉 Complete exposure analysis finished successfully!")
        print(f"📁 Permanent output files:")
        print(f"   - {json_output}")
        print(f"   - {md_output}")
        print(f"   - {pdf_output}")
        
        return {
            "json_report": json_output,
            "markdown_report": md_output,
            "pdf_report": pdf_output,
            "target_url": target_url,
            "js_files_count": len(js_files),
            "secrets_count": len(secrets)
        }
        
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")
        
        # Clean up temporary files even on error
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    # os.remove(temp_file)
                    print(f"📝 Keeping temporary file (error path): {temp_file}")
                except Exception as cleanup_error:
                    print(f"⚠️ Warning: Could not handle temp file {temp_file}: {cleanup_error}")
        
        return None

async def main():
    """Main function"""
    
    if len(sys.argv) < 2:
        print("Usage: python run_complete_exposure_analysis.py <target_url> [max_pages] [depth] [--download] [--download-path <path>] [--keep-local-pdf]")
        print("Example: python run_complete_exposure_analysis.py https://example.com x 2")
        print("\nParameters:")
        print("  target_url: The website URL to analyze")
        print("  max_pages: Maximum pages to crawl (default: 'x' for unlimited)")
        print("  depth: Maximum crawl depth (default: 2)")
        print("  --download: After uploading the PDF to Firebase/GCS, download a copy locally")
        print("  --download-path <path>: Where to save the downloaded PDF (default: same name in CWD)")
        print("  --keep-local-pdf: Do not delete the original local PDF after upload")
        print("\nOutput:")
        print("  - {domain}_api_exposure_report_{timestamp}.json")
        print("  - {domain}_api_exposure_report_{timestamp}.md")
        print("  - {domain}_api_exposure_report_{timestamp}.pdf")
        sys.exit(1)
    
    target_url = sys.argv[1]
    max_pages = sys.argv[2] if len(sys.argv) > 2 else "x"
    depth = int(sys.argv[3]) if len(sys.argv) > 3 else 2

    # Flags
    download_after_upload = "--download" in sys.argv
    keep_local_pdf = "--keep-local-pdf" in sys.argv
    download_path = None
    if "--download-path" in sys.argv:
        try:
            idx = sys.argv.index("--download-path")
            download_path = sys.argv[idx + 1]
        except Exception:
            print("⚠️ --download-path provided without a following path; ignoring")
    
    result = await run_complete_exposure_analysis(
        target_url,
        max_pages,
        depth,
        download_after_upload=download_after_upload,
        download_path=download_path,
        keep_local_pdf=keep_local_pdf,
    )
    
    if result:
        print(f"\n📊 Summary:")
        print(f"   Target URL: {result['target_url']}")
        print(f"   JavaScript files: {result['js_files_count']}")
        print(f"   Secrets found: {result['secrets_count']}")
        print(f"   Reports: {result['json_report']}, {result['markdown_report']}, {result['pdf_report']}")
    else:
        print("\n❌ Analysis failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 