#!/usr/bin/env python3
"""
Enhanced Backend Server Detection Script
Detects web server software and technologies with improved error handling
"""

import requests
import json
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import time

class EnhancedBackendDetector:
    def __init__(self, domains: List[str]):
        self.domains = domains
        self.results = {}
        
        # Enhanced server patterns
        self.server_patterns = {
            'nginx': ['nginx'],
            'Apache': ['apache'],
            'LiteSpeed': ['litespeed'],
            'Microsoft-IIS': ['microsoft-iis', 'iis'],
            'Cloudflare': ['cloudflare'],
            'Google Web Server': ['gws', 'gfe'],
            'Caddy': ['caddy'],
            'Tomcat': ['tomcat'],
            'Jetty': ['jetty'],
            'OpenResty': ['openresty'],
            'Tengine': ['tengine'],
        }
        
        # Patterns for detecting servers that hide their identity
        self.hidden_server_patterns = {
            'Facebook (Proxygen)': {
                'headers': ['x-fb-debug', 'x-fb-connection-quality', 'x-fb-request-id'],
                'domain': ['facebook.com', 'fb.com']
            },
            'GitHub': {
                'headers': ['x-github-request-id', 'x-github-backend'],
                'domain': ['github.com'],
                'content': ['github.githubassets.com']
            },
            'Twitter': {
                'headers': ['x-twitter-', 'x-transaction-id'],
                'domain': ['twitter.com', 'x.com']
            }
        }
    
    def detect_server_from_headers(self, domain: str) -> Dict:
        """Detect server with enhanced error handling and retry logic"""
        result = {
            'domain': domain,
            'server': 'Unknown',
            'headers': {},
            'technologies': [],
            'status_code': None,
            'final_url': None,
            'protocol': None,
            'detection_method': None
        }
        
        # Try multiple approaches
        protocols = ['https', 'http']
        success = False
        
        for protocol in protocols:
            if success:
                break
                
            # Try with different timeout and retry settings
            attempts = [
                {'timeout': 15, 'verify': True},
                {'timeout': 20, 'verify': False},  # Ignore SSL errors
                {'timeout': 30, 'verify': False}   # Last resort with longer timeout
            ]
            
            for attempt_config in attempts:
                try:
                    url = f'{protocol}://{domain}'
                    
                    # Use more realistic headers
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1'
                    }
                    
                    response = requests.get(
                        url,
                        timeout=attempt_config['timeout'],
                        allow_redirects=True,
                        headers=headers,
                        verify=attempt_config['verify']
                    )
                    
                    result['status_code'] = response.status_code
                    result['final_url'] = response.url
                    result['protocol'] = protocol
                    
                    # Collect ALL headers (not just selected ones)
                    result['headers'] = dict(response.headers)
                    
                    # Step 1: Check for standard Server header
                    if 'server' in response.headers:
                        server_header = response.headers['server']
                        result['server_header_raw'] = server_header
                        result['server'] = self.identify_server_from_header(server_header)
                        result['detection_method'] = 'Server header'
                    
                    # Step 2: Check for hidden server patterns (Facebook, GitHub, etc.)
                    if result['server'] == 'Unknown':
                        hidden_server = self.detect_hidden_server(response, domain)
                        if hidden_server:
                            result['server'] = hidden_server
                            result['detection_method'] = 'Header fingerprint'
                    
                    # Step 3: Detect additional technologies
                    result['technologies'] = self.detect_technologies(response)
                    
                    success = True
                    break  # Success, exit retry loop
                    
                except requests.exceptions.SSLError as e:
                    if protocol == 'https' and attempt_config['verify']:
                        continue  # Try without SSL verification
                    else:
                        result['error'] = f'SSL Error: {str(e)[:100]}'
                        
                except requests.exceptions.Timeout:
                    result['error'] = 'Connection timeout'
                    continue  # Try next configuration
                    
                except requests.exceptions.ConnectionError as e:
                    result['error'] = f'Connection error: {str(e)[:100]}'
                    if 'RemoteDisconnected' in str(e):
                        continue  # Try next configuration
                    break  # Don't retry for other connection errors
                    
                except requests.exceptions.RequestException as e:
                    result['error'] = f'Request error: {str(e)[:100]}'
                    continue
                    
                except Exception as e:
                    result['error'] = f'Unexpected error: {str(e)[:100]}'
                    break
        
        return result
    
    def identify_server_from_header(self, server_header: str) -> str:
        """Identify server software from Server header"""
        server_lower = server_header.lower()
        
        for server_name, patterns in self.server_patterns.items():
            for pattern in patterns:
                if pattern in server_lower:
                    return server_name
        
        # If no pattern matches, return the raw header (cleaned up)
        return server_header
    
    def detect_hidden_server(self, response, domain: str) -> Optional[str]:
        """Detect servers that hide their identity using fingerprinting"""
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        content = response.text[:5000].lower() if hasattr(response, 'text') else ''
        
        for server_name, patterns in self.hidden_server_patterns.items():
            # Check domain match
            if 'domain' in patterns:
                if any(d in domain for d in patterns['domain']):
                    # Check for characteristic headers
                    if 'headers' in patterns:
                        header_matches = sum(1 for h in patterns['headers'] 
                                           if any(h.lower() in key for key in headers_lower.keys()))
                        if header_matches >= 1:  # At least one header match
                            return server_name
            
            # Check content patterns
            if 'content' in patterns:
                if any(p in content for p in patterns['content']):
                    return server_name
        
        return None
    
    def detect_technologies(self, response) -> List[str]:
        """Detect additional technologies from response"""
        technologies = []
        headers = response.headers
        
        # Check X-Powered-By
        if 'x-powered-by' in headers:
            tech = headers['x-powered-by']
            technologies.append(f"Powered by: {tech}")
        
        # Check for framework indicators in headers
        framework_headers = {
            'x-aspnet-version': 'ASP.NET',
            'x-aspnetmvc-version': 'ASP.NET MVC',
            'x-drupal-cache': 'Drupal',
            'x-generator': 'Generator'
        }
        
        for header, tech_name in framework_headers.items():
            if header in headers:
                technologies.append(f"{tech_name}: {headers[header]}")
        
        # Check content for CMS/framework (limit to first 10KB)
        try:
            content = response.text[:10000].lower()
            
            cms_indicators = {
                'WordPress': ['wp-content', 'wp-includes', '/wp-json/'],
                'Drupal': ['drupal', '/sites/default/'],
                'Joomla': ['joomla', '/components/com_'],
                'Django': ['csrfmiddlewaretoken', '__admin__'],
                'Laravel': ['laravel', 'laravel_session'],
                'React': ['react-root', '__react', 'data-reactroot'],
                'Vue.js': ['data-v-', 'vue-'],
                'Angular': ['ng-version', 'ng-app', '_nghost-'],
                'Next.js': ['__next', '_next/static'],
            }
            
            for tech, indicators in cms_indicators.items():
                if any(ind in content for ind in indicators):
                    if f"Framework/CMS: {tech}" not in technologies:
                        technologies.append(f"Framework/CMS: {tech}")
        except:
            pass
        
        return technologies
    
    def analyze_all(self):
        """Analyze all domains"""
        for i, domain in enumerate(self.domains, 1):
            print(f"\n[{i}/{len(self.domains)}] Analyzing {domain}...")
            result = self.detect_server_from_headers(domain)
            self.results[domain] = result
            
            # Show result immediately
            if 'error' in result:
                print(f"  ✗ {result['error']}")
            else:
                print(f"  ✓ Server: {result['server']}")
                if result['status_code']:
                    print(f"  ✓ Status: {result['status_code']}")
            
            # Small delay to be polite
            time.sleep(0.5)
    
    def print_results(self):
        """Print detailed results"""
        print("\n" + "="*120)
        print("BACKEND SERVER DETECTION RESULTS")
        print("="*120)
        
        for domain, result in self.results.items():
            print(f"\n{'='*120}")
            print(f"Domain: {result['domain']}")
            print(f"{'='*120}")
            
            if 'error' in result:
                print(f"Status: ERROR")
                print(f"Error: {result['error']}")
                
                # Show any partial information we got
                if result.get('server') and result['server'] != 'Unknown':
                    print(f"Server (partial): {result['server']}")
            else:
                print(f"Server: {result['server']}")
                print(f"Detection Method: {result.get('detection_method', 'N/A')}")
                print(f"Protocol: {result.get('protocol', 'N/A')}")
                print(f"Status Code: {result.get('status_code', 'N/A')}")
                
                if 'final_url' in result and result['final_url'] != f"https://{domain}" and result['final_url'] != f"http://{domain}":
                    print(f"Redirected to: {result['final_url']}")
                
                if 'server_header_raw' in result:
                    print(f"Server Header: {result['server_header_raw']}")
                
                if result['technologies']:
                    print(f"\nDetected Technologies:")
                    for tech in result['technologies'][:5]:  # Limit to 5
                        print(f"  - {tech}")
    
    def generate_comparison_table(self):
        """Generate a comparison table"""
        print("\n" + "="*120)
        print("SERVER TECHNOLOGY COMPARISON TABLE")
        print("="*120)
        print(f"{'Domain':<30} {'Server':<25} {'Status':<10} {'Detection Method':<30}")
        print("-"*120)
        
        for domain, result in self.results.items():
            if 'error' in result:
                status = 'ERROR'
                server = result.get('server', 'Unknown')
                method = result['error'][:28]
            else:
                server = result.get('server', 'Unknown')[:24]
                status = str(result.get('status_code', 'N/A'))
                method = result.get('detection_method', 'N/A')[:28]
            
            print(f"{domain:<30} {server:<25} {status:<10} {method:<30}")
    
    def save_to_json(self, filename: str = 'backend_server_results_enhanced.json'):
        """Save results to JSON"""
        # Create a cleaner version for JSON (remove full headers)
        clean_results = {}
        for domain, result in self.results.items():
            clean_result = result.copy()
            # Only keep important headers
            if 'headers' in clean_result:
                important_headers = ['server', 'x-powered-by', 'x-aspnet-version']
                clean_result['important_headers'] = {
                    k: v for k, v in clean_result['headers'].items() 
                    if k.lower() in important_headers
                }
                del clean_result['headers']  # Remove full headers to reduce size
            clean_results[domain] = clean_result
        
        with open(filename, 'w') as f:
            json.dump(clean_results, f, indent=2)
        print(f"\n\nResults saved to {filename}")
    
    def generate_statistics(self):
        """Generate statistics about server usage"""
        print("\n" + "="*120)
        print("SERVER USAGE STATISTICS")
        print("="*120)
        
        server_counts = {}
        successful_detections = 0
        
        for domain, result in self.results.items():
            if 'error' not in result or result.get('server') != 'Unknown':
                server = result.get('server', 'Unknown')
                server_counts[server] = server_counts.get(server, 0) + 1
                if result.get('server') != 'Unknown':
                    successful_detections += 1
        
        total = len(self.domains)
        
        print(f"\nTotal domains analyzed: {total}")
        print(f"Successful detections: {successful_detections} ({successful_detections/total*100:.1f}%)")
        print(f"Failed detections: {total - successful_detections}")
        
        print("\nServer Distribution:")
        for server, count in sorted(server_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total) * 100
            print(f"  - {server}: {count} ({percentage:.1f}%)")

def main():
    # Suppress SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    domains = [
        'google.com',
        'youtube.com',
        'facebook.com',
        'cool.ntu.edu.tw',
        'linkedin.com',
        'claude.ai',
        'github.com',
        'www.ntu.edu.tw',
        'ntu.im',
        'chatgpt.com'
    ]
    
    print("="*120)
    print("ENHANCED BACKEND SERVER DETECTION TOOL")
    print("="*120)
    print(f"Detecting backend server technologies for {len(domains)} domains...")
    print("Using improved error handling and server fingerprinting")
    
    detector = EnhancedBackendDetector(domains)
    detector.analyze_all()
    detector.print_results()
    detector.generate_comparison_table()
    detector.generate_statistics()
    detector.save_to_json()
    
    print("\n" + "="*120)
    print("Analysis complete!")
    print("="*120)

if __name__ == "__main__":
    main()