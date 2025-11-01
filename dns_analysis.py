#!/usr/bin/env python3
"""
DNS Analysis Script for Modern Internet Infrastructure Investigation
This script queries DNS records for multiple domains and collects:
- A/AAAA records (IP addresses)
- CNAME records (Canonical names)
- MX records (Mail servers)
- DNSSEC status
"""

import dns.resolver
import dns.dnssec
import subprocess
import json
import sys
from typing import Dict, List, Any
import time

class DNSAnalyzer:
    def __init__(self, domains: List[str]):
        self.domains = domains
        self.results = []
    
    def query_a_records(self, domain: str) -> List[str]:
        """Query A records (IPv4 addresses)"""
        try:
            answers = dns.resolver.resolve(domain, 'A')
            return [str(rdata) for rdata in answers]
        except Exception as e:
            return []
    
    def query_aaaa_records(self, domain: str) -> List[str]:
        """Query AAAA records (IPv6 addresses)"""
        try:
            answers = dns.resolver.resolve(domain, 'AAAA')
            return [str(rdata) for rdata in answers]
        except Exception as e:
            return []
    
    def query_cname_records(self, domain: str) -> List[str]:
        """Query CNAME records"""
        try:
            answers = dns.resolver.resolve(domain, 'CNAME')
            return [str(rdata) for rdata in answers]
        except Exception as e:
            return []
    
    def query_mx_records(self, domain: str) -> List[Dict[str, Any]]:
        """Query MX records (Mail servers)"""
        try:
            answers = dns.resolver.resolve(domain, 'MX')
            return [{'preference': rdata.preference, 'exchange': str(rdata.exchange)} 
                    for rdata in answers]
        except Exception as e:
            return []
    
    def check_dnssec(self, domain: str) -> Dict[str, Any]:
        """Check DNSSEC status using dig command"""
        try:
            # Use dig to check for DNSSEC
            result = subprocess.run(
                ['dig', '+dnssec', domain, 'A'],
                capture_output=True,
                text=True,
                timeout=10
            )
            output = result.stdout
            
            has_rrsig = 'RRSIG' in output
            has_ad_flag = 'ad' in output.lower()
            
            return {
                'enabled': has_rrsig,
                'authenticated': has_ad_flag,
                'status': 'Enabled' if has_rrsig else 'Disabled'
            }
        except Exception as e:
            return {'enabled': False, 'authenticated': False, 'status': 'Unknown', 'error': str(e)}
    
    def trace_dns_lookup(self, domain: str) -> List[str]:
        """Trace the DNS lookup path"""
        path = []
        current = domain
        visited = set()
        
        try:
            # Follow CNAME chain
            while current and current not in visited:
                visited.add(current)
                path.append(current)
                
                try:
                    cname_answers = dns.resolver.resolve(current, 'CNAME')
                    current = str(cname_answers[0].target).rstrip('.')
                except:
                    # No more CNAMEs, we've reached the end
                    break
            
            return path
        except Exception as e:
            return [domain]
    
    def analyze_domain(self, domain: str) -> Dict[str, Any]:
        """Analyze a single domain"""
        print(f"Analyzing {domain}...")
        
        result = {
            'domain': domain,
            'a_records': self.query_a_records(domain),
            'aaaa_records': self.query_aaaa_records(domain),
            'cname_records': self.query_cname_records(domain),
            'mx_records': self.query_mx_records(domain),
            'dnssec': self.check_dnssec(domain),
            'dns_lookup_path': self.trace_dns_lookup(domain)
        }
        
        return result
    
    def analyze_all(self):
        """Analyze all domains"""
        for domain in self.domains:
            try:
                result = self.analyze_domain(domain)
                self.results.append(result)
                time.sleep(0.5)  # Be nice to DNS servers
            except Exception as e:
                print(f"Error analyzing {domain}: {e}")
                self.results.append({
                    'domain': domain,
                    'error': str(e)
                })
    
    def print_results(self):
        """Print results in a formatted table"""
        print("\n" + "="*100)
        print("DNS ANALYSIS RESULTS")
        print("="*100)
        
        for result in self.results:
            if 'error' in result:
                print(f"\n{result['domain']}: ERROR - {result['error']}")
                continue
            
            print(f"\n{'='*100}")
            print(f"Domain: {result['domain']}")
            print(f"{'='*100}")
            
            print(f"\nA Records (IPv4):")
            for ip in result['a_records']:
                print(f"  - {ip}")
            
            print(f"\nAAAA Records (IPv6):")
            for ip in result['aaaa_records']:
                print(f"  - {ip}")
            
            print(f"\nCNAME Records:")
            for cname in result['cname_records']:
                print(f"  - {cname}")
            
            print(f"\nMX Records:")
            for mx in result['mx_records']:
                print(f"  - Priority {mx['preference']}: {mx['exchange']}")
            
            print(f"\nDNSSEC:")
            print(f"  - Status: {result['dnssec']['status']}")
            print(f"  - Enabled: {result['dnssec']['enabled']}")
            
            print(f"\nDNS Lookup Path:")
            for i, hop in enumerate(result['dns_lookup_path'], 1):
                print(f"  {i}. {hop}")
    
    def save_to_json(self, filename: str = 'dns_analysis_results.json'):
        """Save results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to {filename}")

def main():
    # List of domains to analyze
    domains = [
        'google.com',
        'youtube.com',
        'facebook.com',
        'amazon.com',
        'wikipedia.org',
        'twitter.com',
        'instagram.com',
        'linkedin.com',
        'netflix.com',
        'github.com'
    ]
    
    print("DNS Analysis Tool")
    print("="*100)
    print(f"Analyzing {len(domains)} domains...")
    
    analyzer = DNSAnalyzer(domains)
    analyzer.analyze_all()
    analyzer.print_results()
    analyzer.save_to_json()

if __name__ == "__main__":
    main()
