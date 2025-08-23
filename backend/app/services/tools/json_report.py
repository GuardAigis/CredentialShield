#!/usr/bin/env python3
"""
JSON Report Generator
"""

from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict
import json
import re
from ..agents.secret_verifier import extract_commands, run_command, verifier
from ..agents.ai_classifier import Remediation_Agent, classify

def get_impact_description(risk: str, secret_type: str) -> str:
    """Generate impact description based on risk level (reference)."""
    impact_descriptions = {
        "CRITICAL": f"Attackers could potentially access, modify, or delete sensitive data using the exposed {secret_type}. This represents a severe security breach.",
        "HIGH": f"Attackers could potentially access sensitive information or perform unauthorized actions using the exposed {secret_type}.",
        "MEDIUM": f"The exposed {secret_type} could potentially be used for unauthorized access or data exposure.",
        "LOW": f"The exposed {secret_type} may pose minimal risk but should be reviewed for potential security implications.",
        "INFO": f"The exposed {secret_type} should be validated to determine if it represents a security risk.",
    }
    return impact_descriptions.get(risk, "Unknown risk level.")

def get_risk_score(risk: str) -> float:
    """Convert risk level to numerical score (reference)."""
    risk_scores = {"CRITICAL": 0.9, "HIGH": 0.7, "MEDIUM": 0.5, "LOW": 0.3, "INFO": 0.1}
    return risk_scores.get(risk, 0.0)

def _extract_candidate_token(evidence_strings: List[str]) -> str | None:
    """Best-effort extraction of a token-like value from evidence strings.

    Looks for common secret patterns first; falls back to longest token-like chunk.
    """
    token_patterns = [
        r"sk_live_[A-Za-z0-9]{16,}",
        r"sk_test_[A-Za-z0-9]{16,}",
        r"xox[baprs]-[A-Za-z0-9-]{16,}",
        r"ghp_[A-Za-z0-9]{20,}",
        r"AIza[0-9A-Za-z\-_]{20,}",
        r"AKIA[0-9A-Z]{16}",
        r"EAACEdEose0cBA[0-9A-Za-z]{10,}",
        r"[A-Za-z0-9_\-]{24,}",
    ]

    for ev in evidence_strings:
        for pat in token_patterns:
            m = re.search(pat, ev)
            if m:
                return m.group(0)

    best: str | None = None
    for ev in evidence_strings:
        for chunk in re.findall(r"[A-Za-z0-9_\-]{20,}", ev):
            if best is None or len(chunk) > len(best):
                best = chunk
    return best

