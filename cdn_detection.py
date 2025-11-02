#!/usr/bin/env python3
"""
Enhanced CDN Identification Tool
Uses dig, whois, and multiple detection methods to identify CDN providers
"""

import subprocess
import requests
import json
import re
from typing import Dict, List, Optional, Tuple
import socket
import time

class EnhancedCDNIdentifier:
    def __init__(self, domains: List[str]):
        self.domains = domains
        self.results = {}
        
        # Enhanced CDN detection patterns
        self.cdn_patterns = {
            'Cloudflare': {
                'cname': ['cloudflare', 'cloudflare.net'],
                'headers': ['cf-ray', 'cf-cache-status', '__cfduid'],
                'server': ['cloudflare'],
                'asn': ['AS13335'],
                'org': ['cloudflare']
            },
            'Fastly': {
                'cname': ['fastly', 'fastly.net', 'fastlylb.net'],
                'headers': ['x-fastly', 'x-served-by', 'fastly-'],
                'server': ['fastly'],
                'asn': ['AS54113'],
                'org': ['fastly'],
                'hostname': ['fastly']
            },
            'Akamai': {
                'cname': ['akamai', 'akamaiedge', 'edgesuite.net', 'edgekey.net', 'akamaized.net'],
                'headers': ['x-akamai', 'akamai-'],
                'asn': ['AS20940', 'AS16625'],
                'org': ['akamai'],
                'hostname': ['akamai']
            },
            'AWS CloudFront': {
                'cname': ['cloudfront', 'cloudfront.net'],
                'headers': ['x-amz-cf-id', 'x-amz-cf-pop', 'via: cloudfront'],
                'asn': ['AS16509'],
                'org': ['amazon']
            },
            'Google Cloud CDN': {
                'cname': ['1e100.net', 'googleusercontent', 'google.'],
                'headers': ['alt-svc: h3'],
                'server': ['gws', 'gfe', 'sffe'],
                'asn': ['AS15169'],
                'org': ['google'],
                'hostname': ['1e100']
            },
            'Azure CDN': {
                'cname': ['azureedge', 'azure', 'msecnd.net'],
                'headers': ['x-azure', 'x-msedge'],
                'asn': ['AS8075'],
                'org': ['microsoft']
            },
            'Facebook CDN': {
                'server': ['proxygen'],
                'asn': ['AS32934', 'AS63293'],
                'org': ['facebook', 'meta'],
                'hostname': ['facebook', 'fbcdn']
            }
        }
    
    def run_command(self, cmd: List[str], timeout: int = 5) -> str:
        """Run shell command and return output"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout.strip()
        except Exception as e:
            return ""
    
    def check_cname_chain(self, domain: str) -> List[str]:
        """Follow the complete CNAME chain"""
        cname_chain = []
        current = domain
        visited = set()
        
        while current and current not in visited and len(cname_chain) < 10:
            visited.add(current)
            
            output = self.run_command(['dig', current, 'CNAME', '+short'])
            if output:
                cnames = [line.strip().rstrip('.') for line in output.split('\n') if line.strip()]
                if cnames:
                    cname_chain.extend(cnames)
                    current = cnames[0]
                else:
                    break
            else:
                break
        
        return cname_chain
    
    def get_a_records(self, domain: str) -> List[str]:
        """Get A records"""
        output = self.run_command(['dig', domain, 'A', '+short'])
        ips = [line.strip() for line in output.split('\n') 
               if line.strip() and re.match(r'^\d+\.\d+\.\d+\.\d+$', line.strip())]
        return ips
    
    def get_reverse_dns(self, ip: str) -> str:
        """Get reverse DNS hostname"""
        try:
            return socket.gethostbyaddr(ip)[0]
        except:
            # Try using dig
            output = self.run_command(['dig', '+short', '-x', ip])
            if output:
                return output.rstrip('.')
            return ""
    
    def get_whois_info(self, ip: str) -> Dict[str, str]:
        """Get comprehensive whois information"""
        info = {
            'asn': '',
            'org': '',
            'country': ''
        }
        
        output = self.run_command(['whois', ip], timeout=10)
        if not output:
            return info
        
        # Extract ASN
        asn_patterns = [
            r'origin(?:as)?:\s*as(\d+)',
            r'(?:^|\s)as(\d+)',
            r'asn:\s*(\d+)'
        ]
        for pattern in asn_patterns:
            match = re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
            if match:
                info['asn'] = f"AS{match.group(1)}"
                break
        
        # Extract organization
        org_patterns = [
            r'org(?:name)?:\s*(.+)',
            r'organization:\s*(.+)',
            r'descr:\s*(.+)',
            r'netname:\s*(.+)'
        ]
        for pattern in org_patterns:
            match = re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
            if match:
                org = match.group(1).strip()
                if org and len(org) > 2 and not org.startswith('#'):
                    info['org'] = org
                    break
        
        # Extract country
        country_match = re.search(r'country:\s*([A-Z]{2})', output, re.IGNORECASE | re.MULTILINE)
        if country_match:
            info['country'] = country_match.group(1).upper()
        
        return info
    
    def get_http_headers(self, domain: str) -> Dict[str, str]:
        """Get HTTP headers"""
        headers = {}
        
        for protocol in ['https', 'http']:
            try:
                url = f'{protocol}://{domain}'
                response = requests.get(
                    url,
                    timeout=10,
                    allow_redirects=True,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
                    verify=False
                )
                
                # Collect all headers (lowercase keys)
                for key, value in response.headers.items():
                    headers[key.lower()] = value
                
                return headers
                
            except:
                continue
        
        return headers
    
    def match_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if any pattern matches the text"""
        if not text:
            return False
        text_lower = text.lower()
        return any(pattern.lower() in text_lower for pattern in patterns)
    
    def detect_cdn(self, domain: str) -> Dict:
        """Comprehensive CDN detection"""
        print(f"\n{'='*100}")
        print(f"Analyzing: {domain}")
        print(f"{'='*100}")
        
        detection_results = []
        evidence = []
        
        # 1. Check CNAME chain
        print("1. Checking CNAME records...")
        cname_chain = self.check_cname_chain(domain)
        if cname_chain:
            print(f"   CNAME chain: {' -> '.join(cname_chain)}")
            for cdn_name, patterns in self.cdn_patterns.items():
                if self.match_patterns(' '.join(cname_chain), patterns.get('cname', [])):
                    detection_results.append(cdn_name)
                    evidence.append(f"CNAME points to {cdn_name}: {cname_chain[0]}")
                    print(f"   ✓ Detected {cdn_name} from CNAME")
        else:
            print("   No CNAME records")
        
        # 2. Check A records and reverse DNS
        print("\n2. Checking A records and reverse DNS...")
        ips = self.get_a_records(domain)
        hostnames = []
        
        if ips:
            print(f"   IPs: {', '.join(ips[:3])}")
            
            # Check first IP
            if ips:
                hostname = self.get_reverse_dns(ips[0])
                if hostname:
                    hostnames.append(hostname)
                    print(f"   Reverse DNS: {hostname}")
                    
                    for cdn_name, patterns in self.cdn_patterns.items():
                        if self.match_patterns(hostname, patterns.get('hostname', [])):
                            if cdn_name not in detection_results:
                                detection_results.append(cdn_name)
                            evidence.append(f"Hostname indicates {cdn_name}: {hostname}")
                            print(f"   ✓ Detected {cdn_name} from hostname")
        
        # 3. Check WHOIS
        print("\n3. Checking WHOIS information...")
        whois_info = {}
        if ips:
            whois_info = self.get_whois_info(ips[0])
            if whois_info['asn']:
                print(f"   ASN: {whois_info['asn']}")
            if whois_info['org']:
                print(f"   Organization: {whois_info['org']}")
            
            # Match ASN
            for cdn_name, patterns in self.cdn_patterns.items():
                if whois_info['asn'] in patterns.get('asn', []):
                    if cdn_name not in detection_results:
                        detection_results.append(cdn_name)
                    evidence.append(f"ASN {whois_info['asn']} belongs to {cdn_name}")
                    print(f"   ✓ Detected {cdn_name} from ASN")
            
            # Match organization
            for cdn_name, patterns in self.cdn_patterns.items():
                if self.match_patterns(whois_info['org'], patterns.get('org', [])):
                    if cdn_name not in detection_results:
                        detection_results.append(cdn_name)
                    evidence.append(f"Organization matches {cdn_name}: {whois_info['org']}")
                    print(f"   ✓ Detected {cdn_name} from organization")
        
        # 4. Check HTTP headers
        print("\n4. Checking HTTP headers...")
        headers = self.get_http_headers(domain)
        
        if headers:
            # Check server header
            if 'server' in headers:
                print(f"   Server: {headers['server']}")
                for cdn_name, patterns in self.cdn_patterns.items():
                    if self.match_patterns(headers['server'], patterns.get('server', [])):
                        if cdn_name not in detection_results:
                            detection_results.append(cdn_name)
                        evidence.append(f"Server header: {headers['server']}")
                        print(f"   ✓ Detected {cdn_name} from Server header")
            
            # Check CDN-specific headers
            cdn_headers_found = []
            for key, value in headers.items():
                if any(x in key for x in ['cf-', 'x-fastly', 'x-amz-cf', 'x-akamai', 'x-cache']):
                    cdn_headers_found.append(f"{key}: {value[:50]}")
            
            if cdn_headers_found:
                print(f"   CDN headers: {len(cdn_headers_found)}")
                for header in cdn_headers_found[:3]:
                    print(f"     - {header}")
            
            # Match header patterns
            headers_str = ' '.join([f"{k}:{v}" for k, v in headers.items()])
            for cdn_name, patterns in self.cdn_patterns.items():
                if self.match_patterns(headers_str, patterns.get('headers', [])):
                    if cdn_name not in detection_results:
                        detection_results.append(cdn_name)
                    evidence.append(f"HTTP headers indicate {cdn_name}")
                    print(f"   ✓ Detected {cdn_name} from HTTP headers")
        
        # Final result
        result = {
            'domain': domain,
            'uses_cdn': len(detection_results) > 0,
            'cdn_provider': detection_results[0] if detection_results else 'No CDN detected',
            'all_detected': detection_results,
            'evidence': evidence,
            'cname_chain': cname_chain,
            'ips': ips[:3],
            'hostnames': hostnames,
            'whois': whois_info,
            'has_cdn_headers': bool(headers and any('cf-' in k or 'x-fastly' in k or 'x-akamai' in k for k in headers.keys()))
        }
        
        print(f"\n{'─'*100}")
        if result['uses_cdn']:
            print(f"✓ CDN Detected: {result['cdn_provider']}")
            if len(detection_results) > 1:
                print(f"  Other detections: {', '.join(detection_results[1:])}")
        else:
            print("✗ No CDN detected (might be self-hosted or using proprietary CDN)")
        print(f"{'─'*100}")
        
        time.sleep(0.5)  # Rate limiting
        
        return result
    
    def analyze_all(self):
        """Analyze all domains"""
        for domain in self.domains:
            result = self.detect_cdn(domain)
            self.results[domain] = result
    
    def print_summary(self):
        """Print summary table"""
        print("\n" + "="*100)
        print("CDN IDENTIFICATION SUMMARY")
        print("="*100)
        print(f"{'Domain':<25} {'Uses CDN':<12} {'CDN Provider':<30} {'Evidence Count':<15}")
        print("-"*100)
        
        for domain, result in self.results.items():
            uses_cdn = 'Yes' if result['uses_cdn'] else 'No'
            provider = result['cdn_provider']
            evidence = len(result['evidence'])
            
            print(f"{domain:<25} {uses_cdn:<12} {provider:<30} {evidence:<15}")
    
    def print_detailed_report(self):
        """Print detailed report"""
        print("\n" + "="*100)
        print("DETAILED REPORT")
        print("="*100)
        
        for domain, result in self.results.items():
            print(f"\n{'─'*100}")
            print(f"Domain: {domain}")
            print(f"{'─'*100}")
            print(f"Uses CDN: {'Yes' if result['uses_cdn'] else 'No'}")
            print(f"CDN Provider: {result['cdn_provider']}")
            
            if result['all_detected'] and len(result['all_detected']) > 1:
                print(f"All Detections: {', '.join(result['all_detected'])}")
            
            if result['evidence']:
                print(f"\nEvidence ({len(result['evidence'])} items):")
                for i, ev in enumerate(result['evidence'], 1):
                    print(f"  {i}. {ev}")
            
            if result['cname_chain']:
                print(f"\nCNAME Chain:")
                print(f"  {domain} → {' → '.join(result['cname_chain'])}")
            
            if result['ips']:
                print(f"\nIP Addresses:")
                for ip in result['ips']:
                    print(f"  - {ip}")
            
            if result['hostnames']:
                print(f"\nReverse DNS:")
                for hostname in result['hostnames']:
                    print(f"  - {hostname}")
            
            if result['whois'].get('asn') or result['whois'].get('org'):
                print(f"\nWHOIS Info:")
                if result['whois'].get('asn'):
                    print(f"  ASN: {result['whois']['asn']}")
                if result['whois'].get('org'):
                    print(f"  Organization: {result['whois']['org']}")
                if result['whois'].get('country'):
                    print(f"  Country: {result['whois']['country']}")
    
    def save_to_json(self, filename: str = 'cdn_identification_enhanced.json'):
        """Save to JSON"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n\nResults saved to {filename}")

def main():
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
    
    print("="*100)
    print("ENHANCED CDN IDENTIFICATION TOOL")
    print("Using dig, whois, and comprehensive pattern matching")
    print("="*100)
    
    identifier = EnhancedCDNIdentifier(domains)
    identifier.analyze_all()
    identifier.print_summary()
    identifier.print_detailed_report()
    identifier.save_to_json()
    
    print("\n" + "="*100)
    print("Analysis Complete!")
    print("="*100)

if __name__ == "__main__":
    main()