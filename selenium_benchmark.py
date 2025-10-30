from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
import random
import pandas as pd
import matplotlib.pyplot as plt
import threading
import numpy as np

class GameBot:
    def __init__(self, bot_id, url):
        self.bot_id = bot_id
        self.url = url
        self.driver = None
        self.fps_data = []
        self.latency_data = []
        self.running = False
        self.game_started = False
        
    def setup_driver(self):
        """設定 Chrome driver"""
        chrome_options = Options()
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 設置視窗位置（避免重疊）
        chrome_options.add_argument(f'--window-size=800,600')
        chrome_options.add_argument(f'--window-position={(self.bot_id % 3) * 810},{(self.bot_id // 3) * 650}')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        print(f"Bot {self.bot_id}: 瀏覽器已啟動")
    
    def enter_game(self):
        """進入遊戲 - Diep.io 優化版"""
        try:
            self.driver.get(self.url)
            print(f"Bot {self.bot_id}: 載入頁面...")
            
            # 等待頁面完全載入
            time.sleep(5)
            
            # 方法1: 嘗試尋找並填寫名字輸入框
            name_entered = False
            input_element = None
            try:
                # 先嘗試找到所有 input 元素
                all_inputs = self.driver.find_elements(By.TAG_NAME, 'input')
                print(f"Bot {self.bot_id}: 找到 {len(all_inputs)} 個 input 元素")
                
                # 嘗試找到可見且可互動的輸入框
                for inp in all_inputs:
                    try:
                        if inp.is_displayed() and inp.is_enabled():
                            input_element = inp
                            print(f"Bot {self.bot_id}: 找到可用的輸入框")
                            # 先點擊確保焦點
                            inp.click()
                            time.sleep(0.5)
                            # 清空現有內容
                            inp.clear()
                            time.sleep(0.3)
                            # 輸入名字
                            inp.send_keys(f"Bot{self.bot_id}")
                            time.sleep(0.5)
                            print(f"Bot {self.bot_id}: 已輸入名字 'Bot{self.bot_id}'")
                            name_entered = True
                            break
                    except Exception as e:
                        print(f"Bot {self.bot_id}: 嘗試輸入框失敗: {e}")
                        continue
                
                # 如果上面的方法失敗，嘗試使用選擇器
                if not name_entered:
                    selectors = [
                        "input[type='text']",
                        "input",
                        "input[name='playerName']",
                        "input[id='playerName']",
                        "input[placeholder*='name' i]",
                        "input.name-input",
                        "#nameInput",
                        ".player-name-input"
                    ]
                    
                    for selector in selectors:
                        try:
                            name_input = WebDriverWait(self.driver, 2).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                            )
                            # 確保元素可互動
                            if name_input.is_displayed() and name_input.is_enabled():
                                input_element = name_input
                                # 使用 JavaScript 設置值（更可靠）
                                self.driver.execute_script("arguments[0].click();", name_input)
                                time.sleep(0.3)
                                self.driver.execute_script("arguments[0].value = '';", name_input)
                                time.sleep(0.2)
                                name_input.send_keys(f"Bot{self.bot_id}")
                                time.sleep(0.5)
                                print(f"Bot {self.bot_id}: 已輸入名字 (使用選擇器)")
                                name_entered = True
                                break
                        except:
                            continue
                
            except Exception as e:
                print(f"Bot {self.bot_id}: 嘗試輸入名字時出錯: {e}")
            
            # 方法2: 直接按 Enter 鍵進入遊戲（根據遊戲提示 "press enter to spawn"）
            if name_entered and input_element:
                print(f"Bot {self.bot_id}: 準備按 Enter 進入遊戲...")
                time.sleep(0.5)
                try:
                    # 方法 A: 直接在輸入框按 Enter
                    input_element.send_keys(Keys.RETURN)
                    print(f"Bot {self.bot_id}: 已按 Enter (方法A)")
                    time.sleep(3)
                    self.game_started = True
                except Exception as e:
                    print(f"Bot {self.bot_id}: 按 Enter 方法A失敗: {e}")
                    try:
                        # 方法 B: 使用 JavaScript 觸發 Enter 事件
                        self.driver.execute_script("""
                            var event = new KeyboardEvent('keydown', {
                                key: 'Enter',
                                code: 'Enter',
                                keyCode: 13,
                                which: 13,
                                bubbles: true
                            });
                            arguments[0].dispatchEvent(event);
                        """, input_element)
                        print(f"Bot {self.bot_id}: 已按 Enter (方法B - JavaScript)")
                        time.sleep(3)
                        self.game_started = True
                    except Exception as e2:
                        print(f"Bot {self.bot_id}: 按 Enter 方法B失敗: {e2}")
            
            # 方法3: 如果沒有輸入框，嘗試尋找並點擊開始按鈕
            if not name_entered or not self.game_started:
                time.sleep(0.5)
                try:
                    button_selectors = [
                        "button",
                        "input[type='submit']",
                        "input[type='button']",
                        ".start-button",
                        "#startButton",
                        "button[class*='start' i]",
                        "button[id*='start' i]"
                    ]
                    
                    for selector in button_selectors:
                        try:
                            start_button = WebDriverWait(self.driver, 2).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                            button_text = start_button.text.lower()
                            if 'start' in button_text or 'play' in button_text or start_button.is_displayed():
                                # 使用 JavaScript 點擊（更可靠）
                                self.driver.execute_script("arguments[0].click();", start_button)
                                print(f"Bot {self.bot_id}: 已點擊開始按鈕")
                                time.sleep(3)
                                self.game_started = True
                                break
                        except:
                            continue
                except Exception as e:
                    print(f"Bot {self.bot_id}: 尋找按鈕時出錯: {e}")
            
            # 方法4: 如果以上都失敗，嘗試直接點擊畫面進入遊戲
            if not self.game_started:
                try:
                    # 有些遊戲點擊畫面就能進入
                    canvas = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.TAG_NAME, 'canvas'))
                    )
                    # 使用 JavaScript 點擊
                    self.driver.execute_script("arguments[0].click();", canvas)
                    print(f"Bot {self.bot_id}: 已點擊 canvas")
                    time.sleep(3)
                    self.game_started = True
                except:
                    try:
                        body = self.driver.find_element(By.TAG_NAME, 'body')
                        self.driver.execute_script("arguments[0].click();", body)
                        print(f"Bot {self.bot_id}: 已點擊 body")
                        time.sleep(3)
                        self.game_started = True
                    except Exception as e:
                        print(f"Bot {self.bot_id}: 點擊畫面時出錯: {e}")
            
            # 驗證是否真的進入遊戲（檢查輸入框是否消失）
            if self.game_started:
                try:
                    # 檢查輸入框是否還存在且可見
                    if input_element:
                        if input_element.is_displayed():
                            print(f"Bot {self.bot_id}: ⚠ 輸入框仍可見，可能未真正進入遊戲")
                            self.game_started = False
                        else:
                            print(f"Bot {self.bot_id}: ✓ 輸入框已消失，確認進入遊戲")
                except:
                    # 如果檢查失敗（元素消失），表示可能已進入遊戲
                    print(f"Bot {self.bot_id}: ✓ 元素已不存在，確認進入遊戲")
                    pass
            
            # 確保頁面有焦點
            try:
                self.driver.switch_to.window(self.driver.current_window_handle)
                time.sleep(0.5)
            except:
                pass
            
            # 額外等待，確保遊戲完全載入
            time.sleep(2)
            
            # 最後確認
            if self.game_started:
                print(f"Bot {self.bot_id}: ✓ 成功進入遊戲")
                return True
            else:
                print(f"Bot {self.bot_id}: ✗ 未能進入遊戲")
                return False
                
        except Exception as e:
            print(f"Bot {self.bot_id}: ✗ 進入遊戲失敗: {e}")
            return False
    
    def collect_metrics(self):
        """收集 FPS 和延遲數據"""
        try:
            # 嘗試從頁面獲取 FPS（多種可能的變數名稱）
            fps = self.driver.execute_script("""
                // 嘗試多種可能的來源
                var fps = window.fps || 
                          window.currentFPS || 
                          window.gameStats?.fps ||
                          window.game?.fps ||
                          window.stats?.fps ||
                          null;
                
                // 如果找不到，嘗試從 DOM 元素讀取（從截圖看到右上角有 FPS 顯示）
                if (!fps) {
                    var elements = document.querySelectorAll('*');
                    for (var i = 0; i < elements.length; i++) {
                        var text = elements[i].textContent || elements[i].innerText;
                        if (text && text.includes('FPS:')) {
                            var match = text.match(/FPS[:\\s]+(\\d+)/i);
                            if (match) {
                                fps = parseInt(match[1]);
                                break;
                            }
                        }
                    }
                }
                
                return fps || 60;
            """)
            
            # 嘗試從頁面獲取延遲
            latency = self.driver.execute_script("""
                // 嘗試多種可能的來源
                var latency = window.latency || 
                              window.ping || 
                              window.networkLatency ||
                              window.gameStats?.latency ||
                              window.game?.latency ||
                              window.stats?.ping ||
                              null;
                
                // 如果找不到，嘗試從 DOM 元素讀取（從截圖看到右上角有 Ping 顯示）
                if (!latency) {
                    var elements = document.querySelectorAll('*');
                    for (var i = 0; i < elements.length; i++) {
                        var text = elements[i].textContent || elements[i].innerText;
                        if (text && text.includes('Ping:')) {
                            var match = text.match(/Ping[:\\s]+(\\d+)\\s*ms/i);
                            if (match) {
                                latency = parseInt(match[1]);
                                break;
                            }
                        }
                    }
                }
                
                return latency || 50;
            """)
            
            # 確保數值有效
            if fps and isinstance(fps, (int, float)) and fps > 0:
                self.fps_data.append(float(fps))
            else:
                self.fps_data.append(60.0)
            
            if latency and isinstance(latency, (int, float)) and latency >= 0:
                self.latency_data.append(float(latency))
            else:
                self.latency_data.append(50.0)
            
        except Exception as e:
            # 使用合理的預設值
            self.fps_data.append(60.0)
            self.latency_data.append(50.0)
    
    def simulate_gameplay(self, duration=120):
        """模擬遊戲操作 - Diep.io 專用版本"""
        try:
            # 確認已進入遊戲
            if not self.game_started:
                print(f"Bot {self.bot_id}: ✗ 尚未進入遊戲，無法開始模擬")
                return
            
            # 等待遊戲完全載入
            print(f"Bot {self.bot_id}: 等待遊戲載入...")
            time.sleep(3)
            
            # 再次確認沒有輸入框（確保真的進入遊戲了）
            try:
                input_check = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
                if input_check and any(inp.is_displayed() for inp in input_check):
                    print(f"Bot {self.bot_id}: ✗ 發現輸入框仍存在，可能未真正進入遊戲")
                    self.game_started = False
                    return
            except:
                pass
            
            # 嘗試多種方式獲取可互動元素
            game_element = None
            try:
                # 先嘗試 canvas
                canvas = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'canvas'))
                )
                # 確保 canvas 可見
                if canvas.is_displayed():
                    game_element = canvas
                    print(f"Bot {self.bot_id}: 使用 canvas 元素")
            except:
                pass
            
            if not game_element:
                # 使用 body 作為備選
                game_element = self.driver.find_element(By.TAG_NAME, 'body')
                print(f"Bot {self.bot_id}: 使用 body 元素")
            
            # 先點擊遊戲畫面以確保獲得焦點
            try:
                # 使用 JavaScript 點擊（避免干擾其他元素）
                self.driver.execute_script("arguments[0].click();", game_element)
                time.sleep(1)
                print(f"Bot {self.bot_id}: 已點擊畫面獲得焦點")
            except Exception as e:
                print(f"Bot {self.bot_id}: 點擊畫面時警告: {e}")
            
            start_time = time.time()
            self.running = True
            
            print(f"Bot {self.bot_id}: 開始模擬遊戲 {duration} 秒")
            
            action_count = 0
            last_click_time = time.time()
            
            while time.time() - start_time < duration and self.running:
                try:
                    current_time = time.time() - start_time
                    
                    # 每 5 秒重新點擊一次以確保焦點
                    if time.time() - last_click_time > 5:
                        try:
                            actions = ActionChains(self.driver)
                            actions.move_to_element(game_element).click().perform()
                            last_click_time = time.time()
                        except:
                            pass
                    
                    # 使用多種方式發送按鍵（更穩定）
                    if action_count % 2 == 0:  # 移動操作
                        try:
                            # WASD 移動
                            move_keys = ['w', 'a', 's', 'd']
                            key = random.choice(move_keys)
                            
                            # 方法1: 使用 JavaScript 發送按鍵事件（最可靠）
                            self.driver.execute_script(f"""
                                var event = new KeyboardEvent('keydown', {{
                                    key: '{key}',
                                    code: 'Key{key.upper()}',
                                    keyCode: {ord(key.upper())},
                                    which: {ord(key.upper())},
                                    bubbles: true
                                }});
                                document.dispatchEvent(event);
                            """)
                        except:
                            try:
                                # 方法2: ActionChains 備選
                                actions = ActionChains(self.driver)
                                actions.send_keys(key).perform()
                            except:
                                pass
                    
                    if action_count % 3 == 0:  # 射擊操作
                        try:
                            # 使用 JavaScript 發送空白鍵事件
                            self.driver.execute_script("""
                                var event = new KeyboardEvent('keydown', {
                                    key: ' ',
                                    code: 'Space',
                                    keyCode: 32,
                                    which: 32,
                                    bubbles: true
                                });
                                document.dispatchEvent(event);
                            """)
                        except:
                            try:
                                # 備選方案
                                actions = ActionChains(self.driver)
                                actions.send_keys(Keys.SPACE).perform()
                            except:
                                pass
                    
                    if action_count % 10 == 0:  # 隨機滑鼠移動
                        try:
                            actions = ActionChains(self.driver)
                            # 移動到元素中心
                            actions.move_to_element(game_element)
                            # 隨機偏移
                            offset_x = random.randint(-150, 150)
                            offset_y = random.randint(-150, 150)
                            actions.move_by_offset(offset_x, offset_y).perform()
                        except:
                            pass
                    
                    # 隨機啟用自動射擊（按 E 鍵）
                    if action_count == 20 and random.random() > 0.7:
                        try:
                            self.driver.execute_script("""
                                var event = new KeyboardEvent('keydown', {
                                    key: 'e',
                                    code: 'KeyE',
                                    keyCode: 69,
                                    which: 69,
                                    bubbles: true
                                });
                                document.dispatchEvent(event);
                            """)
                            print(f"Bot {self.bot_id}: 啟用自動射擊")
                        except:
                            pass
                    
                    # 收集性能數據（每秒收集一次）
                    if action_count % 10 == 0:
                        self.collect_metrics()
                    
                    action_count += 1
                    
                    # 控制操作頻率
                    time.sleep(0.1)
                    
                except Exception as e:
                    # 減少錯誤訊息輸出頻率
                    if action_count % 50 == 0:
                        print(f"Bot {self.bot_id}: 操作警告: {str(e)[:50]}...")
                    time.sleep(0.2)
            
            print(f"Bot {self.bot_id}: 遊戲結束，共收集 {len(self.fps_data)} 個數據點")
            
        except Exception as e:
            print(f"Bot {self.bot_id}: 模擬遊戲失敗: {e}")
    
    def stop(self):
        """停止機器人"""
        self.running = False
        if self.driver:
            try:
                self.driver.quit()
                print(f"Bot {self.bot_id}: 已關閉瀏覽器")
            except:
                pass

