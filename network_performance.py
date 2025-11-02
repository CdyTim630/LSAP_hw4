#!/usr/bin/env python3
"""
Network Performance Monitoring Script
Measures latency, packet loss, and throughput for multiple domains
"""

import subprocess
import re
import time
import requests
import statistics
from typing import Dict, List, Optional
import json
import matplotlib.pyplot as plt

class NetworkPerformanceMonitor:
    def __init__(self, domains: List[str]):
        self.domains = domains
        self.results = {}
    
    def measure_ping_latency(self, domain: str, count: int = 20) -> Dict:
        """Measure ping latency and packet loss"""
        print(f"  Measuring ping latency for {domain}...")
        
        try:
            # Run ping command
            result = subprocess.run(
                ['ping', '-c', str(count), '-i', '0.2', domain],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout
            
            # Parse packet loss
            loss_match = re.search(r'(\d+)% packet loss', output)
            packet_loss = float(loss_match.group(1)) if loss_match else 0.0
            
            # Parse RTT statistics
            rtt_match = re.search(r'rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms', output)
            
            if rtt_match:
                return {
                    'min_latency': float(rtt_match.group(1)),
                    'avg_latency': float(rtt_match.group(2)),
                    'max_latency': float(rtt_match.group(3)),
                    'std_dev': float(rtt_match.group(4)),
                    'packet_loss': packet_loss,
                    'packets_sent': count
                }
            else:
                return {
                    'error': 'Could not parse ping output',
                    'packet_loss': packet_loss
                }
        
        except subprocess.TimeoutExpired:
            return {'error': 'Ping timeout'}
        except Exception as e:
            return {'error': str(e)}
    
    def measure_download_throughput(self, domain: str, timeout: int = 15) -> Dict:
        """Measure download throughput"""
        print(f"  Measuring download throughput for {domain}...")
        
        try:
            url = f'http://{domain}'
            
            # Start timing
            start_time = time.time()
            
            # Download content
            response = requests.get(url, timeout=timeout, stream=True)
            
            total_bytes = 0
            chunk_times = []
            
            # Download in chunks and measure
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    chunk_time = time.time()
                    total_bytes += len(chunk)
                    chunk_times.append(chunk_time)
                    
                    # Stop after reasonable amount of data or time
                    if total_bytes > 5 * 1024 * 1024 or (chunk_time - start_time) > 10:
                        break
            
            end_time = time.time()
            duration = end_time - start_time
            
            if duration > 0:
                # Calculate throughput in Mbps
                throughput_mbps = (total_bytes * 8) / (duration * 1_000_000)
                
                return {
                    'throughput_mbps': throughput_mbps,
                    'total_bytes': total_bytes,
                    'duration_seconds': duration,
                    'avg_speed_mbps': throughput_mbps
                }
            else:
                return {'error': 'Invalid duration'}
        
        except requests.Timeout:
            return {'error': 'Download timeout'}
        except Exception as e:
            return {'error': str(e)}
    
    def measure_domain_performance(self, domain: str) -> Dict:
        """Measure all performance metrics for a domain"""
        print(f"\nAnalyzing {domain}...")
        
        result = {'domain': domain}
        
        # Measure latency and packet loss
        ping_results = self.measure_ping_latency(domain)
        result.update(ping_results)
        
        # Measure throughput
        throughput_results = self.measure_download_throughput(domain)
        result.update(throughput_results)
        
        return result
    
    def analyze_all(self):
        """Analyze all domains"""
        for domain in self.domains:
            try:
                result = self.measure_domain_performance(domain)
                self.results[domain] = result
                time.sleep(1)  # Be nice to servers
            except Exception as e:
                print(f"Error analyzing {domain}: {e}")
                self.results[domain] = {
                    'domain': domain,
                    'error': str(e)
                }
    
    def print_results(self):
        """Print detailed results"""
        print("\n" + "="*120)
        print("NETWORK PERFORMANCE MONITORING RESULTS")
        print("="*120)
        
        for domain, result in self.results.items():
            print(f"\n{'='*120}")
            print(f"Domain: {result['domain']}")
            print(f"{'='*120}")
            
            if 'error' in result and 'avg_latency' not in result:
                print(f"ERROR: {result['error']}")
                continue
            
            # Latency metrics
            if 'avg_latency' in result:
                print(f"\nLatency Metrics:")
                print(f"  - Average RTT: {result['avg_latency']:.2f} ms")
                print(f"  - Min RTT: {result['min_latency']:.2f} ms")
                print(f"  - Max RTT: {result['max_latency']:.2f} ms")
                print(f"  - Std Deviation: {result['std_dev']:.2f} ms")
            
            # Packet loss
            if 'packet_loss' in result:
                print(f"\nPacket Loss:")
                print(f"  - Loss Rate: {result['packet_loss']:.1f}%")
            
            # Throughput
            if 'throughput_mbps' in result:
                print(f"\nThroughput:")
                print(f"  - Download Speed: {result['throughput_mbps']:.2f} Mbps")
                print(f"  - Total Downloaded: {result['total_bytes'] / 1024:.2f} KB")
                print(f"  - Duration: {result['duration_seconds']:.2f} seconds")
            elif 'error' in result:
                print(f"\nThroughput: ERROR - {result.get('error', 'Unknown error')}")
    
    def generate_summary_table(self):
        """Generate a summary table"""
        print("\n" + "="*120)
        print("PERFORMANCE SUMMARY TABLE")
        print("="*120)
        print(f"{'Domain':<25} {'Avg Latency (ms)':<20} {'Packet Loss (%)':<20} {'Throughput (Mbps)':<20}")
        print("-"*120)
        
        for domain, result in self.results.items():
            avg_lat = f"{result.get('avg_latency', 0):.2f}" if 'avg_latency' in result else 'N/A'
            pkt_loss = f"{result.get('packet_loss', 0):.1f}" if 'packet_loss' in result else 'N/A'
            throughput = f"{result.get('throughput_mbps', 0):.2f}" if 'throughput_mbps' in result else 'N/A'
            
            print(f"{domain:<25} {avg_lat:<20} {pkt_loss:<20} {throughput:<20}")
    
    def plot_results(self, filename: str = 'network_performance.png'):
        """Create visualization of results"""
        # Prepare data
        domains = []
        latencies = []
        throughputs = []
        packet_losses = []
        
        for domain, result in self.results.items():
            if 'avg_latency' in result:
                domains.append(domain)
                latencies.append(result.get('avg_latency', 0))
                throughputs.append(result.get('throughput_mbps', 0))
                packet_losses.append(result.get('packet_loss', 0))
        
        if not domains:
            print("No data to plot")
            return
        
        # Create subplots
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        
        # Plot 1: Latency
        axes[0].bar(range(len(domains)), latencies, color='steelblue', alpha=0.8)
        axes[0].set_xlabel('Domain', fontweight='bold')
        axes[0].set_ylabel('Average Latency (ms)', fontweight='bold')
        axes[0].set_title('Average Round-Trip Latency', fontweight='bold', fontsize=12)
        axes[0].set_xticks(range(len(domains)))
        axes[0].set_xticklabels(domains, rotation=45, ha='right')
        axes[0].grid(axis='y', alpha=0.3)
        
        # Plot 2: Packet Loss
        axes[1].bar(range(len(domains)), packet_losses, color='coral', alpha=0.8)
        axes[1].set_xlabel('Domain', fontweight='bold')
        axes[1].set_ylabel('Packet Loss (%)', fontweight='bold')
        axes[1].set_title('Packet Loss Rate', fontweight='bold', fontsize=12)
        axes[1].set_xticks(range(len(domains)))
        axes[1].set_xticklabels(domains, rotation=45, ha='right')
        axes[1].grid(axis='y', alpha=0.3)
        
        # Plot 3: Throughput
        axes[2].bar(range(len(domains)), throughputs, color='seagreen', alpha=0.8)
        axes[2].set_xlabel('Domain', fontweight='bold')
        axes[2].set_ylabel('Throughput (Mbps)', fontweight='bold')
        axes[2].set_title('Download Throughput', fontweight='bold', fontsize=12)
        axes[2].set_xticks(range(len(domains)))
        axes[2].set_xticklabels(domains, rotation=45, ha='right')
        axes[2].grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"\nPerformance charts saved to {filename}")
        plt.close()
    
    def save_to_json(self, filename: str = 'network_performance_results.json'):
        """Save results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Results saved to {filename}")

def main():
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
    
    print("Network Performance Monitoring Tool")
    print("="*120)
    print(f"Measuring network performance for {len(domains)} domains...")
    print("This will measure latency, packet loss, and download throughput.\n")
    
    monitor = NetworkPerformanceMonitor(domains)
    monitor.analyze_all()
    monitor.print_results()
    monitor.generate_summary_table()
    monitor.plot_results()
    monitor.save_to_json()

if __name__ == "__main__":
    main()
