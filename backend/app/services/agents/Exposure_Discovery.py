#!/usr/bin/env python3
"""
Dynamic Katana Discovery Script
Replicates: katana -u https://www.bricklimit.de/ -jc -d 2 | grep ".js$" | uniq | sort > brick.txt
But makes it dynamic for any URL and returns data instead of permanent files
"""

import asyncio
import subprocess
import sys
import os
import tempfile
from datetime import datetime
from typing import List, Dict, Any

async def run_katana_discovery(target_url: str, max_pages: str = "x", depth: int = 2):
    """
    Run Katana discovery and extract JavaScript files
    
    Args:
        target_url: The target website URL
        max_pages: Maximum pages to crawl (default: "x" for unlimited)
        depth: Maximum crawl depth (default: 2)
        
    Returns:
        List of JavaScript URLs discovered
    """
    

    
    try:
        # Build the Katana command using Docker
        cmd = [
            "docker", "run", "--rm",
            "--network", "host",
            "projectdiscovery/katana:latest",
            "-u", target_url,
            "-jc", str(max_pages),
            "-d", str(depth),
            "-system-chrome",
            "-headless"
        ]
        
        # Run Katana and pipe to grep for .js files
        katana_process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Get Katana output
        katana_stdout, katana_stderr = await katana_process.communicate()
        
        if katana_process.returncode != 0:
            return []
        
        # Process the output to extract JavaScript files
        urls = katana_stdout.decode().strip().split('\n')
        js_files = []
        
        for url in urls:
            if url.strip() and url.lower().endswith('.js'):
                js_files.append(url.strip())
        
        # Remove duplicates and sort
        js_files = sorted(list(set(js_files)))
        
        return js_files
        
    except Exception as e:
        return []

async def run_secret_analysis(js_urls: List[str]):
    """
    Run SecretFinder analysis on the discovered JavaScript files
    
    Args:
        js_urls: List of JavaScript URLs to analyze
        
    Returns:
        List of dictionaries containing secret information:
        [
            {
                "file": "https://example.com/script.js",
                "secret": "api_key_12345",
                "type": "API Key",
                "line": 42,
                "context": "const apiKey = 'api_key_12345';"
            },
            ...
        ]
    """
    

    
    try:
        # Import SecretFinder
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
        from app.services.tools.SecretFinder import find_secrets
        
        all_secrets = []
        
        for i, js_url in enumerate(js_urls):
            try:
                # Run SecretFinder without output file - get results directly
                # Use extract=False to get all pattern matches, not just extracted values
                secrets = find_secrets(
                    input_value=js_url,
                    mode="cli",
                    extract=False
                )
                
                if secrets and isinstance(secrets, list):
                    for secret in secrets:
                        # Create structured secret object
                        secret_info = {
                            "file": js_url,
                            "secret": secret,
                            "type": "Unknown",  # SecretFinder doesn't provide type by default
                            "line": None,       # SecretFinder doesn't provide line numbers
                            "context": secret   # Use the secret itself as context
                        }
                        all_secrets.append(secret_info)
                else:
                    pass
                
            except Exception as e:
                pass
        
        return all_secrets
        
    except Exception as e:
        return []

def create_secret_dump(secrets: List[Dict[str, str]]) -> str:
    """
    Create a temporary secret dump file in the format expected by Api_Exposure_classifier
    
    Args:
        secrets: List of secrets with file and secret information
        
    Returns:
        Path to temporary secret dump file
    """
    
    # Create temporary file for secret dump
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    temp_path = temp_file.name
    
    try:
        with open(temp_path, 'w') as f:
            f.write(f"SecretFinder Analysis Results\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Total files analyzed: {len(set(s['file'] for s in secrets))}\n")
            f.write(f"Total secrets found: {len(secrets)}\n")
            f.write("="*60 + "\n\n")
            
            for secret_info in secrets:
                f.write(f"File: {secret_info['file']}\n")
                f.write(f"Secret: {secret_info['secret']}\n")
                f.write("-" * 40 + "\n")
        
        return temp_path
        
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return None

async def main():
    """Main function"""
    
    if len(sys.argv) < 2:
        print("Usage: python Exposure_Discovery.py <target_url> [max_pages] [depth]")
        print("Example: python Exposure_Discovery.py https://example.com x 2")
        print("\nParameters:")
        print("  target_url: The website URL to analyze")
        print("  max_pages: Maximum pages to crawl (default: 'x' for unlimited)")
        print("  depth: Maximum crawl depth (default: 2)")
        sys.exit(1)
    
    target_url = sys.argv[1]
    max_pages = sys.argv[2] if len(sys.argv) > 2 else "x"
    depth = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    
    # Step 1: Run Katana discovery
    js_files = await run_katana_discovery(target_url, max_pages, depth)
    
    if not js_files:
        sys.exit(1)
    
    # Step 2: Run SecretFinder analysis
    secrets = await run_secret_analysis(js_files)
    
    if not secrets:
        sys.exit(0)
    
    # Step 3: Create temporary secret dump for API exposure classifier
    secret_dump_path = create_secret_dump(secrets)
    
    if not secret_dump_path:
        sys.exit(1)
    
    # Return the path for the API exposure classifier to use
    return secret_dump_path

if __name__ == "__main__":
    asyncio.run(main()) 