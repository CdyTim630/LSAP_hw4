#!/usr/bin/env python3
"""
WebSocket Benchmark: 1-1000 Users
用於 LSAP HW4 第 8 題
在 VM 上運行，連接本地遊戲伺服器
"""

import asyncio
import websockets
import struct
import random
import time
import csv
from enum import IntEnum
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # 無 GUI 環境使用
import matplotlib.pyplot as plt

class ServerBound(IntEnum):
    Init = 0
    Input = 1
    Spawn = 2

class InputFlags(IntEnum):
    LeftClick = 1 << 0
    Up = 1 << 1
    Left = 1 << 2
    Down = 1 << 3
    Right = 1 << 4

class BenchmarkBot:
    """用於基準測試的 WebSocket 機器人"""
    
    def __init__(self, bot_id, url):
        self.bot_id = bot_id
        self.url = url
        self.websocket = None
        self.running = True
        self.connected = False
        self.spawned = False
        self.latencies = []  # 記錄延遲
        self.start_time = 0
        self.packets_sent = 0
        self.packets_received = 0
        
    async def connect(self):
        """建立連接"""
        try:
            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    self.url,
                    ping_interval=None,
                    ping_timeout=None,
                    close_timeout=1,
                    max_size=10_000_000
                ),
                timeout=5.0
            )
            self.connected = True
            return True
        except Exception as e:
            return False
    
    async def spawn_bot(self):
        """發送 Spawn 封包"""
        try:
            bot_name = f"bot{self.bot_id}"
            spawn_packet = struct.pack('<B', ServerBound.Spawn) + \
                          bot_name.encode('utf-8') + b'\x00'
            await self.websocket.send(spawn_packet)
            self.packets_sent += 1
            return True
        except:
            return False
    
    async def measure_latency(self, duration=30):
        """測量延遲的遊戲循環"""
        if not await self.connect():
            return
        
        try:
            # Init
            build_hash = "6f59094d60f98fafc14371671d3ff31ef4d75d9e"
            password = ""
            init_packet = struct.pack('<B', ServerBound.Init) + \
                         build_hash.encode('utf-8') + b'\x00' + \
                         password.encode('utf-8') + b'\x00'
            await self.websocket.send(init_packet)
            self.packets_sent += 1
            
            # 等待 Accept
            for _ in range(10):
                try:
                    msg = await asyncio.wait_for(self.websocket.recv(), timeout=0.5)
                    self.packets_received += 1
                    if len(msg) > 0 and msg[0] == 7:
                        break
                except asyncio.TimeoutError:
                    continue
            
            await asyncio.sleep(0.1)
            
            # Spawn (兩次)
            self.start_time = time.time()
            receive_task = asyncio.create_task(self.receive_loop())
            
            await self.spawn_bot()
            await asyncio.sleep(0.2)
            await self.spawn_bot()
            await asyncio.sleep(0.5)
            
            # 主循環：發送輸入並測量延遲
            end_time = time.time() + duration
            
            while time.time() < end_time and self.running:
                try:
                    # 記錄發送時間
                    send_time = time.time()
                    
                    # 隨機輸入
                    flags = random.choice([
                        InputFlags.Up, InputFlags.Down,
                        InputFlags.Left, InputFlags.Right,
                        InputFlags.LeftClick
                    ]) if random.random() > 0.5 else 0
                    
                    input_packet = struct.pack(
                        '<Biffff',
                        ServerBound.Input,
                        flags,
                        random.uniform(-1, 1),
                        random.uniform(-1, 1),
                        random.uniform(-0.5, 0.5),
                        random.uniform(-0.5, 0.5)
                    )
                    
                    await self.websocket.send(input_packet)
                    self.packets_sent += 1
                    
                    # 等待回應（簡化版延遲測量）
                    # 實際延遲 = 從發送到收到下一個 Update 的時間
                    await asyncio.sleep(0.05)  # 20 FPS
                    
                    recv_time = time.time()
                    latency = (recv_time - send_time) * 1000  # 轉換為毫秒
                    self.latencies.append(latency)
                    
                except Exception as e:
                    break
            
            receive_task.cancel()
            
        except Exception as e:
            pass
        finally:
            await self.disconnect()
    
    async def receive_loop(self):
        """接收循環"""
        try:
            while self.running:
                try:
                    msg = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    self.packets_received += 1
                    if len(msg) > 0 and (msg[0] == 0 or msg[0] == 2):
                        if not self.spawned:
                            self.spawned = True
                except asyncio.TimeoutError:
                    continue
                except:
                    break
        except:
            pass
    
    async def disconnect(self):
        """斷開連接"""
        self.running = False
        if self.websocket:
            try:
                await asyncio.wait_for(self.websocket.close(), timeout=1.0)
            except:
                pass

