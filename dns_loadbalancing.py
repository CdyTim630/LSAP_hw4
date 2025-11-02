#!/usr/bin/env python3
"""
DNS Load Balancing Detection Script
Queries the same domain multiple times to detect if different IPs are returned
"""

import dns.resolver
import time
from collections import Counter
from typing import List, Dict, Set
import json

class DNSLoadBalancingDetector:
    def __init__(self, domains: List[str], query_count: int = 20):
        self.domains = domains
        self.query_count = query_count
        self.results = {}
    
    def query_domain_multiple_times(self, domain: str) -> List[List[str]]:
        """Query a domain multiple times and collect all IP responses"""
        all_responses = []
        
        for i in range(self.query_count):
            try:
                # Create new resolver for each query to avoid caching
                resolver = dns.resolver.Resolver()
                resolver.cache = None
                
                answers = resolver.resolve(domain, 'A')
                ips = sorted([str(rdata) for rdata in answers])
                all_responses.append(ips)
                
                time.sleep(0.05)  # Small delay between queries
            except Exception as e:
                print(f"Error querying {domain}: {e}")
        
        return all_responses
    
    def analyze_load_balancing(self, domain: str) -> Dict:
        """Analyze if a domain uses DNS load balancing"""
        print(f"Analyzing load balancing for {domain}...")
        
        responses = self.query_domain_multiple_times(domain)
        
        if not responses:
            return {
                'domain': domain,
                'has_load_balancing': False,
                'error': 'No responses received'
            }
        
        # Flatten all IPs
        all_ips = []
        for response in responses:
            all_ips.extend(response)
        
        # Get unique IPs and their counts
        ip_counter = Counter(all_ips)
        unique_ips = list(ip_counter.keys())
        
        # Check if responses vary (indicating load balancing)
        unique_response_sets = []
        for response in responses:
            response_tuple = tuple(response)
            if response_tuple not in unique_response_sets:
                unique_response_sets.append(response_tuple)
        
        has_load_balancing = len(unique_response_sets) > 1 or len(unique_ips) > 1
        
        # Analyze rotation pattern
        rotation_pattern = []
        for i, response in enumerate(responses):
            if response:
                rotation_pattern.append(response[0])  # First IP in each response
        
        return {
            'domain': domain,
            'has_load_balancing': has_load_balancing,
            'unique_ips': unique_ips,
            'ip_frequency': dict(ip_counter),
            'unique_response_patterns': len(unique_response_sets),
            'total_queries': self.query_count,
            'rotation_pattern': rotation_pattern[:10],  # First 10 for display
            'analysis': self._generate_analysis(unique_ips, unique_response_sets, ip_counter)
        }
    
    def _generate_analysis(self, unique_ips: List[str], unique_patterns: List, 
                          ip_counter: Counter) -> str:
        """Generate a text analysis of the load balancing behavior"""
        if len(unique_ips) == 1:
            return "No load balancing detected - single IP always returned"
        elif len(unique_patterns) == 1:
            return f"Multiple IPs ({len(unique_ips)}) returned consistently in the same order - possible anycast or multi-IP setup"
        else:
            most_common_ip = ip_counter.most_common(1)[0]
            return f"DNS load balancing detected - {len(unique_ips)} different IPs returned with varying patterns. Most common: {most_common_ip[0]} ({most_common_ip[1]} times)"
    
    def analyze_all(self):
        """Analyze all domains"""
        for domain in self.domains:
            try:
                result = self.analyze_load_balancing(domain)
                self.results[domain] = result
            except Exception as e:
                print(f"Error analyzing {domain}: {e}")
                self.results[domain] = {
                    'domain': domain,
                    'has_load_balancing': False,
                    'error': str(e)
                }
    
    def print_results(self):
        """Print results in a formatted manner"""
        print("\n" + "="*100)
        print("DNS LOAD BALANCING ANALYSIS")
        print("="*100)
        
        for domain, result in self.results.items():
            print(f"\n{'='*100}")
            print(f"Domain: {result['domain']}")
            print(f"{'='*100}")
            
            if 'error' in result:
                print(f"ERROR: {result['error']}")
                continue
            
            print(f"\nLoad Balancing: {'YES' if result['has_load_balancing'] else 'NO'}")
            print(f"Total Queries: {result['total_queries']}")
            print(f"Unique IPs Found: {len(result['unique_ips'])}")
            print(f"Unique Response Patterns: {result['unique_response_patterns']}")
            
            print(f"\nIP Addresses:")
            for ip, count in result['ip_frequency'].items():
                percentage = (count / result['total_queries']) * 100
                print(f"  - {ip}: {count} times ({percentage:.1f}%)")
            
            print(f"\nRotation Pattern (first 10 queries):")
            for i, ip in enumerate(result['rotation_pattern'], 1):
                print(f"  Query {i}: {ip}")
            
            print(f"\nAnalysis:")
            print(f"  {result['analysis']}")
    
    def save_to_json(self, filename: str = 'dns_loadbalancing_results.json'):
        """Save results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n\nResults saved to {filename}")
    
    def generate_summary_table(self):
        """Generate a summary table"""
        print("\n" + "="*100)
        print("SUMMARY TABLE")
        print("="*100)
        print(f"{'Domain':<30} {'Load Balancing':<20} {'Unique IPs':<15} {'Patterns':<15}")
        print("-"*100)
        
        for domain, result in self.results.items():
            if 'error' in result:
                print(f"{domain:<30} {'ERROR':<20} {'-':<15} {'-':<15}")
            else:
                lb_status = 'Yes' if result['has_load_balancing'] else 'No'
                print(f"{domain:<30} {lb_status:<20} {len(result['unique_ips']):<15} "
                      f"{result['unique_response_patterns']:<15}")

def main():
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
    
    print("DNS Load Balancing Detection Tool")
    print("="*100)
    print(f"Testing {len(domains)} domains with 20 queries each...\n")
    
    detector = DNSLoadBalancingDetector(domains, query_count=20)
    detector.analyze_all()
    detector.print_results()
    detector.generate_summary_table()
    detector.save_to_json()

if __name__ == "__main__":
    main()
