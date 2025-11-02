#!/usr/bin/env python3
"""
Network Routing Path Analysis Script
Uses traceroute to identify all intermediate hops and enriches with geolocation data
Meets assignment requirements for recording: IP, Hostname, Organization, Country, Location, Latency
"""

import subprocess
import re
import requests
import json
from typing import Dict, List, Optional
import time
import sys

class TracerouteAnalyzer:
    def __init__(self, domain: str):
        self.domain = domain
        self.hops = []
    
    def run_traceroute(self, max_hops: int = 30) -> List[str]:
        """Run traceroute and return raw output lines"""
        print(f"Running traceroute to {self.domain}...")
        print("This may take 1-2 minutes...\n")
        
        try:
            # Try different traceroute commands based on availability
            commands = [
                ['traceroute', '-n', '-m', str(max_hops), '-w', '3', self.domain],
                ['traceroute', '-m', str(max_hops), '-w', '3', self.domain],
                ['traceroute', self.domain]
            ]
            
            output = ""
            for cmd in commands:
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    output = result.stdout
                    if output and 'traceroute' in output.lower():
                        print(f"✓ Used command: {' '.join(cmd)}\n")
                        break
                except FileNotFoundError:
                    continue
                except Exception as e:
                    continue
            
            if not output:
                print("✗ traceroute command not found or failed")
                return []
            
            lines = output.strip().split('\n')
            return lines
        
        except subprocess.TimeoutExpired:
            print("✗ Traceroute timeout")
            return []
        except Exception as e:
            print(f"✗ Error running traceroute: {e}")
            return []
    
    def parse_traceroute_line(self, line: str, hop_num: int) -> Optional[Dict]:
        """Parse a single traceroute output line"""
        # Skip header line
        if 'traceroute' in line.lower() or 'hops max' in line.lower():
            return None
        
        # Remove leading/trailing whitespace
        line = line.strip()
        
        # Collect all IPs and RTTs from the line
        # Pattern for IP addresses
        ip_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        # Pattern for RTT with 'ms' suffix (with or without space)
        rtt_pattern = r'([\d.]+)\s*ms'
        
        ips = re.findall(ip_pattern, line)
        rtts = re.findall(rtt_pattern, line)
        
        # Convert RTTs to floats
        rtt_values = [float(rtt) for rtt in rtts]
        
        # Check if line has timeouts
        has_timeout = '*' in line
        
        # Case 1: Has IP addresses and RTTs
        if ips and rtt_values:
            # Use first IP as the main hop IP
            main_ip = ips[0]
            
            # Take up to 3 RTT values
            rtt_list = rtt_values[:3]
            
            # Calculate average
            avg_latency = round(sum(rtt_list) / len(rtt_list), 2) if rtt_list else 0
            
            return {
                'hop_number': hop_num,
                'ip_address': main_ip,
                'hostname': None,  # Will be enriched later
                'rtt_ms': rtt_list,
                'avg_latency_ms': avg_latency,
                'status': 'active',
                'all_ips': ips  # Store all IPs seen in this hop
            }
        
        # Case 2: Only timeouts
        elif has_timeout and not ips:
            return {
                'hop_number': hop_num,
                'ip_address': None,
                'hostname': None,
                'rtt_ms': [],
                'avg_latency_ms': 0,
                'status': 'timeout'
            }
        
        # Case 3: Mixed (some * and some IPs)
        elif has_timeout and ips:
            # Still consider it active if we got at least one IP
            main_ip = ips[0]
            rtt_list = rtt_values[:3] if rtt_values else []
            avg_latency = round(sum(rtt_list) / len(rtt_list), 2) if rtt_list else 0
            
            return {
                'hop_number': hop_num,
                'ip_address': main_ip,
                'hostname': None,
                'rtt_ms': rtt_list,
                'avg_latency_ms': avg_latency,
                'status': 'partial',  # Indicates some packets were lost
                'all_ips': ips
            }
        
        return None
    
    def parse_traceroute_output(self, lines: List[str]) -> List[Dict]:
        """Parse complete traceroute output"""
        hops = []
        
        for line in lines:
            # Extract hop number from line
            hop_match = re.match(r'\s*(\d+)', line)
            if not hop_match:
                continue
            
            hop_num = int(hop_match.group(1))
            hop_data = self.parse_traceroute_line(line, hop_num)
            
            if hop_data:
                hops.append(hop_data)
                status = "✓" if hop_data['status'] == 'active' else "✗"
                ip = hop_data['ip_address'] or "* * *"
                latency = f"{hop_data['avg_latency_ms']:.2f}ms" if hop_data['avg_latency_ms'] > 0 else "timeout"
                print(f"  {status} Hop {hop_num}: {ip} ({latency})")
        
        return hops
    
    def get_hostname_via_dig(self, ip: str) -> Optional[str]:
        """Get hostname using dig reverse DNS lookup"""
        try:
            result = subprocess.run(
                ['dig', '+short', '-x', ip],
                capture_output=True,
                text=True,
                timeout=5
            )
            hostname = result.stdout.strip().rstrip('.')
            return hostname if hostname else None
        except:
            return None
    
    def get_ip_geolocation(self, ip: str) -> Dict:
        """Get geolocation info for IP using ip-api.com"""
        try:
            response = requests.get(
                f'http://ip-api.com/json/{ip}',
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success':
                    return {
                        'organization': data.get('isp', 'Unknown'),
                        'country': data.get('country', 'Unknown'),
                        'country_code': data.get('countryCode', 'Unknown'),
                        'city': data.get('city', 'Unknown'),
                        'region': data.get('regionName', 'Unknown'),
                        'location': f"{data.get('city', 'Unknown')}, {data.get('regionName', 'Unknown')}, {data.get('country', 'Unknown')}",
                        'lat': data.get('lat'),
                        'lon': data.get('lon'),
                        'as': data.get('as', 'Unknown')
                    }
        except Exception as e:
            pass
        
        return {
            'organization': 'Unknown',
            'country': 'Unknown',
            'country_code': 'Unknown',
            'city': 'Unknown',
            'region': 'Unknown',
            'location': 'Unknown',
            'lat': None,
            'lon': None,
            'as': 'Unknown'
        }
    
    def enrich_hop_info(self, hop: Dict) -> Dict:
        """Enrich hop with hostname and geolocation"""
        if hop['status'] == 'timeout' or not hop['ip_address']:
            hop['hostname'] = 'N/A'
            hop['organization'] = 'N/A'
            hop['country'] = 'N/A'
            hop['location'] = 'N/A'
            hop['as'] = 'N/A'
            return hop
        
        ip = hop['ip_address']
        print(f"  Enriching Hop {hop['hop_number']}: {ip}", end='')
        
        # Get hostname if not already present
        if not hop['hostname']:
            hostname = self.get_hostname_via_dig(ip)
            hop['hostname'] = hostname if hostname else 'N/A'
            if hostname:
                print(f" → {hostname[:50]}")
            else:
                print()
        
        # Get geolocation
        geo_info = self.get_ip_geolocation(ip)
        hop['organization'] = geo_info['organization']
        hop['country'] = geo_info['country']
        hop['country_code'] = geo_info['country_code']
        hop['city'] = geo_info['city']
        hop['region'] = geo_info['region']
        hop['location'] = geo_info['location']
        hop['as'] = geo_info['as']
        
        # Rate limiting
        time.sleep(0.5)
        
        return hop
    
    def analyze(self):
        """Run complete analysis"""
        # Step 1: Run traceroute
        raw_output = self.run_traceroute()
        
        if not raw_output:
            print("✗ Failed to get traceroute output")
            return
        
        # Step 2: Parse output
        print("\nParsing traceroute output...")
        self.hops = self.parse_traceroute_output(raw_output)
        
        if not self.hops:
            print("✗ No hops parsed from output")
            print("\nRaw output:")
            for line in raw_output:
                print(line)
            return
        
        print(f"\n✓ Parsed {len(self.hops)} hops")
        
        # Step 3: Enrich with geolocation
        print("\nEnriching hop information with geolocation data...")
        enriched_hops = []
        
        for hop in self.hops:
            enriched_hop = self.enrich_hop_info(hop)
            enriched_hops.append(enriched_hop)
        
        self.hops = enriched_hops
        print(f"\n✓ Enriched all hops")
    
    def print_table(self):
        """Print results as a table"""
        print("\n" + "="*160)
        print(f"NETWORK ROUTING PATH ANALYSIS: {self.domain}")
        print("="*160)
        
        # Header
        print(f"{'Hop':<5} {'IP Address':<18} {'Hostname':<40} {'Organization':<30} {'Country':<15} {'Location':<30} {'Latency(ms)':<12}")
        print("-"*160)
        
        # Rows
        for hop in self.hops:
            hop_num = hop.get('hop_number', 'N/A')
            ip = hop.get('ip_address', 'N/A') if hop.get('ip_address') else '* * *'
            hostname = hop.get('hostname', 'N/A')
            if hostname and len(hostname) > 38:
                hostname = hostname[:35] + '...'
            org = hop.get('organization', 'N/A')
            if org and len(org) > 28:
                org = org[:25] + '...'
            country = hop.get('country', 'N/A')
            location = hop.get('location', 'N/A')
            if location and len(location) > 28:
                location = location[:25] + '...'
            latency = f"{hop.get('avg_latency_ms', 0):.2f}" if hop.get('avg_latency_ms', 0) > 0 else 'timeout'
            
            print(f"{hop_num:<5} {ip:<18} {hostname:<40} {org:<30} {country:<15} {location:<30} {latency:<12}")
        
        print("="*160)
    
    def generate_route_diagram(self):
        """Generate ASCII route diagram"""
        print("\n" + "="*120)
        print("ROUTE DIAGRAM")
        print("="*120)
        
        print(f"\nSource → {self.domain}\n")
        
        for i, hop in enumerate(self.hops, 1):
            ip = hop.get('ip_address', '* * *')
            hostname = hop.get('hostname', 'N/A')
            org = hop.get('organization', 'N/A')
            country = hop.get('country', 'N/A')
            latency = hop.get('avg_latency_ms', 0)
            status = hop.get('status', 'unknown')
            
            connector = '├─' if i < len(self.hops) else '└─'
            
            if status == 'timeout':
                print(f"  {connector} Hop {i}: * * * (timeout)")
            else:
                print(f"  {connector} Hop {i}: {ip}")
                if hostname != 'N/A':
                    print(f"  │    Hostname: {hostname}")
                if org != 'N/A':
                    print(f"  │    Organization: {org}")
                if country != 'N/A':
                    print(f"  │    Country: {country}")
                print(f"  │    Latency: {latency:.2f} ms")
            
            if i < len(self.hops):
                print("  │")
        
        print("\n  Destination reached" if self.hops else "  No route found")
    
    def save_to_json(self, filename: str = None):
        """Save results to JSON"""
        if filename is None:
            filename = f'traceroute_{self.domain.replace(".", "_")}.json'
        
        data = {
            'domain': self.domain,
            'total_hops': len(self.hops),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'hops': self.hops
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n✓ Results saved to {filename}")
    
    def generate_summary(self):
        """Print summary statistics"""
        print("\n" + "="*120)
        print("SUMMARY STATISTICS")
        print("="*120)
        
        active_hops = [h for h in self.hops if h['status'] == 'active']
        timeout_hops = [h for h in self.hops if h['status'] == 'timeout']
        
        print(f"Total Hops: {len(self.hops)}")
        print(f"Active Hops: {len(active_hops)}")
        print(f"Timeout Hops: {len(timeout_hops)}")
        
        if active_hops:
            latencies = [h['avg_latency_ms'] for h in active_hops if h['avg_latency_ms'] > 0]
            if latencies:
                print(f"\nLatency Statistics:")
                print(f"  Minimum: {min(latencies):.2f} ms")
                print(f"  Maximum: {max(latencies):.2f} ms")
                print(f"  Average: {sum(latencies)/len(latencies):.2f} ms")
        
        # Count countries
        countries = [h['country'] for h in active_hops if h.get('country') and h['country'] != 'Unknown']
        if countries:
            unique_countries = list(set(countries))
            print(f"\nCountries traversed: {', '.join(unique_countries)}")

def main():
    import sys
    
    # Get domain from command line or use default
    if len(sys.argv) > 1:
        domain = sys.argv[1]
    else:
        print("Usage: python3 traceroute_analysis.py <domain>")
        print("Example: python3 traceroute_analysis.py google.com")
        print("\nUsing default: google.com")
        domain = 'google.com'
    
    print("="*120)
    print("NETWORK ROUTING PATH ANALYSIS TOOL")
    print("="*120)
    print(f"Target: {domain}")
    print("="*120)
    
    # Check if traceroute is available
    try:
        subprocess.run(['which', 'traceroute'], capture_output=True, check=True)
        print("✓ traceroute command found\n")
    except:
        print("✗ ERROR: traceroute command not found!")
        print("  Please install: sudo apt-get install traceroute")
        sys.exit(1)
    
    analyzer = TracerouteAnalyzer(domain)
    analyzer.analyze()
    
    if analyzer.hops:
        analyzer.print_table()
        analyzer.generate_route_diagram()
        analyzer.generate_summary()
        analyzer.save_to_json()
    else:
        print("\n✗ No route information available")
        print("This might be because:")
        print("  1. The target host is blocking traceroute")
        print("  2. Firewall is blocking ICMP/UDP packets")
        print("  3. Network configuration issues")
    
    print("\n" + "="*120)
    print("Analysis complete!")
    print("="*120)

if __name__ == "__main__":
    main()