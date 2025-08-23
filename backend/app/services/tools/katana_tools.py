"""
Katana Tools - Integration with Project Discovery Katana for URL discovery
Using subprocess for direct binary execution
"""

import asyncio
import json
import os
import tempfile
import subprocess
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class KatanaTools:
    """Tools for interacting with Project Discovery Katana via subprocess"""
    
    def __init__(self, katana_binary: str = "katana"):
        self.katana_binary = katana_binary
        self.output_dir = os.path.join(os.getcwd(), "katana_output")
        os.makedirs(self.output_dir, exist_ok=True)
    
    async def run_katana_discovery(
        self, 
        target_url: str, 
        max_depth: int = 2,
        max_pages: int = 100,
        output_format: str = "json"
    ) -> Dict[str, Any]:
        """
        Run Katana URL discovery on a target website using subprocess
        
        Args:
            target_url: The target website URL
            max_depth: Maximum crawl depth (default: 2)
            max_pages: Maximum pages to crawl (default: 100)
            output_format: Output format (json, txt) (default: json)
            
        Returns:
            Dictionary with discovery results
        """
        try:
            logger.info(f"🔍 Starting Katana discovery for: {target_url}")
            
            # Check Katana availability first
            availability = await self.check_katana_availability()
            if not availability.get("available"):
                error_msg = availability.get("error", "Katana not available")
                suggestions = availability.get("suggestions", [])
                
                logger.error(f"❌ Katana not available: {error_msg}")
                if suggestions:
                    logger.error("💡 Suggestions:")
                    for suggestion in suggestions:
                        logger.error(f"   - {suggestion}")
                
                return {
                    "status": "error",
                    "error": f"Katana not available: {error_msg}",
                    "target_url": target_url,
                    "timestamp": datetime.utcnow().isoformat(),
                    "suggestions": suggestions
                }
            
            # Build Katana command
            cmd = [
                self.katana_binary,
                "-u", target_url,
                "-d", str(max_depth),
                "-jc", str(max_pages)
            ]
            
            # Add JSON output format
            if output_format == "json":
                cmd.append("-json")
            
            logger.info(f"🚀 Executing Katana: {' '.join(cmd)}")
            
            # Run Katana process
            result = await self._run_subprocess_async(cmd, timeout=300)
            
            if result["status"] == "error":
                return {
                    "status": "error",
                    "error": result["error"],
                    "target_url": target_url,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Parse results from subprocess output
            results = await self._parse_katana_output(result["output"], target_url)
            
            logger.info(f"✅ Katana discovery completed: {len(results.get('urls', []))} URLs found")
            return results
            
        except Exception as e:
            logger.error(f"❌ Katana discovery error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "target_url": target_url,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def run_katana_with_custom_config(
        self, 
        target_url: str, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run Katana with custom configuration using subprocess
        
        Args:
            target_url: The target website URL
            config: Custom Katana configuration
            
        Returns:
            Dictionary with discovery results
        """
        try:
            # Build command from config
            cmd = [self.katana_binary, "-u", target_url]
            
            # Add configuration options
            if "depth" in config:
                cmd.extend(["-d", str(config["depth"])])
            
            if "max_pages" in config:
                cmd.extend(["-jc", str(config["max_pages"])])
            
            if "timeout" in config:
                cmd.extend(["-timeout", str(config["timeout"])])
            
            if "concurrency" in config:
                cmd.extend(["-c", str(config["concurrency"])])
            
            if "user_agent" in config:
                cmd.extend(["-H", f"User-Agent: {config['user_agent']}"])
            
            if "cookies" in config:
                cmd.extend(["-cookie", config["cookies"]])
            
            if "headers" in config:
                for header in config["headers"]:
                    cmd.extend(["-H", header])
            
            # Add output format
            output_format = config.get("output_format", "json")
            if output_format == "json":
                cmd.append("-json")
            
            logger.info(f"🚀 Executing custom Katana: {' '.join(cmd)}")
            
            # Run Katana process
            result = await self._run_subprocess_async(cmd, timeout=300)
            
            if result["status"] == "error":
                return {
                    "status": "error",
                    "error": result["error"],
                    "target_url": target_url,
                    "config": config,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Parse results
            results = await self._parse_katana_output(result["output"], target_url)
            results["config_used"] = config
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Custom Katana discovery error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "target_url": target_url,
                "config": config,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def run_katana_scan(self, url: str) -> List[str]:
        """
        Enhanced version of the user's run_katana_scan function
        
        Args:
            url: URL to scan for JavaScript files
            
        Returns:
            List of JavaScript file URLs
        """
        try:
            logger.info(f"🔍 Scanning for JS files: {url}")
            
            # Build command to get JS files specifically
            cmd = f'{self.katana_binary} -u {url} -jc -d 2 | grep "\\.js$" | uniq | sort'
            
            # Use shell=True for pipe operations
            result = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                js_files = stdout.decode('utf-8').strip().split('\n')
                # Filter out empty lines
                js_files = [f for f in js_files if f.strip()]
                logger.info(f"✅ Found {len(js_files)} JavaScript files")
                return js_files
            else:
                error_msg = stderr.decode('utf-8')
                logger.error(f"❌ Katana scan failed: {error_msg}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error in run_katana_scan: {str(e)}")
            return []
    
    async def _run_subprocess_async(
        self,
        cmd: List[str],
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Run subprocess asynchronously with timeout
        
        Args:
            cmd: Command to run
            timeout: Timeout in seconds
            
        Returns:
            Dictionary with subprocess output and status
        """
        try:
            logger.info(f"🔧 Running subprocess: {' '.join(cmd)}")
            
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.kill()
                await process.wait()
                return {
                    "status": "error",
                    "error": f"Process timed out after {timeout} seconds",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Check return code
            if process.returncode == 0:
                output = stdout.decode('utf-8')
                return {
                    "status": "success",
                    "output": output,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                error = stderr.decode('utf-8') if stderr else "Process failed"
                return {
                    "status": "error",
                    "error": f"Process failed with exit code {process.returncode}: {error}",
                    "exit_code": process.returncode,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"❌ Subprocess error: {str(e)}")
            return {
                "status": "error",
                "error": f"Subprocess error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _parse_katana_output(self, output: str, target_url: str) -> Dict[str, Any]:
        """Parse Katana output and extract URLs"""
        try:
            urls = []
            login_urls = []
            functional_urls = []
            api_urls = []
            
            # Parse JSON output line by line
            for line in output.strip().split('\n'):
                if line.strip():
                    try:
                        # Try parsing as JSON first
                        data = json.loads(line)
                        url = data.get('url', '')
                        
                        if url:
                            urls.append(url)
                            
                            # Categorize URLs
                            url_lower = url.lower()
                            if any(pattern in url_lower for pattern in ['login', 'signin', 'auth', 'register', 'signup']):
                                login_urls.append(url)
                            elif any(pattern in url_lower for pattern in ['api', 'rest', 'graphql', 'swagger']):
                                api_urls.append(url)
                            elif any(pattern in url_lower for pattern in ['dashboard', 'admin', 'profile', 'settings', 'account']):
                                functional_urls.append(url)
                    
                    except json.JSONDecodeError:
                        # Handle non-JSON lines (treat as plain URLs)
                        if line.strip().startswith('http'):
                            url = line.strip()
                            urls.append(url)
                            
                            # Categorize URLs
                            url_lower = url.lower()
                            if any(pattern in url_lower for pattern in ['login', 'signin', 'auth', 'register', 'signup']):
                                login_urls.append(url)
                            elif any(pattern in url_lower for pattern in ['api', 'rest', 'graphql', 'swagger']):
                                api_urls.append(url)
                            elif any(pattern in url_lower for pattern in ['dashboard', 'admin', 'profile', 'settings', 'account']):
                                functional_urls.append(url)
            
            return {
                "status": "success",
                "target_url": target_url,
                "total_urls": len(urls),
                "urls": urls,
                "login_urls": login_urls,
                "functional_urls": functional_urls,
                "api_urls": api_urls,
                "discovery_method": "katana_subprocess",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error parsing Katana output: {str(e)}")
            return {
                "status": "error",
                "error": f"Failed to parse output: {str(e)}",
                "raw_output": output,
                "target_url": target_url,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def check_katana_availability(self) -> Dict[str, Any]:
        """Check if Katana is available and working using subprocess"""
        try:
            logger.info("🔧 Checking Katana availability...")
            
            # First check if binary exists
            import shutil
            if not shutil.which(self.katana_binary):
                return {
                    "available": False,
                    "status": "error",
                    "error": f"Katana binary '{self.katana_binary}' not found in PATH",
                    "binary": self.katana_binary,
                    "timestamp": datetime.utcnow().isoformat(),
                    "suggestions": [
                        "Install Katana: go install github.com/projectdiscovery/katana/cmd/katana@latest",
                        "Add Go bin to PATH: export PATH=$PATH:$(go env GOPATH)/bin",
                        "Or run inside Docker container where Katana is pre-installed"
                    ]
                }
            
            # Test run with version command
            result = await self._run_subprocess_async([self.katana_binary, "--version"], timeout=30)
            
            if result["status"] == "success":
                version = result["output"].strip()
                return {
                    "available": True,
                    "status": "available",
                    "version": version,
                    "binary": self.katana_binary,
                    "method": "subprocess",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "available": False,
                    "status": "error",
                    "error": result["error"],
                    "binary": self.katana_binary,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"❌ Error checking Katana: {str(e)}")
            return {
                "available": False,
                "status": "error",
                "error": f"Error checking Katana: {str(e)}",
                "binary": self.katana_binary,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def cleanup(self):
        """Cleanup resources (no-op for subprocess implementation)"""
        logger.info("🧹 Katana tools cleanup completed")

# Create a global instance
katana_tools = KatanaTools() 