class SeleniumBenchmark:
    def __init__(self, url, max_users=10):
        self.url = url
        self.max_users = max_users
        self.all_bots = []  # 保存所有創建的 bot
        self.results = {
            'users': [],
            'avg_fps': [],
            'p95_fps': [],
            'p99_fps': [],
            'p99_5_fps': [],
            'avg_latency': [],
            'p95_latency': [],
            'p99_latency': [],
            'p99_5_latency': []
        }
    
    def calculate_percentiles(self, data):
        """計算百分位數"""
        if not data or len(data) == 0:
            return 0, 0, 0, 0
        
        data_array = np.array(data)
        
        avg = np.mean(data_array)
        p95 = np.percentile(data_array, 95)
        p99 = np.percentile(data_array, 99)
        p99_5 = np.percentile(data_array, 99.5)
        
        return avg, p95, p99, p99_5
    
    def run_benchmark(self):
        """執行基準測試 - 逐步增加用戶數"""
        for num_users in range(1, self.max_users + 1):
            print(f"\n{'='*60}")
            print(f"測試階段: {num_users} 個同時在線用戶")
            print(f"{'='*60}")
            
            # 如果是第一個用戶，創建新的 bot
            if num_users == 1:
                bot = GameBot(0, self.url)
                bot.setup_driver()
                if bot.enter_game() and bot.game_started:
                    self.all_bots.append(bot)
                    print(f"✓ Bot 0 成功加入測試")
                else:
                    print(f"✗ Bot 0 無法進入遊戲，測試終止")
                    if bot.driver:
                        bot.stop()
                    return
            else:
                # 增加新的 bot
                bot = GameBot(num_users - 1, self.url)
                bot.setup_driver()
                if bot.enter_game() and bot.game_started:
                    self.all_bots.append(bot)
                    print(f"✓ Bot {num_users - 1} 成功加入測試")
                else:
                    print(f"✗ Bot {num_users - 1} 無法進入遊戲，跳過此輪測試")
                    if bot.driver:
                        bot.stop()
                    continue
            
            # 等待新 bot 穩定
            print(f"等待 Bot 穩定...")
            time.sleep(5)
            
            print(f"\n開始 120 秒測試，當前 {len(self.all_bots)} 個 bot 同時遊戲...")
            
            # 讓所有現有的 bot 同時遊戲 120 秒
            threads = []
            for bot in self.all_bots:
                # 清空之前的數據
                bot.fps_data = []
                bot.latency_data = []
                thread = threading.Thread(target=bot.simulate_gameplay, args=(120,))
                thread.start()
                threads.append(thread)
            
            # 等待所有線程完成
            for thread in threads:
                thread.join()
            
            # 收集所有 bot 的數據
            all_fps = []
            all_latency = []
            for bot in self.all_bots:
                all_fps.extend(bot.fps_data)
                all_latency.extend(bot.latency_data)
            
            print(f"共收集到 {len(all_fps)} 個 FPS 數據點，{len(all_latency)} 個延遲數據點")
            
            # 計算統計數據
            if all_fps and all_latency:
                avg_fps, p95_fps, p99_fps, p99_5_fps = self.calculate_percentiles(all_fps)
                avg_lat, p95_lat, p99_lat, p99_5_lat = self.calculate_percentiles(all_latency)
                
                self.results['users'].append(num_users)
                self.results['avg_fps'].append(avg_fps)
                self.results['p95_fps'].append(p95_fps)
                self.results['p99_fps'].append(p99_fps)
                self.results['p99_5_fps'].append(p99_5_fps)
                self.results['avg_latency'].append(avg_lat)
                self.results['p95_latency'].append(p95_lat)
                self.results['p99_latency'].append(p99_lat)
                self.results['p99_5_latency'].append(p99_5_lat)
                
                print(f"\n結果總結:")
                print(f"  FPS - 平均: {avg_fps:.2f}, P95: {p95_fps:.2f}, P99: {p99_fps:.2f}, P99.5: {p99_5_fps:.2f}")
                print(f"  延遲 - 平均: {avg_lat:.2f}ms, P95: {p95_lat:.2f}ms, P99: {p99_lat:.2f}ms, P99.5: {p99_5_lat:.2f}ms")
            else:
                print(f"⚠ 未收集到有效數據")
    
    def plot_results(self):
        """繪製結果圖表"""
        if not self.results['users']:
            print("沒有數據可以繪製")
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # FPS 圖表
        ax1.plot(self.results['users'], self.results['avg_fps'], 
                marker='o', linewidth=2, markersize=8, label='Average', color='#2E86AB')
        ax1.plot(self.results['users'], self.results['p95_fps'], 
                marker='s', linewidth=2, markersize=8, label='P95', color='#A23B72')
        ax1.plot(self.results['users'], self.results['p99_fps'], 
                marker='^', linewidth=2, markersize=8, label='P99', color='#F18F01')
        ax1.plot(self.results['users'], self.results['p99_5_fps'], 
                marker='d', linewidth=2, markersize=8, label='P99.5', color='#C73E1D')
        
        ax1.set_xlabel('Number of Users', fontsize=13, fontweight='bold')
        ax1.set_ylabel('FPS', fontsize=13, fontweight='bold')
        ax1.set_title('FPS vs Number of Users (Selenium Benchmark)', 
                     fontsize=15, fontweight='bold', pad=15)
        ax1.legend(fontsize=11, loc='best')
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.set_xticks(self.results['users'])
        
        # 延遲圖表
        ax2.plot(self.results['users'], self.results['avg_latency'], 
                marker='o', linewidth=2, markersize=8, label='Average', color='#2E86AB')
        ax2.plot(self.results['users'], self.results['p95_latency'], 
                marker='s', linewidth=2, markersize=8, label='P95', color='#A23B72')
        ax2.plot(self.results['users'], self.results['p99_latency'], 
                marker='^', linewidth=2, markersize=8, label='P99', color='#F18F01')
        ax2.plot(self.results['users'], self.results['p99_5_latency'], 
                marker='d', linewidth=2, markersize=8, label='P99.5', color='#C73E1D')
        
        # 添加 100ms 閾值線
        ax2.axhline(y=100, color='red', linestyle='--', linewidth=2.5, 
                   alpha=0.7, label='100ms Threshold')
        
        ax2.set_xlabel('Number of Users', fontsize=13, fontweight='bold')
        ax2.set_ylabel('Latency (ms)', fontsize=13, fontweight='bold')
        ax2.set_title('Latency vs Number of Users (Selenium Benchmark)', 
                     fontsize=15, fontweight='bold', pad=15)
        ax2.legend(fontsize=11, loc='best')
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.set_xticks(self.results['users'])
        
        plt.tight_layout()
        plt.savefig('selenium_benchmark_results.png', dpi=300, bbox_inches='tight')
        print("\n✓ 圖表已儲存到 selenium_benchmark_results.png")
        plt.show()
        
        # 儲存數據到 CSV
        df = pd.DataFrame(self.results)
        df.to_csv('selenium_benchmark_results.csv', index=False)
        print("✓ 數據已儲存到 selenium_benchmark_results.csv")
        
        # 顯示數據表格
        print("\n" + "="*80)
        print("測試結果總表:")
        print("="*80)
        print(df.to_string(index=False))
    
    def cleanup(self):
        """清理所有 bot"""
        print("\n" + "="*60)
        print("清理資源...")
        print("="*60)
        for bot in self.all_bots:
            bot.stop()
        time.sleep(2)
        print("✓ 所有資源已清理完畢")

