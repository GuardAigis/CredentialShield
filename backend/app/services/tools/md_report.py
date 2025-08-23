#!/usr/bin/env python3
"""
Markdown Report Generator
"""

from typing import Dict

def build_markdown(findings_json: Dict) -> str:
    """Generate markdown report in the format expected by the frontend (reference)."""
    md = [
        "# API Exposure Security Report",
        f"**Overall Risk Level:** {findings_json['overall_risk']}",
        f"**Analysis Type:** {findings_json.get('analysis_type', 'api_exposure')}",
        f"**Timestamp:** {findings_json.get('timestamp', 'Unknown')}",
        "",
        "## Summary",
        f"- **Total Findings:** {findings_json['summary']['total_findings']}",
        f"- **Critical:** {findings_json['summary']['critical_findings']}",
        f"- **High:** {findings_json['summary']['high_findings']}",
        f"- **Medium:** {findings_json['summary']['medium_findings']}",
        f"- **Low:** {findings_json['summary']['low_findings']}",
        "",
        "## Vulnerability Findings",
        ""
    ]
    for f in findings_json["findings"]:
        # Get filename and URL from evidence_data if available
        filename = "Unknown"
        url = "Unknown"
        evidence_data = f.get('evidence_data', [])
        if evidence_data and len(evidence_data) > 0:
            filename = evidence_data[0].get('filename', 'Unknown')
            url = evidence_data[0].get('url', 'Unknown')
        
        # Get verification status for warning/bug badge
        verification = f.get('verification', {})
        is_verified = bool(verification.get('verified', False))
        verify_label = 'BUG' if is_verified else 'WARNING'
        
        md.extend([
            f"### {f['title']}",
            f"**Severity:** {f['severity']} | **Status:** {f['status']} | **File:** {filename} | **Verification:** {verify_label}",
        ])
        
        if url != "Unknown":
            md.append(f"**URL:** {url}")
        
        md.extend([
            "",
            f"**Description:**",
            f"{f['description']}",
            "",
            f"**Impact:**",
            f"{f['impact']}",
            "",
            "**Remediation Steps:**",
        ])
        for i, step in enumerate(f['remediation_steps'], 1):
            md.append(f"{i}. {step}")
        md.extend([
            "",
            f"**Evidence:**",
            f"```",
        ])
        
        # Use evidence_data if available, otherwise fall back to evidence
        if evidence_data:
            for ev_item in evidence_data[:3]:
                filename = ev_item.get('filename', 'Unknown')
                evidence_text = ev_item.get('evidence', '')
                url = ev_item.get('url', 'Unknown')
                if url != 'Unknown':
                    md.append(f"- URL: {url}")
                    md.append(f"  {filename}: {evidence_text}")
                else:
                    md.append(f"- {filename}: {evidence_text}")
        else:
            for evidence in f['evidence'][:3]:
                md.append(f"- {evidence}")
        
        md.extend([
            "```",
            "",
            f"**Risk Score:** {(f['risk_score'] * 100):.0f}%",
            f"**Confidence:** {f['confidence_level']}",
        ])
        
        # Add verification details if available
        if verification.get('attempted', False):
            md.append(f"**Verification Attempted:** Yes")
            if verification.get('results'):
                md.append("**Verification Results:**")
                for i, result in enumerate(verification['results'][:2], 1):  # Show first 2 results
                    success = result.get('success', False)
                    status = "✅ SUCCESS" if success else "❌ FAILED"
                    md.append(f"  {i}. {status}")
                    if result.get('command'):
                        md.append(f"     Command: `{result['command']}`")
                    if result.get('stdout'):
                        md.append(f"     Output: {result['stdout'][:200]}...")
        
        md.extend([
            "",
            "---",
            "",
        ])
    return "\n".join(md)
