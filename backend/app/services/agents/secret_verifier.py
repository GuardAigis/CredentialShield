#!/usr/bin/env python3
import re, shlex, asyncio, sys, json
from pathlib import Path
from typing import Tuple
from openai import AsyncOpenAI
from dotenv import load_dotenv

MD_PATH = Path(__file__).parent / "key_verifier.md"

# Initialize OpenAI client for AI-assisted verification
load_dotenv()
client = AsyncOpenAI()

def normalize(s: str) -> str:
    """
    Normalize a string by removing all non-alphanumeric characters and converting to lowercase.
    
    Args:
        s (str): The input string to normalize
        
    Returns:
        str: Normalized string containing only lowercase letters and numbers
        
    Example:
        >>> normalize("GitHub API Key (v2)")
        'githubapikeyv2'
    """
    return re.sub(r"[^a-z0-9]+", "", s.lower())

def extract_commands(secret_type: str, md_text: str) -> list[str]:
    """
    Extract curl commands from markdown text that match the specified secret type.
    
    This function parses the key_verifier.md file to find curl commands for verifying
    specific types of API keys or secrets. It searches for sections that match the
    secret type and extracts all curl commands from code blocks and inline curl lines.
    
    Args:
        secret_type (str): The type of secret to search for (e.g., "GitHub Token", "AWS Key")
        md_text (str): The markdown content to search through
        
    Returns:
        list[str]: List of curl command strings found for the specified secret type
        
    Example:
        >>> commands = extract_commands("GitHub Token", markdown_content)
        >>> print(commands)
        ['curl -s -H "Authorization: token TOKEN_HERE" "https://api.github.com/users/USERNAME_HERE/orgs"']
    """
    wanted = normalize(secret_type)
    commands: list[str] = []
    sections = md_text.split("## ")
    
    for sec in sections:
        lines = sec.splitlines()
        if not lines:
            continue
        title = re.sub(r"\([^)]*\)$", "", re.sub(r"\[([^]]+)\].*", r"\1", lines[0].strip())).strip()
        if not title:
            continue
            
        normalized_title = normalize(title)
        
        if (normalized_title in wanted) or (wanted in normalized_title):
            body = "\n".join(lines[1:])
            
            # code fences (``` or ````)
            code_blocks = re.findall(r"(`{3,}).*?\n(.*?)\n\1", body, re.DOTALL | re.IGNORECASE)
            
            for block in code_blocks:
                for line in block[1].splitlines():
                    if line.strip().lower().startswith("curl"):
                        commands.append(line.strip())
            
            # inline curl lines
            inline_curls = re.findall(r"^curl[^\n\r]*$", body, re.MULTILINE | re.IGNORECASE)
            
            for line in inline_curls:
                if line.strip() not in commands:
                    commands.append(line.strip())
    return commands

def parse_curl_evidence(evidence: str) -> tuple[str, str]:
    """
    Parse curl evidence to extract the command and token placeholder.
    
    This function analyzes a curl command to identify token placeholders and
    returns both the command and the placeholder pattern found.
    
    Args:
        evidence (str): Curl command with token placeholder (e.g., "curl -X GET -H "X-TrackerToken: $TOKEN" ...")
        
    Returns:
        tuple[str, str]: A tuple containing:
            - command_with_placeholder (str): The original curl command
            - token_placeholder (str): The placeholder pattern found, or None if no pattern detected
            
    Example:
        >>> cmd, placeholder = parse_curl_evidence('curl -H "Authorization: Bearer $TOKEN" https://api.example.com')
        >>> print(cmd)
        'curl -H "Authorization: Bearer $TOKEN" https://api.example.com'
        >>> print(placeholder)
        '$TOKEN'
    """
    # Look for common token patterns in curl commands
    token_patterns = [
        r'\$TOKEN',
        r'\$API_KEY',
        r'\$TOKEN_HERE',
        r'<your_token>',
        r'API_KEY_HERE',
        r'TOKEN_HERE'
    ]
    
    for pattern in token_patterns:
        if re.search(pattern, evidence):
            return evidence, pattern
    
    # If no token pattern found, assume the last part might be the token
    return evidence, None


