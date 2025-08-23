#!/usr/bin/env python3
"""
API Exposure Classifier
"""

from datetime import datetime
import uuid
import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict
from dotenv import load_dotenv
from openai import AsyncOpenAI
import base64
from io import BytesIO
import re
from .secret_verifier import extract_commands, run_command
from ..tools.pdf_report import build_pdf_report
from ..tools.md_report import build_markdown
from ..tools.json_report import build_json_report

def classify(data: dict) -> dict:
    """Deprecated wrapper retained for compatibility (unused in reference flow)."""
    return {"findings": [], "overall_risk": "INFO", "summary": {}}

def parse_secret_file(path: Path) -> Dict[str, List[Dict]]:
    """Build dict {secret_type: [{'evidence': str, 'filename': str, 'url': str}, …]} from lines like: key -> value"""
    secrets: Dict[str, List[Dict]] = defaultdict(list)
    current_url = "Unknown"
    
    with path.open(encoding="utf-8", errors="ignore") as fh:
        for raw in fh:
            line = raw.strip()
            
            # Check if this line contains a URL
            if line.startswith("[ + ] URL:"):
                # Extract URL from line like "[ + ] URL: https://example.com/file.js"
                try:
                    current_url = line.split("URL:", 1)[1].strip()
                except:
                    current_url = "Unknown"
                continue
            
            # Process secret lines
            if "->" not in line:
                continue
                
            secret_type, evidence = map(str.strip, line.split("->", 1))
            
            # Try to extract filename from evidence or URL
            filename = "Unknown"
            if ":" in evidence:
                # Common format: filename:line:content
                parts = evidence.split(":", 2)
                if len(parts) >= 2:
                    filename = parts[0]
                    # Clean up filename - remove any path separators and get just the basename
                    if "/" in filename:
                        filename = filename.split("/")[-1]
                    elif "\\" in filename:
                        filename = filename.split("\\")[-1]
            elif current_url != "Unknown":
                # Extract filename from current URL
                try:
                    from urllib.parse import urlparse
                    parsed_url = urlparse(current_url)
                    filename = parsed_url.path.split('/')[-1] if parsed_url.path else "Unknown"
                    if not filename or filename == "":
                        filename = "Unknown"
                except:
                    filename = "Unknown"
            
            secrets[secret_type].append({
                "evidence": evidence,
                "filename": filename,
                "url": current_url
            })
    return secrets



def classify_api_exposure(data):
    """Deprecated placeholder (not used by the reference flow)."""
    return {"findings": [], "overall_risk": "INFO", "summary": {}}

def parse_secret_dump(dump_path: str) -> dict:
    """Deprecated parser (kept for compatibility). Use parse_secret_file instead."""
    return {"secrets": [], "total_secrets": 0, "files_analyzed": 0}

async def main():
    ap = argparse.ArgumentParser(
        description="Classify and explain secrets from a SecretFinder text dump.")
    ap.add_argument("input_file", type=Path, help="Path to secrets.txt")
    ap.add_argument("--report-json", type=Path, default=Path("secret_report.json"))
    ap.add_argument("--report-md",   type=Path, default=Path("secret_report.md"))
    ap.add_argument("--report-pdf",  type=Path, default=Path("secret_report.pdf"))
    ap.add_argument("--target-url", type=str, default=None, help="Target URL being analyzed (shown in PDF header)")
    args = ap.parse_args()

    if not args.input_file.exists():
        ap.error(f"Input file {args.input_file} not found.")

    try:
        # Ensure reports directory exists
        reports_dir = Path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Derive persistent output filenames if defaults are used
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_label = "report"
        if args.target_url:
            try:
                from urllib.parse import urlparse
                netloc = urlparse(args.target_url).netloc or args.target_url
                base_label = netloc
            except Exception:
                base_label = args.target_url
        # Sanitize for filenames
        base_label = re.sub(r"[^A-Za-z0-9]+", "_", base_label).strip("_") or "report"

        # Only override when user left the defaults
        if args.report_json == Path("secret_report.json"):
            args.report_json = reports_dir / f"{base_label}_api_exposure_report_{timestamp}.json"
        if args.report_md == Path("secret_report.md"):
            args.report_md = reports_dir / f"{base_label}_api_exposure_report_{timestamp}.md"
        if args.report_pdf == Path("secret_report.pdf"):
            args.report_pdf = reports_dir / f"{base_label}_api_exposure_report_{timestamp}.pdf"

        secrets = parse_secret_file(args.input_file)
        report = await build_json_report(secrets)
        # Inject target URL for PDF header if provided
        if args.target_url:
            report["target_url"] = args.target_url
        markdown_content = build_markdown(report)

        # Save outputs
        
        try:
            args.report_json.write_text(json.dumps(report, indent=2))
            print(f"✅ Wrote JSON file")
        except Exception as json_error:
            print(f"❌ Failed to write JSON: {json_error}")
            raise json_error
            
        try:
            args.report_md.write_text(markdown_content)
            print(f"✅ Wrote MD file")
        except Exception as md_error:
            print(f"❌ Failed to write MD: {md_error}")
            raise md_error

        # Generate PDF using the imported builder
        try:
            build_pdf_report(report, args.report_pdf)
            print(f"✓ Analysis complete. JSON → {args.report_json}, Markdown → {args.report_md}, PDF → {args.report_pdf}")
        except Exception as pdf_error:
            print(f"⚠️ PDF generation failed: {pdf_error}")
            print(f"✓ Analysis complete. JSON → {args.report_json}, Markdown → {args.report_md} (PDF skipped)")

        # Skipping cloud uploads; reports are kept locally

        # Keep input and reports; no cleanup to ensure outputs remain permanent

        # Return local artifact paths
        result = {
            "markdown_report": str(args.report_md),
            "json_report": str(args.report_json),
            "pdf_report": str(args.report_pdf),
        }
        
        # Log what we're returning
        print(f"📋 Returning artifacts:")
        print(f"   - markdown_report: {result['markdown_report']}")
        print(f"   - json_report: {result['json_report']}")
        print(f"   - pdf_report: {result['pdf_report']}")
        
        return result

    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        # No cleanup on error to preserve artifacts for debugging
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
