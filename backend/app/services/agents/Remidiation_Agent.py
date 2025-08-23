"""
Remediation Agent (AI-powered)
Generates detailed remediation steps for a given secret type using OpenAI.

This mirrors the reference implementation you provided and exposes a single
async function `Remediation_Agent(secret_type: str) -> List[str]`.
"""

from typing import List
import json
from dotenv import load_dotenv
from openai import AsyncOpenAI


# Load environment variables for OpenAI credentials, etc.
load_dotenv()

# Async OpenAI client
client = AsyncOpenAI()


async def Remediation_Agent(secret_type: str) -> List[str]:
    """Return AI-generated remediation steps for the given secret type."""
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
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a cybersecurity expert providing practical remediation guidance."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        steps = data.get("remediation_steps")
        if isinstance(steps, list) and steps:
            # Strip any leading "Step X:" prefixes for cleaner display
            normalized = []
            for s in steps:
                s = str(s)
                for k in range(1, 10):
                    s = s.replace(f"Step {k}:", "").strip()
                normalized.append(s)
            return normalized
    except Exception:
        # Fall back to safe defaults on any error
        pass

    return [
        "Revoke the exposed credential(s) immediately and rotate keys/tokens.",
        "Remove secrets from client-side code and public repositories.",
        "Store secrets in a server-side secrets manager and enforce least privilege.",
        "Add CI/CD secret scanning (e.g., Gitleaks/TruffleHog) to prevent future leaks.",
    ]