async def verifier(secret_type: str, evidence: str, command: str) -> Tuple[str, str]:
    """
    AI-powered secret verification function.
    
    This function uses GPT-4o-mini to analyze evidence and command to provide verification guidance.
    
    Args:
        secret_type (str): The type of secret to verify (e.g., "GitHub Token", "AWS Key")
        evidence (str): The evidence string containing the secret/token
        command (str): The curl command to be used for verification
        
    Returns:
        Tuple[str, str]: A tuple containing (verification_status, analysis) where:
            - verification_status: One of [VALID, INVALID, UNKNOWN, ERROR]
            - analysis: Detailed analysis of the evidence and command for verification
            
    Example:
        >>> status, analysis = await verifier("GitHub Token", "ghp_abc123", "curl -H 'Authorization: token $TOKEN' https://api.github.com/user")
        >>> print(f"Status: {status}")
        Status: VALID
    """
    prompt = f"""
You are a cybersecurity expert specializing in verification of sensitive secret exposure.
Secret type: "{secret_type}"
Evidence: "{evidence}"
Command: "{command}"

Analyze the evidence and command to determine if this is a valid verification approach.
Consider:
1. Does the command format match the secret type?
2. Are the placeholders in the command appropriate for the evidence?
3. What would be the expected outcome of running this command?

Respond in json format:
{{"verification_status": "VALID|INVALID|UNKNOWN|ERROR", "analysis": "detailed explanation of the verification approach and expected results"}}
"""
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful security analyst specializing in secret verification."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    content = response.choices[0].message.content
    data = json.loads(content)
    return data["verification_status"], data["analysis"]


async def run_command(cmd: str, token: str | None = None, timeout: int = 60):
    """
    Execute a curl command with optional token replacement.
    
    This function takes a curl command template, replaces token placeholders with
    actual tokens, and executes the command asynchronously. It handles various
    placeholder formats and provides timeout protection.
    
    Args:
        cmd (str): The curl command to execute (may contain token placeholders)
        token (str | None): The actual token to replace placeholders with
        timeout (int): Maximum execution time in seconds (default: 60)
        
    Returns:
        tuple: A tuple containing:
            - returncode (int): The exit code of the command (0 for success)
            - stdout (str): Standard output from the command
            - stderr (str): Standard error from the command
            - executed_cmd (str): The actual command that was executed (with token replaced)
            
    Example:
        >>> code, out, err, exec_cmd = await run_command('curl -H "Authorization: Bearer $TOKEN" https://api.example.com', 'abc123')
        >>> print(f"Executed: {exec_cmd}")
        Executed: curl -H "Authorization: Bearer abc123" https://api.example.com
    """
    original_cmd = cmd
    # Replace common placeholders
    if token:
        # Replace various token placeholders
        replacements = {
            "<your_token>": token,
            "API_KEY_HERE": token,
            "TOKEN_HERE": token,
            "$TOKEN": token,
            "$API_KEY": token,
            "TOKEN": token
        }
        
        for placeholder, replacement in replacements.items():
            cmd = cmd.replace(placeholder, replacement)
    
    args = shlex.split(cmd)
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out_b, err_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    return proc.returncode, out_b.decode(errors="replace"), err_b.decode(errors="replace"), cmd