async def _verify_secret_type(secret_type: str, evid_list: List[Dict]) -> Dict:
    """Extract validation commands for the secret type and attempt lightweight verification.

    Also runs an AI-based verifier over the best available evidence and each
    candidate command to provide guidance. The AI output is attached to each
    command result as "ai_status" and "ai_analysis".
    """
    try:
        from pathlib import Path
        # Fix the path to point to the correct location of key_verifier.md
        key_md_path = Path(__file__).parent.parent / "agents" / "key_verifier.md"
        md_text = key_md_path.read_text(encoding="utf-8", errors="ignore") if key_md_path.exists() else ""

        commands: List[str] = extract_commands(secret_type, md_text) if md_text else []

        evidence_strings = [item.get("evidence", "") for item in evid_list]
        
        attempted = False   
        verified = False
        results: List[Dict] = []

        placeholder_terms = ("<your_token>", "API_KEY_HERE", "TOKEN", "TOKEN_HERE")

        # Try multiple evidence values, not just the first one
        for cmd in commands[:3]:
            cmd_attempted = False
            cmd_verified = False
            best_result = None
            
            # Try each evidence string as a potential token
            for i, evidence in enumerate(evidence_strings[:5]):  # Try first 5 evidence values
                # Always ask AI verifier for guidance
                ai_status: str | None = None
                ai_analysis: str | None = None
                try:
                    ai_status, ai_analysis = await verifier(secret_type, evidence, cmd)
                except Exception as ex:
                    ai_status, ai_analysis = "ERROR", str(ex)

                if any(term in cmd for term in placeholder_terms):
                    cmd_attempted = True
                    attempted = True
                    try:
                        code, out, err, executed_cmd = await run_command(cmd, token=evidence, timeout=20)
                        combined = (out + "\n" + err).lower()
                        looks_auth_error = any(word in combined for word in ["unauthorized", "forbidden", "invalid", "denied"])  # heuristic
                        success = (code == 0) and not looks_auth_error and len(out.strip()) > 0
                        
                        if success:
                            cmd_verified = True
                            verified = True
                        
                        result = {
                            "command": cmd,  # Original command template
                            "executed_command": executed_cmd,  # Actual command that was run
                            "exit_code": code,
                            "stdout": out[:4000],
                            "stderr": err[:4000],
                            "success": success,
                            "ai_status": ai_status,
                            "ai_analysis": ai_analysis,
                            "evidence_used": evidence[:50] + "..." if len(evidence) > 50 else evidence,
                        }
                        
                        # Keep the best result (successful ones first, then by evidence order)
                        if best_result is None or (success and not best_result.get("success", False)):
                            best_result = result
                            
                    except Exception as ex:
                        result = {
                            "command": cmd,
                            "error": str(ex),
                            "success": False,
                            "ai_status": ai_status,
                            "ai_analysis": ai_analysis,
                            "evidence_used": evidence[:50] + "..." if len(evidence) > 50 else evidence,
                        }
                        if best_result is None:
                            best_result = result
                
                # If we found a successful verification, no need to try more evidence
                if cmd_verified:
                    break
            
            # If no runnable attempt was made, still record AI guidance
            if not cmd_attempted:
                best_result = {
                    "command": cmd,
                    "success": False,
                    "ai_status": ai_status,
                    "ai_analysis": ai_analysis,
                    "evidence_used": "No token candidates found",
                }
            
            if best_result:
                results.append(best_result)


        
        return {
            "commands": commands[:3],
            "attempted": attempted,
            "verified": verified,
            "results": results,
        }
    except Exception as e:
        return {"commands": [], "attempted": False, "verified": False, "error": str(e), "results": []}

async def build_json_report(secrets: Dict[str, List[Dict]]) -> Dict:
    """Reference builder that classifies and composes findings JSON."""
    findings: List[Dict] = []
    highest_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
    max_score = 0

    for stype, evid_list in secrets.items():
        risk, desc = await classify(stype)
        max_score = max(max_score, highest_rank.get(risk, 0))
        ai_remediation_steps = await Remediation_Agent(stype)
        # Attempt verification using key_verifier.md commands and evidence
        verification = await _verify_secret_type(stype, evid_list)
        
        # Extract evidence strings and structured data with URLs
        evidence_strings = [item["evidence"] for item in evid_list[:5]]
        evidence_data = evid_list[:5]  # Keep the structured data for PDF (includes URL, filename, evidence)
        
        finding = {
            "id": f"api_exposure_{stype.lower().replace(' ', '_')}",
            "title": f"API Exposure - {stype}",
            "severity": risk,
            "status": "OPEN",
            "endpoint": "JavaScript Files",
            "description": desc,
            "impact": get_impact_description(risk, stype),
            "remediation_steps": ai_remediation_steps,
            "validation_commands": verification.get("commands", []),
            "verification": {
                "attempted": verification.get("attempted", False),
                "verified": verification.get("verified", False),
                "commands": verification.get("commands", []),
                "results": verification.get("results", []),
            },
            "evidence": evidence_strings,
            "evidence_data": evidence_data,  # Structured data with filenames
            "secret_type": stype,
            "risk_score": get_risk_score(risk),
            "confidence_level": "high",
            "timestamp": datetime.now().isoformat(),
            "category": "api_exposure",
        }
        findings.append(finding)
    
    overall_risk = ({v: k for k, v in highest_rank.items()}[max_score] if findings else "INFO")
    return {
        "overall_risk": overall_risk,
        "summary": {
            "total_findings": len(findings),
            "critical_findings": len([f for f in findings if f["severity"] == "CRITICAL"]),
            "high_findings": len([f for f in findings if f["severity"] == "HIGH"]),
            "medium_findings": len([f for f in findings if f["severity"] == "MEDIUM"]),
            "low_findings": len([f for f in findings if f["severity"] == "LOW"]),
            "total_secret_types": len(secrets),
            "total_evidences": sum(len(v) for v in secrets.values()),
        },
        "findings": sorted(findings, key=lambda f: highest_rank.get(f["severity"], 0), reverse=True),
        "analysis_type": "api_exposure",
        "timestamp": datetime.now().isoformat(),
    }
