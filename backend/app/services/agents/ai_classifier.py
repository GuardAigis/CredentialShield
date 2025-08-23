#!/usr/bin/env python3
"""
AI Classifier Agent
Contains AI-powered functions for secret classification and remediation.
"""

import json
from typing import List, Tuple
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment and initialize AsyncOpenAI client
load_dotenv()
client = AsyncOpenAI()

async def Remediation_Agent(secret_type: str) -> List[str]:
    """
    AI-powered remediation steps generator.
    
    This function uses GPT-4o-mini to generate specific, actionable remediation steps
    for fixing security issues related to exposed secrets.
    
    Args:
        secret_type (str): The type of secret that was exposed (e.g., "GitHub Token", "AWS Key")
        
    Returns:
        List[str]: List of remediation steps as strings
        
    Example:
        >>> steps = await Remediation_Agent("GitHub Token")
        >>> print(steps)
        ['Step 1: Immediately revoke the exposed GitHub token...', 'Step 2: Generate a new token...']
    """
    prompt = f"""
You are a cybersecurity expert specializing in remediation of sensitive secret exposure.
Secret type: "{secret_type}"

Generate 3-5 specific, actionable remediation steps to fix this security issue.
Each step should be clear, practical, and immediately actionable.

Respond in json format with an array of steps:
{{"remediation_steps": [
    "Step 1: [specific action]",
    "Step 2: [specific action]",
    "Step 3: [specific action]"
]}}

Focus on:
- Immediate actions to secure the exposed secret
- Long-term prevention measures
- Best practices for secret management
- Tools and technologies to use
"""
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a cybersecurity expert providing practical remediation guidance."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    content = response.choices[0].message.content
    data = json.loads(content)
    return data.get("remediation_steps", ["Review and assess the security implications"])

async def classify(secret_type: str) -> Tuple[str, str]:
    """
    AI-powered secret classification function.
    
    This function uses GPT-4o-mini to classify the risk level and generate a description
    for a given secret type.
    
    Args:
        secret_type (str): The type of secret to classify (e.g., "GitHub Token", "AWS Key")
        
    Returns:
        Tuple[str, str]: A tuple containing (risk_level, description) where:
            - risk_level: One of [CRITICAL, HIGH, MEDIUM, LOW, INFO]
            - description: Explanation of the secret and its security implications
            
    Example:
        >>> risk, desc = await classify("GitHub Token")
        >>> print(f"Risk: {risk}")
        Risk: HIGH
        >>> print(f"Description: {desc}")
        Description: GitHub tokens provide access to repositories and user data...
    """
    prompt = f"""
You are a cybersecurity expert specializing in detection of sensitive secret exposure.
Secret type: "{secret_type}"

Classify the risk as one of [CRITICAL, HIGH, MEDIUM, LOW, INFO].
Give a simple explanation of the secret and its risk.
Respond in json: {{"risk": "...", "description": "..."}}
"""
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful security analyst."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    content = response.choices[0].message.content
    data = json.loads(content)
    return data["risk"], data["description"]