async def run_benchmark(num_users, duration=120, is_final=False):
    """運行基準測試"""
    url = "ws://localhost:8080/ffa"
    
    print(f"\n{'='*70}")
    print(f"開始基準測試: {num_users} 個用戶，持續 {duration} 秒")
    print(f"{'='*70}\n")
    
    # 創建機器人
    bots = [BenchmarkBot(i, url) for i in range(num_users)]
    
    # 分批啟動（避免同時連接過多）
    batch_size = 50
    start_time = time.time()
    
    for batch_start in range(0, num_users, batch_size):
        batch_end = min(batch_start + batch_size, num_users)
        print(f"啟動機器人 {batch_start+1}-{batch_end}...", end=' ')
        
        batch_bots = bots[batch_start:batch_end]
        tasks = [bot.measure_latency(duration) for bot in batch_bots]
        
        for task in tasks:
            asyncio.create_task(task)
        
        print("完成")
        await asyncio.sleep(1.0)  # 批次間延遲
    
    print(f"\n等待所有機器人連接...")
    await asyncio.sleep(5)
    
    # 等待測試完成
    connected = sum(1 for bot in bots if bot.connected)
    spawned = sum(1 for bot in bots if bot.spawned)
    print(f"已連接: {connected}/{num_users}, 已進入遊戲: {spawned}/{num_users}")
    
    print(f"\n測試進行中... 持續時間: {duration} 秒")
    for remaining in range(duration, 0, -10):
        active = sum(1 for bot in bots if bot.running)
        spawned_now = sum(1 for bot in bots if bot.spawned)
        print(f"  活躍機器人: {active}/{num_users}, 遊戲中: {spawned_now}/{num_users}, 剩餘: {remaining} 秒")
        await asyncio.sleep(10)
    
    # 等待所有機器人完成
    await asyncio.sleep(2)
    
    # 停止所有機器人
    for bot in bots:
        bot.running = False
    
    await asyncio.sleep(1)
    
    # 收集統計數據
    end_time = time.time()
    total_duration = end_time - start_time
    
    all_latencies = []
    total_packets_sent = 0
    total_packets_received = 0
    
    for bot in bots:
        all_latencies.extend(bot.latencies)
        total_packets_sent += bot.packets_sent
        total_packets_received += bot.packets_received
    
    if all_latencies:
        all_latencies.sort()
        avg_latency = sum(all_latencies) / len(all_latencies)
        median_latency = all_latencies[len(all_latencies) // 2]
        p95_latency = all_latencies[int(len(all_latencies) * 0.95)]
        p99_latency = all_latencies[int(len(all_latencies) * 0.99)]
        p99_5_latency = all_latencies[int(len(all_latencies) * 0.995)]  # P99.5
        min_latency = min(all_latencies)
        max_latency = max(all_latencies)
    else:
        avg_latency = median_latency = p95_latency = p99_latency = p99_5_latency = 0
        min_latency = max_latency = 0
    
    # 顯示結果
    print(f"\n{'='*70}")
    print(f"測試完成: {num_users} 個用戶")
    print(f"{'='*70}")
    print(f"總時長: {total_duration:.2f} 秒")
    print(f"成功連接: {connected}/{num_users} ({connected/num_users*100:.1f}%)")
    print(f"成功進入: {spawned}/{num_users} ({spawned/num_users*100:.1f}%)")
    print(f"發送封包: {total_packets_sent}")
    print(f"接收封包: {total_packets_received}")
    print(f"\n延遲統計 (毫秒):")
    print(f"  平均: {avg_latency:.2f} ms")
    print(f"  中位數: {median_latency:.2f} ms")
    print(f"  最小: {min_latency:.2f} ms")
    print(f"  最大: {max_latency:.2f} ms")
    print(f"  P95: {p95_latency:.2f} ms")
    print(f"  P99: {p99_latency:.2f} ms")
    print(f"  P99.5: {p99_5_latency:.2f} ms")
    print(f"{'='*70}\n")
    
    return {
        'users': num_users,
        'duration': total_duration,
        'connected': connected,
        'spawned': spawned,
        'packets_sent': total_packets_sent,
        'packets_received': total_packets_received,
        'avg_latency': avg_latency,
        'median_latency': median_latency,
        'min_latency': min_latency,
        'max_latency': max_latency,
        'p95_latency': p95_latency,
        'p99_latency': p99_latency,
        'p99_5_latency': p99_5_latency,
        'success_rate': connected / num_users * 100
    }

async def check_server_connection():
    """檢查伺服器是否可連接"""
    url = "ws://localhost:8080/ffa"
    print("\n🔍 檢查伺服器連接...")
    print(f"   嘗試連接: {url}")
    
    try:
        ws = await asyncio.wait_for(
            websockets.connect(url, ping_interval=None, ping_timeout=None),
            timeout=5.0
        )
        await ws.close()
        print("   ✅ 伺服器連接成功！")
        return True
    except asyncio.TimeoutError:
        print("   ❌ 連接超時！")
        print("\n請檢查:")
        print("   1. 遊戲伺服器是否正在運行:")
        print("      sudo systemctl status shooter-game")
        print("   2. 端口 8080 是否開放:")
        print("      netstat -tuln | grep 8080")
        print("   3. 嘗試手動啟動:")
        print("      cd ~/minimal-shooter-game && npm start")
        return False
    except ConnectionRefusedError:
        print("   ❌ 連接被拒絕！")
        print("\n伺服器未運行，請啟動:")
        print("   sudo systemctl start shooter-game")
        print("   或手動啟動:")
        print("   cd ~/minimal-shooter-game && npm start")
        return False
    except Exception as e:
        print(f"   ❌ 連接失敗: {e}")
        return False

async def main():
    """主程式"""
    print("="*70)
    print("WebSocket 基準測試 - LSAP HW4 第 8 題")
    print("="*70)
    print("\n測試配置:")
    print("  連接: ws://localhost:8080/ffa (本地伺服器)")
    print("  用戶數量: 從 1 遞增至 1000（每次遞增 100）")
    print("  每次測試持續: 2 分鐘（120 秒）")
    
    # 檢查伺服器連接
    if not await check_server_connection():
        print("\n⚠️  無法連接到伺服器，測試中止。")
        return
    
    print()
    input("按 Enter 開始測試...")
    
    # 測試不同數量的用戶：從 1 開始，然後每次遞增 100
    test_cases = [1] + list(range(100, 1001, 100))  # [1, 100, 200, 300, ..., 1000]
    results = []
    
    print(f"\n將執行 {len(test_cases)} 次測試: {test_cases}")
    print(f"預計總時間: 約 {len(test_cases) * 2.5} 分鐘\n")
    
    for i, num_users in enumerate(test_cases):
        is_final = (i == len(test_cases) - 1)  # 最後一個測試
        # 所有測試都是 2 分鐘（120 秒）
        result = await run_benchmark(num_users, duration=120, is_final=is_final)
        results.append(result)
        
        # 每次測試之間等待一下
        if not is_final:
            print(f"\n等待 10 秒後進行下一個測試...")
            await asyncio.sleep(10)
    
    # 保存結果到 CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"websocket_benchmark_results_{timestamp}.csv"
    
    with open(csv_filename, 'w', newline='') as csvfile:
        fieldnames = ['users', 'duration', 'connected', 'spawned', 'success_rate',
                     'packets_sent', 'packets_received', 
                     'avg_latency', 'median_latency', 'min_latency', 'max_latency',
                     'p95_latency', 'p99_latency', 'p99_5_latency']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print(f"\n✅ 測試完成！結果已保存到: {csv_filename}")
    print(f"\n📊 測試摘要:")
    print(f"{'用戶數':<10} {'成功率':<10} {'平均':<12} {'P95':<12} {'P99':<12} {'P99.5':<12}")
    print("-" * 70)
    for result in results:
        print(f"{result['users']:<10} "
              f"{result['success_rate']:<10.1f}% "
              f"{result['avg_latency']:<12.2f}ms "
              f"{result['p95_latency']:<12.2f}ms "
              f"{result['p99_latency']:<12.2f}ms "
              f"{result['p99_5_latency']:<12.2f}ms")
    
    # 生成圖表
    print(f"\n� 正在生成圖表...")
    generate_charts(results, timestamp)
    
    print(f"\n�💡 下載結果檔案到本地:")
    print(f"   scp -P 5034 classuser@lsap2.lu.im.ntu.edu.tw:~/lsap_hw4/{csv_filename} .")
    print(f"   scp -P 5034 classuser@lsap2.lu.im.ntu.edu.tw:~/lsap_hw4/latency_chart_{timestamp}.png .")
    print(f"   scp -P 5034 classuser@lsap2.lu.im.ntu.edu.tw:~/lsap_hw4/success_rate_chart_{timestamp}.png .")

def generate_charts(results, timestamp):
    """生成圖表"""
    users = [r['users'] for r in results]
    avg_latency = [r['avg_latency'] for r in results]
    p95_latency = [r['p95_latency'] for r in results]
    p99_latency = [r['p99_latency'] for r in results]
    p99_5_latency = [r['p99_5_latency'] for r in results]
    success_rate = [r['success_rate'] for r in results]
    
    # 設置中文字體（如果需要）
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 圖表 1: 延遲統計（包含 P99.5）
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(users, avg_latency, marker='o', linewidth=2.5, label='Average', color='#2E86AB', markersize=6)
    ax.plot(users, p95_latency, marker='s', linewidth=2.5, label='P95', color='#A23B72', markersize=6)
    ax.plot(users, p99_latency, marker='^', linewidth=2.5, label='P99', color='#F18F01', markersize=6)
    ax.plot(users, p99_5_latency, marker='D', linewidth=2.5, label='P99.5', color='#C73E1D', markersize=6)
    
    ax.set_xlabel('Number of Users', fontsize=13, fontweight='bold')
    ax.set_ylabel('Latency (ms)', fontsize=13, fontweight='bold')
    ax.set_title('WebSocket Latency Metrics vs Number of Users (2-minute test)', fontsize=15, fontweight='bold')
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # 添加數據標籤（只在關鍵點）
    key_indices = [0, len(users)//2, -1]  # 第一個、中間、最後一個
    for i in key_indices:
        if i < len(users):
            ax.annotate(f'{avg_latency[i]:.1f}', (users[i], avg_latency[i]), 
                       textcoords="offset points", xytext=(0,8), ha='center', fontsize=9, color='#2E86AB')
    
    plt.tight_layout()
    latency_filename = f'latency_chart_{timestamp}.png'
    plt.savefig(latency_filename, dpi=300, bbox_inches='tight')
    print(f"   ✅ 延遲圖表已保存: {latency_filename}")
    plt.close()
    
    # 圖表 2: 成功率和延遲組合圖
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 子圖 1: 成功率
    bars = ax1.bar(range(len(users)), success_rate, color='#06A77D', alpha=0.8)
    ax1.set_xlabel('Number of Users', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Connection Success Rate', fontsize=14, fontweight='bold')
    ax1.set_xticks(range(len(users)))
    ax1.set_xticklabels(users)
    ax1.set_ylim([0, 110])
    ax1.grid(True, alpha=0.3, axis='y')
    
    # 添加百分比標籤
    for i, (bar, rate) in enumerate(zip(bars, success_rate)):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 2,
                f'{rate:.1f}%', ha='center', va='bottom', fontsize=9)
    
    # 子圖 2: 延遲箱形圖風格（包含 P99.5）
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
    width = 0.2
    x = range(len(users))
    
    ax2.bar([i - 1.5*width for i in x], avg_latency, width, label='Avg', color=colors[0], alpha=0.8)
    ax2.bar([i - 0.5*width for i in x], p95_latency, width, label='P95', color=colors[1], alpha=0.8)
    ax2.bar([i + 0.5*width for i in x], p99_latency, width, label='P99', color=colors[2], alpha=0.8)
    ax2.bar([i + 1.5*width for i in x], p99_5_latency, width, label='P99.5', color=colors[3], alpha=0.8)
    
    ax2.set_xlabel('Number of Users', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Latency (ms)', fontsize=12, fontweight='bold')
    ax2.set_title('Latency Distribution by Percentile', fontsize=14, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(users)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    combined_filename = f'success_rate_chart_{timestamp}.png'
    plt.savefig(combined_filename, dpi=300, bbox_inches='tight')
    print(f"   ✅ 成功率與延遲圖表已保存: {combined_filename}")
    plt.close()
    
    # 圖表 3: 封包統計
    packets_sent = [r['packets_sent'] for r in results]
    packets_received = [r['packets_received'] for r in results]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    width = 0.35
    x = range(len(users))
    
    bars1 = ax.bar([i - width/2 for i in x], packets_sent, width, 
                   label='Packets Sent', color='#06A77D', alpha=0.8)
    bars2 = ax.bar([i + width/2 for i in x], packets_received, width,
                   label='Packets Received', color='#C73E1D', alpha=0.8)
    
    ax.set_xlabel('Number of Users', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Packets', fontsize=12, fontweight='bold')
    ax.set_title('Packet Traffic Statistics', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(users)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    packets_filename = f'packets_chart_{timestamp}.png'
    plt.savefig(packets_filename, dpi=300, bbox_inches='tight')
    print(f"   ✅ 封包統計圖表已保存: {packets_filename}")
    plt.close()
    
    print(f"\n📊 共生成 3 個圖表:")
    print(f"   1. {latency_filename} - 延遲趨勢圖")
    print(f"   2. {combined_filename} - 成功率與延遲分布")
    print(f"   3. {packets_filename} - 封包流量統計")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  測試已中斷")