async def verify_secret_with_evidence(evidence: str, token: str, timeout: int = 60):
    """
    Verify a secret using provided curl evidence and token.
    
    This function takes a curl command evidence and an actual token, then executes
    the command to verify if the secret is valid. It analyzes the response to
    determine success or failure based on exit codes and error messages.
    
    Args:
        evidence (str): Curl command with token placeholder (e.g., "curl -X GET -H "X-TrackerToken: $TOKEN" ...")
        token (str): The actual token to use for verification
        timeout (int): Command timeout in seconds (default: 60)
    
    Returns:
        tuple: A tuple containing:
            - success (bool): True if verification was successful, False otherwise
            - exit_code (int): The exit code from the curl command
            - stdout (str): Standard output from the command
            - stderr (str): Standard error from the command
            
    Example:
        >>> success, code, out, err = await verify_secret_with_evidence(
        ...     'curl -H "Authorization: Bearer $TOKEN" https://api.example.com/user',
        ...     'valid_token_here'
        ... )
        >>> print(f"Verification successful: {success}")
        Verification successful: True
    """
    try:
        # Parse the evidence to get the command with placeholder
        command, placeholder = parse_curl_evidence(evidence)
        
        if not command.strip().lower().startswith("curl"):
            return False, -1, "", "Error: Evidence must be a curl command"
        
        # Run the command with the provided token
        exit_code, stdout, stderr = await run_command(command, token=token, timeout=timeout)
        
        # Consider it successful if exit code is 0 and no obvious error messages
        success = exit_code == 0 and not any(error in stderr.lower() for error in [
            "unauthorized", "forbidden", "invalid", "authentication failed", "access denied"
        ])
        
        return success, exit_code, stdout, stderr
        
    except Exception as e:
        return False, -1, "", f"Error executing command: {str(e)}"

async def main():
    """
    Main entry point for the secret verifier script.
    
    This function handles command-line arguments and provides two modes of operation:
    1. Evidence mode: Verify a specific curl command with a token
    2. Secret type mode: Search for commands by secret type and optionally run them
    
    Command line usage:
        python secret_verifier.py "<Secret Type>" [token]
        python secret_verifier.py --evidence "<curl_command>" --token <actual_token>
        
    Examples:
        python secret_verifier.py "GitHub Token" abc123
        python secret_verifier.py --evidence "curl -H 'Authorization: Bearer $TOKEN' https://api.github.com/user" --token abc123
    """
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python secret_verifier.py \"<Secret Type>\" [token]")
        print("  python secret_verifier.py --evidence \"curl -X GET -H 'X-TrackerToken: $TOKEN' 'https://...'\" --token <actual_token>")
        sys.exit(1)
    
    # Check if using evidence mode
    if sys.argv[1] == "--evidence":
        if len(sys.argv) < 5 or sys.argv[3] != "--token":
            print("Usage: python secret_verifier.py --evidence \"<curl_command>\" --token <token>")
            sys.exit(1)
        
        evidence = sys.argv[2]
        token = sys.argv[4]
        
        print(f"Verifying secret with evidence: {evidence}")
        print(f"Using token: {token[:10]}..." if len(token) > 10 else f"Using token: {token}")
        
        success, exit_code, stdout, stderr = await verify_secret_with_evidence(evidence, token)
        
        print(f"\nVerification Result:")
        print(f"Success: {success}")
        print(f"Exit Code: {exit_code}")
        print(f"--- STDOUT ---\n{stdout[:500]}")
        if stderr:
            print(f"--- STDERR ---\n{stderr[:500]}")
        
        return
    
    # Original mode - search by secret type
    secret_type = sys.argv[1]
    token = sys.argv[2] if len(sys.argv) > 2 else None

    md_text = MD_PATH.read_text(encoding="utf-8", errors="ignore")
    cmds = extract_commands(secret_type, md_text)
    if not cmds:
        print("No commands found.")
        return

    print(f"Found {len(cmds)} command(s):")
    for i, c in enumerate(cmds, 1):
        print(f"{i}. {c}")

    # Optional: run first command
    if token:
        print(f"\nRunning the first command with token: {token[:10]}..." if len(token) > 10 else f"\nRunning the first command with token: {token}")
        code, out, err = await run_command(cmds[0], token=token)
        print(f"\nExit code: {code}\n--- STDOUT ---\n{out[:400]}\n--- STDERR ---\n{err[:400]}")
    else:
        print("\nNo token provided. Commands shown above can be run manually with a valid token.")

if __name__ == "__main__":
    asyncio.run(main())