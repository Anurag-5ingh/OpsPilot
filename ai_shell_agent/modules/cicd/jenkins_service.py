"""
Jenkins Integration Service

Handles connection to Jenkins servers, fetching build information, and retrieving logs.
Supports Basic Auth with API tokens and filters builds by server context.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, quote
import base64
import json
import re
import time

from .models import BuildLog, JenkinsConfig
from ..ssh.secrets import get_secret

# Disable SSL warnings for corporate environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class JenkinsService:
    """Service for interacting with Jenkins API."""
    
    def __init__(self, config: JenkinsConfig):
        self.config = config
        self.base_url = config.base_url
        self.username = config.username
        self._auth_header = None
        self._session = requests.Session()
        self._session.timeout = 30
        
        # Disable SSL verification for corporate/self-signed certificates
        self._session.verify = False
        
        # Set up retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)
        
        # Set up authentication
        self._setup_auth()
        
        # Log sanitized initialization details
        try:
            logger.info(
                "JenkinsService initialized: config_id=%s base_url=%s user=%s has_api_token=%s has_password=%s auth_header_set=%s",
                getattr(self.config, 'id', None),
                self.base_url,
                self.username,
                bool(getattr(self.config, 'api_token_secret_id', None)),
                bool(getattr(self.config, 'password_secret_id', None)),
                bool(self._auth_header),
            )
        except Exception:
            pass
    
    def _setup_auth(self):
        """Set up authentication headers using either API token or password."""
        auth_credential = None
        
        # Try API token first (preferred)
        if self.config.api_token_secret_id:
            try:
                auth_credential = get_secret(self.config.api_token_secret_id)
                if auth_credential:
                    logger.info("Using API token authentication")
                else:
                    logger.warning(f"Could not retrieve API token for Jenkins config {self.config.id}")
            except Exception as e:
                logger.error(f"Failed to retrieve API token: {e}")
        
        # Fallback to password if no API token
        if not auth_credential and self.config.password_secret_id:
            try:
                auth_credential = get_secret(self.config.password_secret_id)
                if auth_credential:
                    logger.info("Using password authentication")
                else:
                    logger.warning(f"Could not retrieve password for Jenkins config {self.config.id}")
            except Exception as e:
                logger.error(f"Failed to retrieve password: {e}")
        
        # Set up Basic Auth if we have credentials
        if auth_credential:
            try:
                auth_string = f"{self.username}:{auth_credential}"
                auth_bytes = auth_string.encode('ascii')
                auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
                self._auth_header = f"Basic {auth_b64}"
                self._session.headers.update({'Authorization': self._auth_header})
                # Do not log secrets; only log metadata
                logger.debug(f"Authentication header set; user={self.username}, token_len={len(str(auth_credential))}")
            except Exception as e:
                logger.error(f"Failed to setup Jenkins authentication: {e}")
        else:
            # As a last resort, check for direct credentials (fallback for keyring failures)
            fallback_auth = getattr(self.config, '_fallback_password', None) or getattr(self.config, '_fallback_token', None)
            if fallback_auth:
                logger.info("Using fallback authentication")
                try:
                    auth_string = f"{self.username}:{fallback_auth}"
                    auth_bytes = auth_string.encode('ascii')
                    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
                    self._auth_header = f"Basic {auth_b64}"
                    self._session.headers.update({'Authorization': self._auth_header})
                    logger.debug("Fallback authentication header set successfully")
                except Exception as e:
                    logger.error(f"Failed to setup fallback Jenkins authentication: {e}")
            else:
                logger.warning("No valid authentication credentials found for Jenkins")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Jenkins server with detailed error reporting."""
        logger.info(f"Testing connection to Jenkins server: {self.base_url}")
        
        # Validate URL format
        if not self.base_url or not self.base_url.startswith(('http://', 'https://')):
            error_msg = f"Invalid Jenkins URL format: {self.base_url}"
            logger.error(f"URL validation failed: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'error_type': 'INVALID_URL',
                'suggestion': 'URL must start with http:// or https://',
                'url_tested': self.base_url or 'N/A'
            }
        
        # Check if we have authentication configured
        if not self._auth_header and not getattr(self.config, '_fallback_password', None) and not getattr(self.config, '_fallback_token', None):
            error_msg = "No authentication configured - password or API token required"
            logger.error(f"Jenkins auth check failed: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'error_type': 'AUTHENTICATION_MISSING',
                'url_tested': f"{self.base_url.rstrip('/')}/api/json"
            }
        
        try:
            url = f"{self.base_url.rstrip('/')}/api/json"
            logger.info(f"Making request to: {url}")
            dbg_headers = {k: ('<redacted>' if k.lower() == 'authorization' else v) for k, v in self._session.headers.items()}
            logger.debug(f"Session headers: {dbg_headers}")
            response = self._session.get(url)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    result = {
                        'success': True,
                        'version': data.get('version', 'Unknown'),
                        'node_name': data.get('nodeName', 'master'),
                        'num_jobs': len(data.get('jobs', [])),
                        'url_tested': url
                    }
                    logger.info(f"Jenkins connection successful - Version: {result['version']}, Jobs: {result['num_jobs']}")
                    return result
                except json.JSONDecodeError as e:
                    error_msg = f"Invalid JSON response from Jenkins - server may not be Jenkins or may be misconfigured"
                    logger.error(f"JSON decode error: {str(e)}")
                    return {
                        'success': False,
                        'error': error_msg,
                        'error_type': 'INVALID_RESPONSE',
                        'response_preview': response.text[:200] + '...' if len(response.text) > 200 else response.text,
                        'url_tested': url
                    }
            elif response.status_code == 401:
                error_msg = 'Authentication failed - Invalid username or password/API token'
                logger.error(f"Jenkins authentication failed for {self.base_url} - HTTP 401")
                return {
                    'success': False,
                    'error': error_msg,
                    'error_type': 'AUTHENTICATION_FAILED',
                    'suggestion': 'Check your username and password. If using API token, ensure it\'s valid and not expired.',
                    'url_tested': url
                }
            elif response.status_code == 403:
                error_msg = 'Access denied - User lacks required permissions'
                logger.error(f"Jenkins access denied for {self.base_url} - HTTP 403")
                return {
                    'success': False,
                    'error': error_msg,
                    'error_type': 'PERMISSION_DENIED',
                    'suggestion': 'Contact Jenkins administrator to grant API access permissions to your user.',
                    'url_tested': url
                }
            elif response.status_code == 404:
                error_msg = 'Jenkins API not found - Check URL path'
                logger.error(f"Jenkins API not found for {self.base_url} - HTTP 404")
                return {
                    'success': False,
                    'error': error_msg,
                    'error_type': 'URL_NOT_FOUND',
                    'suggestion': f'Verify the Jenkins URL. Tried: {url}',
                    'url_tested': url
                }
            else:
                error_msg = f'HTTP {response.status_code}: {response.reason}'
                logger.error(f"Jenkins connection failed for {self.base_url} - {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'error_type': 'HTTP_ERROR',
                    'status_code': response.status_code,
                    'url_tested': url
                }
                
        except requests.exceptions.SSLError as e:
            error_msg = 'SSL Certificate verification failed'
            ssl_details = str(e)
            logger.error(f"Jenkins SSL error for {self.base_url}: {ssl_details}")
            return {
                'success': False,
                'error': error_msg,
                'error_type': 'SSL_ERROR',
                'details': ssl_details,
                'suggestion': 'This should be fixed now, but if you still see this, the certificate may have other issues.',
                'url_tested': url
            }
        except requests.exceptions.ConnectionError as e:
            connection_details = str(e)
            if "Name or service not known" in connection_details or "nodename nor servname provided" in connection_details:
                error_msg = 'Cannot resolve hostname - Check URL'
                error_type = 'DNS_ERROR'
                suggestion = f'Verify the hostname in URL: {self.base_url}'
            elif "Connection refused" in connection_details:
                error_msg = 'Connection refused - Check URL and port'
                error_type = 'CONNECTION_REFUSED' 
                suggestion = f'Verify Jenkins is running on: {self.base_url}'
            elif "timeout" in connection_details.lower():
                error_msg = 'Network timeout - Check network connectivity'
                error_type = 'NETWORK_TIMEOUT'
                suggestion = 'Check network connection and firewall rules'
            else:
                error_msg = 'Network connection failed'
                error_type = 'CONNECTION_ERROR'
                suggestion = 'Check network connectivity and URL'
            
            logger.error(f"Jenkins connection error for {self.base_url}: {connection_details}")
            return {
                'success': False,
                'error': error_msg,
                'error_type': error_type,
                'details': connection_details,
                'suggestion': suggestion,
                'url_tested': url
            }
        except requests.Timeout as e:
            error_msg = 'Request timeout - Server may be slow or unresponsive'
            logger.error(f"Jenkins timeout for {self.base_url}: {str(e)}")
            return {
                'success': False,
                'error': error_msg,
                'error_type': 'TIMEOUT',
                'suggestion': 'Try again later or check if Jenkins server is overloaded',
                'url_tested': url
            }
        except Exception as e:
            error_msg = f'Unexpected error: {str(e)}'
            logger.error(f"Jenkins connection exception for {self.base_url}: {str(e)}")
            return {
                'success': False,
                'error': error_msg,
                'error_type': 'UNKNOWN_ERROR',
                'details': str(e),
                'url_tested': url
            }
    
    def close(self):
        """Clean up session resources."""
        if hasattr(self, '_session') and self._session:
            self._session.close()
    
    def get_jobs(self, server_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of Jenkins jobs, optionally filtered by server context."""
        try:
            url = f"{self.base_url.rstrip('/')}/api/json?tree=jobs[name,url,color,lastBuild[number,url]]"
            logger.debug(f"Fetching jobs from: {url}")
            response = self._session.get(url)
            response.raise_for_status()
            
            data = response.json()
            jobs = data.get('jobs', [])
            
            # Filter jobs by server if specified
            if server_filter:
                filtered_jobs = []
                for job in jobs:
                    job_name = job.get('name', '').lower()
                    server_filter_lower = server_filter.lower()
                    
                    # Check if server name is in job name or get job config to check parameters
                    if (server_filter_lower in job_name or 
                        self._job_targets_server(job['name'], server_filter)):
                        filtered_jobs.append(job)
                
                return filtered_jobs
            
            return jobs
            
        except Exception as e:
            logger.error(f"Failed to get Jenkins jobs: {e}")
            return []
    
    def _job_targets_server(self, job_name: str, server_filter: str) -> bool:
        """Check if a job targets a specific server by examining its configuration."""
        try:
            # Get job configuration
            job_path = self._build_job_path(job_name)
            url = f"{self.base_url.rstrip('/')}{job_path}/config.xml"
            response = self._session.get(url)
            
            if response.status_code == 200:
                config_xml = response.text
                server_filter_lower = server_filter.lower()
                
                # Look for server references in various places:
                # 1. Ansible inventory file references
                if f"--limit {server_filter_lower}" in config_xml.lower():
                    return True
                if f"--limit={server_filter_lower}" in config_xml.lower():
                    return True
                
                # 2. SSH host parameters
                if f"host={server_filter_lower}" in config_xml.lower():
                    return True
                if f"hostname={server_filter_lower}" in config_xml.lower():
                    return True
                
                # 3. Environment variables
                if server_filter_lower in config_xml.lower():
                    return True
                    
        except Exception as e:
            logger.debug(f"Could not check job config for {job_name}: {e}")
        
        return False

    def _build_job_path(self, job_full_name: str) -> str:
        """Construct Jenkins job path handling folders/multibranch (e.g., /job/a/job/b)."""
        try:
            parts = [p for p in (job_full_name or '').split('/') if p]
            if not parts:
                return ''
            encoded_parts = [quote(p) for p in parts]
            return "/job/" + "/job/".join(encoded_parts)
        except Exception:
            # Fallback to legacy encoding of whole name
            return f"/job/{quote(job_full_name)}"
    
    def get_job_builds(self, job_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent builds for a specific job."""
        try:
            # Build correct Jenkins job path (handles folders)
            job_path = self._build_job_path(job_name)
            tree_param = f"builds[number,url,result,duration,timestamp,id]{{,{limit}}}"
            url = f"{self.base_url.rstrip('/')}{job_path}/api/json?tree={tree_param}"
            
            logger.debug(f"Fetching builds for job '{job_name}' from: {url}")
            response = self._session.get(url)
            response.raise_for_status()
            
            data = response.json()
            builds = data.get('builds', [])
            
            # Convert to our format
            formatted_builds = []
            for build in builds:
                formatted_build = {
                    'job_name': job_name,
                    'build_number': build.get('number'),
                    'status': self._convert_jenkins_result(build.get('result')),
                    'duration': build.get('duration'),  # in milliseconds
                    'started_at': self._convert_jenkins_timestamp(build.get('timestamp')),
                    'jenkins_url': build.get('url'),
                    'console_log_url': build.get('url') + 'console' if build.get('url') else None
                }
                formatted_builds.append(formatted_build)
            
            return formatted_builds
            
        except Exception as e:
            logger.error(f"Failed to get builds for job {job_name}: {e}")
            return []
    
    def get_build_details(self, job_name: str, build_number: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific build."""
        try:
            job_path = self._build_job_path(job_name)
            url = f"{self.base_url.rstrip('/')}{job_path}/{build_number}/api/json"
            
            logger.debug(f"Fetching build details: {url}")
            response = self._session.get(url)
            response.raise_for_status()
            
            build_data = response.json()
            
            # Extract parameters to identify target server
            target_server = self._extract_target_server(build_data)
            
            return {
                'job_name': job_name,
                'build_number': build_number,
                'status': self._convert_jenkins_result(build_data.get('result')),
                'duration': build_data.get('duration'),
                'started_at': self._convert_jenkins_timestamp(build_data.get('timestamp')),
                'jenkins_url': build_data.get('url'),
                'console_log_url': build_data.get('url') + 'console' if build_data.get('url') else None,
                'target_server': target_server,
                'description': build_data.get('description'),
                'building': build_data.get('building', False)
            }
            
        except Exception as e:
            logger.error(f"Failed to get build details for {job_name}#{build_number}: {e}")
            return None
    
    def get_console_log(self, job_name: str, build_number: int, 
                       start_offset: int = 0, max_lines: int = 1000) -> Tuple[str, bool]:
        """
        Get console log for a build.
        
        Returns:
            Tuple of (log_text, has_more_data)
        """
        try:
            job_path = self._build_job_path(job_name)
            
            # Use progressive text API for better performance
            if start_offset > 0:
                url = f"{self.base_url.rstrip('/')}{job_path}/{build_number}/logText/progressiveText"
                params = {'start': start_offset}
            else:
                url = f"{self.base_url.rstrip('/')}{job_path}/{build_number}/consoleText"
                params = {}
            
            # Log auth/header presence without leaking secrets
            try:
                dbg_headers = {k: ('<redacted>' if k.lower() == 'authorization' else v) for k, v in self._session.headers.items()}
                logger.info(
                    "Fetching console log: config_id=%s job=%s build=%s url=%s start_offset=%s max_lines=%s auth_present=%s",
                    getattr(self.config, 'id', None), job_name, build_number, url, start_offset, max_lines, bool(self._auth_header)
                )
                logger.debug(f"Session headers: {dbg_headers}")
            except Exception:
                pass
            
            response = self._session.get(url, params=params)
            
            if response.status_code in (401, 403):
                logger.error(
                    "Authorization error fetching console log: status=%s reason=%s config_id=%s user=%s auth_present=%s url=%s",
                    response.status_code, response.reason, getattr(self.config, 'id', None), self.username, bool(self._auth_header), url
                )
            
            response.raise_for_status()
            
            log_text = response.text
            
            # Check if there's more data (for progressive loading)
            has_more = response.headers.get('X-More-Data') == 'true'
            
            # Limit lines if specified
            if max_lines > 0:
                lines = log_text.split('\n')
                if len(lines) > max_lines:
                    log_text = '\n'.join(lines[-max_lines:])
                    has_more = True
            
            return log_text, has_more
            
        except requests.HTTPError as e:
            status = getattr(e.response, 'status_code', 'N/A') if hasattr(e, 'response') and e.response is not None else 'N/A'
            reason = getattr(e.response, 'reason', '') if hasattr(e, 'response') and e.response is not None else ''
            preview = ''
            try:
                if hasattr(e, 'response') and e.response is not None:
                    text = e.response.text or ''
                    preview = text[:200] + ('...' if len(text) > 200 else '')
            except Exception:
                pass
            logger.error(
                "HTTP error fetching console log for %s#%s: status=%s reason=%s auth_present=%s preview=%s",
                job_name, build_number, status, reason, bool(self._auth_header), preview
            )
            return "", False
        except Exception as e:
            logger.error(f"Failed to get console log for {job_name}#{build_number}: {e}")
            return "", False
    
    def get_console_log_tail(self, job_name: str, build_number: int, 
                            lines: int = 100) -> str:
        """Get the last N lines of console log for error analysis."""
        try:
            logger.info(
                "Fetching console log tail: config_id=%s job=%s build=%s lines=%s auth_present=%s",
                getattr(self.config, 'id', None), job_name, build_number, lines, bool(self._auth_header)
            )
            log_text, _ = self.get_console_log(job_name, build_number, max_lines=lines)
            return log_text
        except Exception as e:
            logger.error(f"Failed to get console log tail: {e}")
            return ""
    
    def fetch_and_store_builds(self, server_name: Optional[str] = None, 
                              limit: int = 20) -> List[BuildLog]:
        """Fetch builds from Jenkins and store them in the database."""
        logger.info(f"Fetching builds from Jenkins for server: {server_name or 'all'}, limit: {limit}")
        stored_builds = []
        
        try:
            # Get jobs filtered by server
            logger.debug(f"Getting jobs from Jenkins with server filter: {server_name}")
            jobs = self.get_jobs(server_filter=server_name)
            logger.info(f"Found {len(jobs)} jobs matching filter criteria")
            
            for job in jobs:
                job_name = job.get('name')
                if not job_name:
                    logger.warning(f"Skipping job with no name: {job}")
                    continue
                
                logger.debug(f"Processing job: {job_name}")
                # Get recent builds for this job
                builds = self.get_job_builds(job_name, limit=limit)
                logger.debug(f"Found {len(builds)} builds for job {job_name}")
                
                for build_data in builds:
                    # Get detailed build info to determine target server
                    build_details = self.get_build_details(
                        job_name, build_data['build_number']
                    )
                    
                    if build_details:
                        # Create BuildLog instance
                        build_log = BuildLog(
                            job_name=build_details['job_name'],
                            build_number=build_details['build_number'],
                            status=build_details['status'],
                            duration=build_details.get('duration'),
                            started_at=build_details.get('started_at'),
                            jenkins_url=build_details.get('jenkins_url'),
                            target_server=build_details.get('target_server', server_name),
                            console_log_url=build_details.get('console_log_url')
                        )
                        
                        # Save to database
                        build_log.save()
                        stored_builds.append(build_log)
                        
                        logger.debug(f"Stored build: {job_name}#{build_details['build_number']}")
            
            # Update last sync time
            self.config.last_sync = datetime.now(timezone.utc)
            self.config.save()
            
            logger.info(f"Fetched and stored {len(stored_builds)} builds for server: {server_name}")
            return stored_builds
            
        except Exception as e:
            logger.error(f"Failed to fetch and store builds: {e}")
            return stored_builds
    
    def _convert_jenkins_result(self, result: Optional[str]) -> str:
        """Convert Jenkins result to our standard format."""
        if not result:
            return 'BUILDING'
        
        # Map Jenkins results to our format
        result_map = {
            'SUCCESS': 'SUCCESS',
            'FAILURE': 'FAILURE',  
            'ABORTED': 'ABORTED',
            'UNSTABLE': 'UNSTABLE',
            'NOT_BUILT': 'NOT_BUILT'
        }
        
        return result_map.get(result.upper(), result.upper())
    
    def _convert_jenkins_timestamp(self, timestamp: Optional[int]) -> Optional[datetime]:
        """Convert Jenkins timestamp (milliseconds) to datetime."""
        if timestamp:
            try:
                return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            except (ValueError, OSError):
                pass
        return None
    
    def _extract_target_server(self, build_data: Dict[str, Any]) -> Optional[str]:
        """Extract target server from build parameters or actions."""
        try:
            # Look in build parameters
            actions = build_data.get('actions', [])
            
            for action in actions:
                if action.get('_class') == 'hudson.model.ParametersAction':
                    parameters = action.get('parameters', [])
                    
                    for param in parameters:
                        param_name = param.get('name', '').lower()
                        param_value = param.get('value', '')
                        
                        # Common parameter names for target servers
                        if param_name in ['server', 'host', 'hostname', 'target', 'target_host']:
                            return param_value
                        
                        # Ansible limit parameter
                        if param_name in ['limit', 'ansible_limit']:
                            return param_value
                        
                        # Environment parameter that might contain server info
                        if param_name in ['environment', 'env'] and param_value:
                            # Try to extract server from environment string
                            server_match = re.search(r'server[=:](\w+)', param_value.lower())
                            if server_match:
                                return server_match.group(1)
            
            # If no explicit parameter, try to extract from build description
            description = build_data.get('description', '')
            if description:
                server_match = re.search(r'server[:\s]+(\w+)', description.lower())
                if server_match:
                    return server_match.group(1)
                    
        except Exception as e:
            logger.debug(f"Could not extract target server from build data: {e}")
        
        return None
    
    def close(self):
        """Close the session."""
        if self._session:
            self._session.close()


def create_jenkins_service(config_id: int) -> Optional[JenkinsService]:
    """Create a Jenkins service instance from a stored configuration."""
    try:
        config = JenkinsConfig.get_by_id(config_id)
        if config:
            return JenkinsService(config)
        else:
            logger.error(f"Jenkins config {config_id} not found")
            return None
    except Exception as e:
        logger.error(f"Failed to create Jenkins service: {e}")
        return None