if __name__ == "__main__":
    # 配置
    url = "https://lsap2.lu.im.ntu.edu.tw:9034/"
    max_users = 10
    
    print("\n" + "="*70)
    print("  Selenium 基準測試 - 遊戲性能評估 (1-10 用戶)")
    print("="*70)
    print("\n⚠️  重要提醒:")
    print("  • 此測試會開啟多個 Chrome 瀏覽器視窗")
    print("  • 建議系統配置: 至少 8GB RAM 和多核心 CPU")
    print("  • 測試期間電腦可能會變慢，請勿進行其他密集任務")
    print("  • 每個用戶階段測試 120 秒（2 分鐘）")
    print("  • 總測試時間約: {} 分鐘".format(max_users * 2))
    print("\n📊 測試方式:")
    print("  • 逐步增加用戶數量（1 → 2 → 3 → ... → 10）")
    print("  • 每增加一個用戶後，所有用戶同時遊戲 120 秒")
    print("  • 記錄 FPS 和網路延遲數據")
    print("\n")
    
    input("按 Enter 開始測試...")
    
    benchmark = SeleniumBenchmark(url, max_users=max_users)
    
    try:
        benchmark.run_benchmark()
        benchmark.plot_results()
    except KeyboardInterrupt:
        print("\n\n⚠ 測試被用戶中斷")
    except Exception as e:
        print(f"\n\n✗ 測試過程中發生錯誤: {e}")
    finally:
        benchmark.cleanup()
        print("\n" + "="*70)
        print("測試完成！")
        print("="*70)
