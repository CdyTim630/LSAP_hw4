#!/usr/bin/env python3
"""
DNS Resolution Time Measurement Script (Using dig command)
Measures the time taken to resolve DNS queries using dig tool as required
"""

import subprocess
import re
import statistics
import matplotlib.pyplot as plt
from typing import List, Dict
import json
import time

class DigTimingAnalyzer:
    def __init__(self, domains: List[str], iterations: int = 10):
        self.domains = domains
        self.iterations = iterations
        self.results = {}
    
    def measure_dns_time_with_dig(self, domain: str) -> float:
        """
        Measure DNS resolution time using dig command (in milliseconds)
        This meets the assignment requirement to use dig or nslookup
        """
        try:
            # Use dig with +stats to get query time
            # Don't use +noall as it removes the stats section
            result = subprocess.run(
                ['dig', domain, 'A'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            output = result.stdout
            
            # Debug: print first occurrence (remove in production)
            # print(f"Output snippet: {output[-500:]}")
            
            # Parse Query time from dig output
            # Example output: ";; Query time: 23 msec"
            match = re.search(r'Query time:\s+(\d+)\s+msec', output)
            
            if match:
                return float(match.group(1))
            else:
                # Alternative: look for different format
                # Some versions use: ";; Query time: 23 ms"
                match2 = re.search(r'Query time:\s+(\d+)\s+ms\b', output)
                if match2:
                    return float(match2.group(1))
                
                # If still not found, check if query was successful
                if 'ANSWER SECTION' in output or 'status: NOERROR' in output:
                    # Query succeeded but no timing info found
                    # This shouldn't happen with standard dig
                    print(f"  Warning: Query succeeded but no timing found for {domain}")
                    return -1
                else:
                    print(f"  Query failed for {domain}")
                    return -1
        
        except subprocess.TimeoutExpired:
            print(f"  Timeout querying {domain}")
            return -1
        except Exception as e:
            print(f"  Error querying {domain}: {e}")
            return -1
    
    def measure_dns_time_with_nslookup(self, domain: str) -> float:
        """
        Alternative: Measure DNS resolution time using nslookup
        (For comparison purposes)
        """
        try:
            start = time.perf_counter()
            
            result = subprocess.run(
                ['nslookup', domain],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            end = time.perf_counter()
            
            # Check if query was successful
            if result.returncode == 0 and 'can\'t find' not in result.stdout.lower():
                return (end - start) * 1000  # Convert to milliseconds
            else:
                return -1
        
        except Exception as e:
            return -1
    
    def test_dig_output(self, domain: str):
        """Debug function to see actual dig output"""
        print(f"\n=== Testing dig output for {domain} ===")
        try:
            result = subprocess.run(
                ['dig', domain, 'A'],
                capture_output=True,
                text=True,
                timeout=5
            )
            print("Full output:")
            print(result.stdout)
            print("\n=== End of output ===\n")
        except Exception as e:
            print(f"Error: {e}")
    
    def measure_domain(self, domain: str, debug: bool = False) -> Dict[str, float]:
        """Measure DNS resolution time multiple times and calculate statistics"""
        print(f"Measuring DNS resolution time for {domain} using dig...")
        
        # Debug mode: show one full output
        if debug:
            self.test_dig_output(domain)
        
        times = []
        nslookup_times = []
        
        for i in range(self.iterations):
            # Measure with dig
            resolution_time = self.measure_dns_time_with_dig(domain)
            if resolution_time > 0:
                times.append(resolution_time)
            
            # Optional: Also measure with nslookup for comparison
            nslookup_time = self.measure_dns_time_with_nslookup(domain)
            if nslookup_time > 0:
                nslookup_times.append(nslookup_time)
            
            # Small delay between queries
            time.sleep(0.2)
        
        if not times:
            return {
                'domain': domain,
                'dig_avg': 0,
                'dig_min': 0,
                'dig_max': 0,
                'dig_median': 0,
                'dig_std_dev': 0,
                'error': 'Failed to resolve with dig'
            }
        
        result = {
            'domain': domain,
            'dig_avg': statistics.mean(times),
            'dig_min': min(times),
            'dig_max': max(times),
            'dig_median': statistics.median(times),
            'dig_std_dev': statistics.stdev(times) if len(times) > 1 else 0,
            'dig_all_times': times,
            'successful_queries': len(times),
            'total_queries': self.iterations
        }
        
        # Add nslookup comparison if available
        if nslookup_times:
            result['nslookup_avg'] = statistics.mean(nslookup_times)
            result['nslookup_min'] = min(nslookup_times)
            result['nslookup_max'] = max(nslookup_times)
        
        return result
    
    def analyze_all(self, debug: bool = False):
        """Analyze all domains"""
        for i, domain in enumerate(self.domains):
            # Enable debug for first domain only
            result = self.measure_domain(domain, debug=(debug and i == 0))
            self.results[domain] = result
    
    def print_results(self):
        """Print results in a formatted table"""
        print("\n" + "="*120)
        print("DNS RESOLUTION TIME ANALYSIS (Using dig command)")
        print("="*120)
        print(f"{'Domain':<25} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12} "
              f"{'Median (ms)':<12} {'Std Dev':<12} {'Success Rate':<15}")
        print("-"*120)
        
        for domain, result in self.results.items():
            if 'error' in result:
                print(f"{domain:<25} ERROR: {result['error']}")
            else:
                success_rate = f"{result['successful_queries']}/{result['total_queries']}"
                print(f"{result['domain']:<25} "
                      f"{result['dig_avg']:<12.2f} "
                      f"{result['dig_min']:<12.2f} "
                      f"{result['dig_max']:<12.2f} "
                      f"{result['dig_median']:<12.2f} "
                      f"{result['dig_std_dev']:<12.2f} "
                      f"{success_rate:<15}")
    
    def print_comparison_table(self):
        """Print comparison between dig and nslookup if available"""
        has_nslookup = any('nslookup_avg' in r for r in self.results.values())
        
        if not has_nslookup:
            return
        
        print("\n" + "="*100)
        print("COMPARISON: dig vs nslookup")
        print("="*100)
        print(f"{'Domain':<25} {'dig Avg (ms)':<20} {'nslookup Avg (ms)':<20} {'Difference (ms)':<20}")
        print("-"*100)
        
        for domain, result in self.results.items():
            if 'nslookup_avg' in result and 'dig_avg' in result:
                diff = result['nslookup_avg'] - result['dig_avg']
                print(f"{domain:<25} "
                      f"{result['dig_avg']:<20.2f} "
                      f"{result['nslookup_avg']:<20.2f} "
                      f"{diff:<20.2f}")
    
    def plot_results(self, filename: str = 'dig_dns_resolution_times.png'):
        """Create a bar chart of average DNS resolution times"""
        domains = []
        avg_times = []
        
        for domain, result in self.results.items():
            if 'error' not in result:
                domains.append(domain)
                avg_times.append(result['dig_avg'])
        
        if not domains:
            print("No data to plot")
            return
        
        # Create bar chart
        plt.figure(figsize=(14, 7))
        bars = plt.bar(range(len(domains)), avg_times, color='steelblue', alpha=0.8, edgecolor='navy')
        
        # Customize chart
        plt.xlabel('Domain', fontsize=12, fontweight='bold')
        plt.ylabel('Average DNS Resolution Time (ms)', fontsize=12, fontweight='bold')
        plt.title('DNS Resolution Time Comparison (Using dig)', fontsize=14, fontweight='bold')
        plt.xticks(range(len(domains)), domains, rotation=45, ha='right')
        plt.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Add value labels on bars
        for i, bar in enumerate(bars):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}ms',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        # Add average line
        if avg_times:
            overall_avg = statistics.mean(avg_times)
            plt.axhline(y=overall_avg, color='red', linestyle='--', 
                       label=f'Overall Average: {overall_avg:.1f}ms', linewidth=2)
            plt.legend()
        
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"\nChart saved to {filename}")
        plt.close()
    
    def plot_detailed_comparison(self, filename: str = 'dig_dns_detailed_comparison.png'):
        """Create detailed comparison chart with min/max/avg"""
        domains = []
        mins = []
        avgs = []
        maxs = []
        
        for domain, result in self.results.items():
            if 'error' not in result:
                domains.append(domain)
                mins.append(result['dig_min'])
                avgs.append(result['dig_avg'])
                maxs.append(result['dig_max'])
        
        if not domains:
            print("No data to plot")
            return
        
        x = range(len(domains))
        width = 0.25
        
        fig, ax = plt.subplots(figsize=(14, 7))
        
        bars1 = ax.bar([i - width for i in x], mins, width, label='Min', color='lightgreen', alpha=0.8)
        bars2 = ax.bar(x, avgs, width, label='Average', color='steelblue', alpha=0.8)
        bars3 = ax.bar([i + width for i in x], maxs, width, label='Max', color='coral', alpha=0.8)
        
        ax.set_xlabel('Domain', fontsize=12, fontweight='bold')
        ax.set_ylabel('DNS Resolution Time (ms)', fontsize=12, fontweight='bold')
        ax.set_title('DNS Resolution Time: Min, Average, and Max (Using dig)', 
                     fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(domains, rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"Detailed comparison chart saved to {filename}")
        plt.close()
    
    def save_to_json(self, filename: str = 'dig_dns_timing_results.json'):
        """Save results to JSON file"""
        # Remove 'all_times' for cleaner JSON
        clean_results = {}
        for domain, result in self.results.items():
            clean_result = {k: v for k, v in result.items() if k != 'dig_all_times'}
            clean_results[domain] = clean_result
        
        with open(filename, 'w') as f:
            json.dump(clean_results, f, indent=2)
        print(f"Results saved to {filename}")
    
    def generate_dig_examples(self):
        """Generate example dig commands for documentation"""
        print("\n" + "="*100)
        print("EXAMPLE DIG COMMANDS USED")
        print("="*100)
        
        for domain in self.domains[:3]:  # Show first 3 as examples
            print(f"\n# Query {domain}:")
            print(f"dig {domain} A")
            print(f"\n# With specific DNS server (e.g., Google DNS):")
            print(f"dig @8.8.8.8 {domain} A")
            print(f"\n# Show only query time:")
            print(f"dig {domain} | grep 'Query time'")

def main():
    import sys
    
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
    
    # Check for debug flag
    debug = '--debug' in sys.argv
    
    print("DNS Resolution Time Measurement Tool (Using dig)")
    print("="*120)
    print(f"Measuring DNS resolution times for {len(domains)} domains...")
    print(f"Each domain will be queried {10} times using the dig command.\n")
    
    if debug:
        print("*** DEBUG MODE ENABLED - Will show detailed output for first domain ***\n")
    
    # Check if dig is available
    try:
        result = subprocess.run(['which', 'dig'], capture_output=True, check=True)
        dig_path = result.stdout.decode().strip()
        print(f"✓ dig command found at: {dig_path}")
        
        # Test dig version
        result = subprocess.run(['dig', '-v'], capture_output=True)
        version_output = result.stderr.decode().strip()
        print(f"✓ dig version: {version_output}\n")
    except:
        print("✗ ERROR: dig command not found!")
        print("  Please install dnsutils: sudo apt-get install dnsutils")
        return
    
    analyzer = DigTimingAnalyzer(domains, iterations=10)
    analyzer.analyze_all(debug=debug)
    analyzer.print_results()
    analyzer.print_comparison_table()
    analyzer.plot_results()
    analyzer.plot_detailed_comparison()
    analyzer.save_to_json()
    analyzer.generate_dig_examples()
    
    print("\n" + "="*120)
    print("Analysis complete!")
    print("="*120)

if __name__ == "__main__":
    main()