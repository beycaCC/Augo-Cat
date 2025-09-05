import psutil
import time
import random
import pyautogui
import cv2
import numpy as np
from PIL import Image
import threading
import subprocess
import os
import ctypes
from ctypes import wintypes
import pytesseract
import re
from datetime import datetime

class SteamGameMonitor:
    def __init__(self):
        self.is_game_running = False
        self.countdown_active = False
        self.typing_thread = None
        self.stop_typing = False
        self.screenshot_dir = "./screenshot"
        self.bongo_cat_window = None
        self.max_screenshots_per_category = 5  # Keep 5 most recent screenshots per category
        
        # Create screenshot directory if it doesn't exist
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)
            print(f"Created screenshot directory: {self.screenshot_dir}")
    
    def cleanup_old_screenshots(self):
        """Keep only the most recent screenshots per category for OpenCV training"""
        try:
            if not os.path.exists(self.screenshot_dir):
                return
            
            # Define screenshot categories based on filename patterns
            categories = {
                'chest_found': [],
                'chest_search': [],
                'taskbar_icon_found': [],
                'taskbar_search': [],
                'chest_not_found': [],
                'bongo_cat': []
            }
            
            # Categorize all screenshot files
            for filename in os.listdir(self.screenshot_dir):
                if filename.endswith(('.png', '.jpg', '.jpeg')):
                    filepath = os.path.join(self.screenshot_dir, filename)
                    mtime = os.path.getmtime(filepath)
                    
                    # Determine category based on filename
                    if 'chest_found' in filename:
                        categories['chest_found'].append((mtime, filepath))
                    elif 'chest_search' in filename:
                        categories['chest_search'].append((mtime, filepath))
                    elif 'taskbar_icon_found' in filename:
                        categories['taskbar_icon_found'].append((mtime, filepath))
                    elif 'taskbar_search' in filename:
                        categories['taskbar_search'].append((mtime, filepath))
                    elif 'chest_not_found' in filename:
                        categories['chest_not_found'].append((mtime, filepath))
                    elif 'bongo_cat' in filename:
                        categories['bongo_cat'].append((mtime, filepath))
            
            total_deleted = 0
            total_kept = 0
            
            # Clean up each category
            for category, files in categories.items():
                if not files:
                    continue
                    
                # Sort by modification time (newest first)
                files.sort(reverse=True)
                
                # Keep only the most recent ones per category
                if len(files) > self.max_screenshots_per_category:
                    files_to_delete = files[self.max_screenshots_per_category:]
                    for _, filepath in files_to_delete:
                        try:
                            os.remove(filepath)
                            print(f"🗑️ Cleaned up old {category}: {os.path.basename(filepath)}")
                            total_deleted += 1
                        except Exception as e:
                            print(f"⚠️ Could not delete {filepath}: {e}")
                    
                    kept_count = min(len(files), self.max_screenshots_per_category)
                    total_kept += kept_count
                    print(f"📸 Kept {kept_count} most recent {category} screenshots")
                else:
                    total_kept += len(files)
            
            if total_deleted > 0:
                print(f"📸 Screenshot cleanup complete: {total_deleted} deleted, {total_kept} kept")
            else:
                print(f"📸 Screenshot storage: {total_kept} images (within limits)")
                
        except Exception as e:
            print(f"⚠️ Error cleaning up screenshots: {e}")
        
    def is_steam_game_running(self):
        """Check if any Steam game is currently running"""
        steam_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                if proc.info['exe'] and 'steam' in proc.info['exe'].lower():
                    # Check if it's a game process (not just Steam client)
                    if any(game_indicator in proc.info['name'].lower() for game_indicator in 
                          ['.exe', 'game', 'launcher', 'client']):
                        # Additional check: Steam games usually have specific patterns
                        if not any(steam_client in proc.info['name'].lower() for steam_client in 
                                 ['steam.exe', 'steamwebhelper.exe', 'steamservice.exe']):
                            steam_processes.append(proc.info['name'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        return len(steam_processes) > 0, steam_processes
    
    def is_bongo_cat_running(self):
        """Check if Bongo Cat game is specifically running"""
        bongo_processes = []
        
        # Bongo Cat process names (based on actual detection)
        bongo_names = [
            'bongocat.exe',
            'bongo cat',
            'bongocat',
            'bongo-cat',
            'bongo_cat',
            'unitycrashhandler64.exe'  # Unity crash handler for Bongo Cat
        ]
        
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                proc_name = proc.info['name'].lower()
                proc_exe = proc.info['exe'].lower() if proc.info['exe'] else ''
                
                # Check if process name contains bongo cat
                for bongo_name in bongo_names:
                    if bongo_name in proc_name or bongo_name in proc_exe:
                        bongo_processes.append({
                            'name': proc.info['name'],
                            'exe': proc.info['exe'],
                            'pid': proc.info['pid']
                        })
                        break
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        return len(bongo_processes) > 0, bongo_processes
    
    def list_all_running_processes(self):
        """List all running processes to help identify Bongo Cat"""
        print("Scanning all running processes...")
        print("Looking for processes that might be Bongo Cat...")
        
        all_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                all_processes.append({
                    'name': proc.info['name'],
                    'exe': proc.info['exe'],
                    'pid': proc.info['pid']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Filter for potential game processes
        game_processes = []
        for proc in all_processes:
            name = proc['name'].lower()
            exe = proc['exe'].lower() if proc['exe'] else ''
            
            # Look for game-related keywords
            if any(keyword in name or keyword in exe for keyword in 
                   ['game', 'bongo', 'cat', 'steam', 'unity', 'unreal', 'game.exe']):
                game_processes.append(proc)
        
        print(f"\nFound {len(game_processes)} potential game processes:")
        for proc in game_processes[:20]:  # Show first 20
            print(f"  - {proc['name']} (PID: {proc['pid']})")
            if proc['exe']:
                print(f"    Path: {proc['exe']}")
        
        if len(game_processes) > 20:
            print(f"  ... and {len(game_processes) - 20} more processes")
        
        return game_processes
    
    def find_bongo_cat_window(self):
        """Find and focus on Bongo Cat window"""
        try:
            import pygetwindow as gw
            # Try different window title patterns
            window_titles = ['Bongo Cat', 'BongoCat', 'bongo cat', 'bongocat']
            
            for title in window_titles:
                windows = gw.getWindowsWithTitle(title)
                if windows:
                    window = windows[0]
                    # Check if window is valid and not minimized
                    if window.left >= -1000 and window.top >= -1000 and window.width > 100 and window.height > 100:
                        self.bongo_cat_window = window
                        print(f"Found Bongo Cat window with title: '{title}'")
                        print(f"Window position: ({self.bongo_cat_window.left}, {self.bongo_cat_window.top})")
                        print(f"Window size: {self.bongo_cat_window.width}x{self.bongo_cat_window.height}")
                        return True
                    else:
                        print(f"Found window but coordinates are invalid: x={window.left}, y={window.top}, w={window.width}, h={window.height}")
                        # Try to restore and activate the window
                        try:
                            window.restore()
                            window.activate()
                            time.sleep(1)
                            # Check coordinates again
                            if window.left >= -1000 and window.top >= -1000 and window.width > 100 and window.height > 100:
                                self.bongo_cat_window = window
                                print(f"Window restored successfully")
                                print(f"Window position: ({self.bongo_cat_window.left}, {self.bongo_cat_window.top})")
                                print(f"Window size: {self.bongo_cat_window.width}x{self.bongo_cat_window.height}")
                                return True
                        except Exception as restore_error:
                            print(f"Could not restore window: {restore_error}")
            
            # If no exact match, try to find any window with "bongo" in the title
            all_windows = gw.getAllWindows()
            for window in all_windows:
                if window.title and 'bongo' in window.title.lower():
                    if window.left >= -1000 and window.top >= -1000 and window.width > 100 and window.height > 100:
                        self.bongo_cat_window = window
                        print(f"Found Bongo Cat window with partial title: '{window.title}'")
                        print(f"Window position: ({self.bongo_cat_window.left}, {self.bongo_cat_window.top})")
                        print(f"Window size: {self.bongo_cat_window.width}x{self.bongo_cat_window.height}")
                        return True
            
            print("No valid Bongo Cat window found")
            return False
        except Exception as e:
            print(f"Error finding Bongo Cat window: {e}")
            return False
    
    def click_timer_area(self):
        """Click on the typing counter area to show timer"""
        try:
            if not self.bongo_cat_window:
                if not self.find_bongo_cat_window():
                    print("Could not find Bongo Cat window")
                    return False
            
            # Get window position and size
            x, y, width, height = self.bongo_cat_window.left, self.bongo_cat_window.top, self.bongo_cat_window.width, self.bongo_cat_window.height
            
            # Validate window coordinates (allow y=-1 for some window managers)
            if x < 0 or y < -1 or width <= 0 or height <= 0:
                print(f"Invalid window coordinates: x={x}, y={y}, width={width}, height={height}")
                return False
            
            # Estimate timer area (left box under the cat)
            # Adjust these coordinates based on your Bongo Cat layout
            timer_x = x + width // 4  # Left side of window
            timer_y = y + height // 2  # Middle height of window
            
            # Validate calculated coordinates
            if timer_x < 0 or timer_y < 0:
                print(f"Invalid calculated coordinates: timer_x={timer_x}, timer_y={timer_y}")
                return False
            
            print(f"Clicking timer area at ({timer_x}, {timer_y})")
            
            # Temporarily disable failsafe for this click
            original_failsafe = pyautogui.FAILSAFE
            pyautogui.FAILSAFE = False
            
            try:
                pyautogui.click(timer_x, timer_y)
                time.sleep(1)  # Wait for timer to appear
                return True
            finally:
                # Restore original failsafe setting
                pyautogui.FAILSAFE = original_failsafe
            
        except Exception as e:
            print(f"Error clicking timer area: {e}")
            return False
    
    def read_timer_with_ocr(self):
        """Read timer using OCR from Bongo Cat window"""
        try:
            # Take screenshot of Bongo Cat window
            if not self.bongo_cat_window:
                if not self.find_bongo_cat_window():
                    return None
            
            # Get window coordinates
            x, y, width, height = self.bongo_cat_window.left, self.bongo_cat_window.top, self.bongo_cat_window.width, self.bongo_cat_window.height
            
            # Take screenshot of the window
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(self.screenshot_dir, f"bongo_cat_{timestamp}.png")
            screenshot.save(screenshot_path)
            
            # Convert to OpenCV format
            img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # Crop to timer area (adjust coordinates based on your layout)
            timer_region = img[height//3:height//2, width//6:width//3]  # Adjust these values
            
            # Use OCR to read timer
            timer_text = pytesseract.image_to_string(timer_region, config='--psm 8 -c tessedit_char_whitelist=0123456789:')
            
            # Parse timer format (MM:SS)
            timer_match = re.search(r'(\d{1,2}):(\d{2})', timer_text.strip())
            if timer_match:
                minutes = int(timer_match.group(1))
                seconds = int(timer_match.group(2))
                total_seconds = minutes * 60 + seconds
                print(f"OCR detected timer: {minutes:02d}:{seconds:02d} ({total_seconds} seconds)")
                return total_seconds
            else:
                print(f"Could not parse timer from OCR: '{timer_text.strip()}'")
                return None
                
        except Exception as e:
            print(f"Error reading timer with OCR: {e}")
            return None
    
    def get_smart_countdown_duration(self):
        """Get countdown duration using OCR timer reading"""
        print("Attempting to read game timer with OCR...")
        
        # Try to find Bongo Cat window first
        if not self.find_bongo_cat_window():
            print("Could not find Bongo Cat window, using default 30 minutes")
            return 30 * 60
        
        # Check if Tesseract is available
        try:
            pytesseract.get_tesseract_version()
            print("Tesseract OCR is available")
        except Exception as e:
            print(f"Tesseract OCR not available: {e}")
            print("Please install Tesseract OCR for timer reading functionality")
            print("For now, using default 30 minutes")
            return 30 * 60
        
        # Try to click timer area to make timer visible
        if not self.click_timer_area():
            print("Could not click timer area, trying OCR without clicking...")
        
        # Read timer with OCR
        remaining_seconds = self.read_timer_with_ocr()
        
        if remaining_seconds is not None and remaining_seconds > 0:
            print(f"Using OCR timer: {remaining_seconds} seconds remaining")
            return remaining_seconds
        else:
            print("OCR failed, using default 30 minutes")
            return 30 * 60
    
    def get_random_words(self):
        """Generate random words for typing"""
        words = [
            "hello", "world", "python", "programming", "computer", "keyboard", "mouse",
            "screen", "monitor", "desktop", "window", "application", "software", "hardware",
            "internet", "network", "database", "algorithm", "function", "variable", "class",
            "object", "method", "parameter", "argument", "return", "import", "module",
            "library", "framework", "development", "coding", "debugging", "testing",
            "steam", "game", "gaming", "player", "level", "score", "achievement",
            "bongo", "cat", "chest", "icon", "click", "screenshot", "image", "detection"
        ]
        return random.choice(words)
    
    def get_random_chars(self):
        """Generate random single characters for more frequent keypresses"""
        chars = "abcdefghijklmnopqrstuvwxyz0123456789"
        return random.choice(chars)
    
    def send_keypress_winapi(self, char):
        """Send keypress using Windows API for more realistic simulation"""
        try:
            # Virtual key codes
            VK_SPACE = 0x20
            VK_RETURN = 0x0D
            
            if char == ' ':
                vk_code = VK_SPACE
            elif char == '\n':
                vk_code = VK_RETURN
            else:
                vk_code = ord(char.upper())
            
            # Send key down with longer duration for better detection
            ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
            time.sleep(random.uniform(0.05, 0.15))  # Longer key down time
            # Send key up
            ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)  # 2 = KEYEVENTF_KEYUP
            
        except Exception as e:
            print(f"WinAPI keypress error: {e}")
            # Fallback to pyautogui
            pyautogui.press(char)
    
    def send_keypress_pyautogui(self, char):
        """Send keypress using pyautogui with enhanced timing"""
        try:
            # Use pyautogui with more realistic timing
            pyautogui.keyDown(char)
            time.sleep(random.uniform(0.05, 0.15))  # Longer key down time
            pyautogui.keyUp(char)
        except Exception as e:
            print(f"PyAutoGUI keypress error: {e}")
    
    def send_keypress_enhanced(self, char):
        """Enhanced keypress method that tries multiple approaches"""
        try:
            # Method 1: Windows API
            self.send_keypress_winapi(char)
            time.sleep(random.uniform(0.01, 0.03))
            
            # Method 2: PyAutoGUI as backup (for better detection)
            self.send_keypress_pyautogui(char)
            
        except Exception as e:
            print(f"Enhanced keypress error: {e}")
            # Final fallback
            pyautogui.press(char)
    
    def type_random_words_with_target(self, target_chars):
        """Type random words with character target tracking"""
        keypress_count = 0
        self.chars_typed_this_cycle = 0
        
        while not self.stop_typing and self.countdown_active and self.chars_typed_this_cycle < target_chars:
            try:
                # Mix of different typing patterns for better detection
                typing_pattern = random.choice(['word', 'chars', 'mixed', 'rapid'])
                
                if typing_pattern == 'word':
                    # Type a full word with enhanced keypress
                    word = self.get_random_words()
                    for char in word:
                        if self.stop_typing or not self.countdown_active or self.chars_typed_this_cycle >= target_chars:
                            break
                        self.send_keypress_enhanced(char)
                        keypress_count += 1
                        self.chars_typed_this_cycle += 1
                        time.sleep(random.uniform(0.02, 0.08))
                    
                    # Add space
                    if not self.stop_typing and self.countdown_active and self.chars_typed_this_cycle < target_chars:
                        self.send_keypress_enhanced(' ')
                        keypress_count += 1
                        self.chars_typed_this_cycle += 1
                    
                elif typing_pattern == 'chars':
                    # Type individual characters more frequently
                    for _ in range(random.randint(2, 5)):
                        if self.stop_typing or not self.countdown_active or self.chars_typed_this_cycle >= target_chars:
                            break
                        char = self.get_random_chars()
                        self.send_keypress_enhanced(char)
                        keypress_count += 1
                        self.chars_typed_this_cycle += 1
                        time.sleep(random.uniform(0.02, 0.08))
                    
                    # Add space
                    if not self.stop_typing and self.countdown_active and self.chars_typed_this_cycle < target_chars:
                        self.send_keypress_enhanced(' ')
                        keypress_count += 1
                        self.chars_typed_this_cycle += 1
                
                elif typing_pattern == 'rapid':
                    # Rapid single character typing for maximum detection
                    for _ in range(random.randint(1, 3)):
                        if self.stop_typing or not self.countdown_active or self.chars_typed_this_cycle >= target_chars:
                            break
                        char = self.get_random_chars()
                        # Try multiple methods for each character
                        self.send_keypress_winapi(char)
                        time.sleep(random.uniform(0.01, 0.03))
                        self.send_keypress_pyautogui(char)
                        keypress_count += 2
                        self.chars_typed_this_cycle += 1
                        time.sleep(random.uniform(0.02, 0.05))
                
                else:  # mixed
                    # Mix of words and individual characters
                    for _ in range(random.randint(1, 3)):
                        if self.stop_typing or not self.countdown_active or self.chars_typed_this_cycle >= target_chars:
                            break
                        if random.choice([True, False]):
                            # Type a word
                            word = self.get_random_words()
                            for char in word:
                                if self.stop_typing or not self.countdown_active or self.chars_typed_this_cycle >= target_chars:
                                    break
                                self.send_keypress_enhanced(char)
                                keypress_count += 1
                                self.chars_typed_this_cycle += 1
                                time.sleep(random.uniform(0.02, 0.08))
                        else:
                            # Type individual characters
                            char = self.get_random_chars()
                            self.send_keypress_enhanced(char)
                            keypress_count += 1
                            self.chars_typed_this_cycle += 1
                            time.sleep(random.uniform(0.02, 0.08))
                    
                    # Add space
                    if not self.stop_typing and self.countdown_active and self.chars_typed_this_cycle < target_chars:
                        self.send_keypress_enhanced(' ')
                        keypress_count += 1
                        self.chars_typed_this_cycle += 1
                
                # Print progress every 50 characters
                if self.chars_typed_this_cycle % 50 == 0 and self.chars_typed_this_cycle > 0:
                    progress = (self.chars_typed_this_cycle / target_chars) * 100
                    print(f"\n[PROGRESS] {self.chars_typed_this_cycle:,}/{target_chars:,} characters ({progress:.1f}%)")
                
                # Random delay between typing sessions
                time.sleep(random.uniform(0.1, 0.5))
                
            except Exception as e:
                print(f"Error typing: {e}")
                break
        
        print(f"\n[FINAL] Characters typed this cycle: {self.chars_typed_this_cycle:,}/{target_chars:,}")
        print(f"[FINAL] Total keypresses sent: {keypress_count}")

    def type_random_words(self):
        """Legacy method - kept for backward compatibility"""
        keypress_count = 0
        while not self.stop_typing and self.countdown_active:
            try:
                # Mix of different typing patterns for better detection
                typing_pattern = random.choice(['word', 'chars', 'mixed', 'rapid'])
                
                if typing_pattern == 'word':
                    # Type a full word with enhanced keypress
                    word = self.get_random_words()
                    for char in word:
                        if self.stop_typing or not self.countdown_active:
                            break
                        self.send_keypress_enhanced(char)
                        keypress_count += 1
                        time.sleep(random.uniform(0.02, 0.08))  # Slightly longer delays
                    
                    # Add space
                    if not self.stop_typing and self.countdown_active:
                        self.send_keypress_enhanced(' ')
                        keypress_count += 1
                    
                elif typing_pattern == 'chars':
                    # Type individual characters more frequently
                    for _ in range(random.randint(2, 5)):  # Reduced for better detection
                        if self.stop_typing or not self.countdown_active:
                            break
                        char = self.get_random_chars()
                        self.send_keypress_enhanced(char)
                        keypress_count += 1
                        time.sleep(random.uniform(0.02, 0.08))
                    
                    # Add space
                    if not self.stop_typing and self.countdown_active:
                        self.send_keypress_enhanced(' ')
                        keypress_count += 1
                
                elif typing_pattern == 'rapid':
                    # Rapid single character typing for maximum detection
                    for _ in range(random.randint(1, 3)):
                        if self.stop_typing or not self.countdown_active:
                            break
                        char = self.get_random_chars()
                        # Try multiple methods for each character
                        self.send_keypress_winapi(char)
                        time.sleep(random.uniform(0.01, 0.03))
                        self.send_keypress_pyautogui(char)
                        keypress_count += 2  # Count both attempts
                        time.sleep(random.uniform(0.02, 0.05))
                
                else:  # mixed
                    # Mix of words and individual characters
                    for _ in range(random.randint(1, 3)):  # Reduced for better detection
                        if self.stop_typing or not self.countdown_active:
                            break
                        if random.choice([True, False]):
                            # Type a word
                            word = self.get_random_words()
                            for char in word:
                                if self.stop_typing or not self.countdown_active:
                                    break
                                self.send_keypress_enhanced(char)
                                keypress_count += 1
                                time.sleep(random.uniform(0.02, 0.08))
                        else:
                            # Type individual characters
                            char = self.get_random_chars()
                            self.send_keypress_enhanced(char)
                            keypress_count += 1
                            time.sleep(random.uniform(0.02, 0.08))
                    
                    # Add space
                    if not self.stop_typing and self.countdown_active:
                        self.send_keypress_enhanced(' ')
                        keypress_count += 1
                
                # Print keypress count every 1000 keypresses
                if keypress_count % 1000 == 0:
                    print(f"\n[DEBUG] Total keypresses sent: {keypress_count}")
                
                # Random delay between typing sessions
                time.sleep(random.uniform(0.1, 0.5))  # Longer delays for better detection
                
            except Exception as e:
                print(f"Error typing: {e}")
                break
        
        print(f"\n[FINAL] Total keypresses sent: {keypress_count}")
    
    def find_bongo_cat_taskbar_icon(self):
        """Find and click the Bongo Cat app icon on the taskbar"""
        try:
            print("Looking for Bongo Cat taskbar icon...")
            
            # Take a screenshot of the taskbar area
            screenshot = pyautogui.screenshot()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            taskbar_screenshot_path = os.path.join(self.screenshot_dir, f"taskbar_search_{timestamp}.png")
            screenshot.save(taskbar_screenshot_path)
            
            # Load the screenshot and taskbar icon template
            img = cv2.imread(taskbar_screenshot_path)
            if img is None:
                print("Failed to load taskbar screenshot")
                return False
            
            # Load Bongo Cat taskbar icon template
            icon_template_path = "App_icon_on_task_bar.png"
            if not os.path.exists(icon_template_path):
                print(f"Bongo Cat taskbar icon template not found at {icon_template_path}")
                return False
            
            template = cv2.imread(icon_template_path)
            if template is None:
                print("Failed to load taskbar icon template")
                return False
            
            print(f"📏 Screenshot dimensions: {img.shape[1]}x{img.shape[0]}")
            print(f"📏 Icon template dimensions: {template.shape[1]}x{template.shape[0]}")
            
            # Convert both images to grayscale for template matching
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            # Get template dimensions
            template_h, template_w = template_gray.shape
            
            print(f"🔍 Starting taskbar icon template matching...")
            
            # Perform template matching
            result = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            
            # Find the best match location
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            print(f"🎯 Best match confidence: {max_val:.4f}")
            
            # Set threshold for matching
            threshold = 0.7
            
            if max_val >= threshold:
                # Get the top-left corner of the matched area
                top_left = max_loc
                bottom_right = (top_left[0] + template_w, top_left[1] + template_h)
                
                # Calculate center point for clicking
                center_x = top_left[0] + template_w // 2
                center_y = top_left[1] + template_h // 2
                
                print(f"🎯 Bongo Cat taskbar icon found! Confidence: {max_val:.4f}")
                print(f"📍 Icon location: top_left=({top_left[0]}, {top_left[1]}), bottom_right=({bottom_right[0]}, {bottom_right[1]})")
                print(f"🖱️ Clicking on taskbar icon at position ({center_x}, {center_y})")
                
                # Move mouse and click
                pyautogui.moveTo(center_x, center_y, duration=0.5)
                time.sleep(0.2)
                pyautogui.click()
                time.sleep(0.5)  # Wait for Bongo Cat to become active
                
                print("✅ Bongo Cat taskbar icon clicked!")
                
                # Draw rectangle around the found icon for verification
                cv2.rectangle(img, top_left, bottom_right, (0, 255, 0), 2)
                cv2.putText(img, f"Bongo Cat Icon (Conf: {max_val:.3f})", 
                           (top_left[0], top_left[1] - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Save verification screenshot
                verification_path = os.path.join(self.screenshot_dir, f"taskbar_icon_found_{timestamp}.png")
                cv2.imwrite(verification_path, img)
                print(f"✅ Screenshot with detected taskbar icon saved as {verification_path}")
                
                # Clean up old screenshots to keep only 10 most recent
                self.cleanup_old_screenshots()
                return True
            else:
                print(f"❌ Bongo Cat taskbar icon not found. Best match confidence: {max_val:.4f} (threshold: {threshold})")
                print("💡 Try adjusting the threshold or check if the icon is visible in the screenshot")
                
                # Still save the screenshot for manual inspection
                verification_path = os.path.join(self.screenshot_dir, f"taskbar_icon_not_found_{timestamp}.png")
                cv2.imwrite(verification_path, img)
                print(f"📸 Screenshot saved for inspection: {verification_path}")
                return False
                
        except Exception as e:
            print(f"Error finding Bongo Cat taskbar icon: {e}")
            import traceback
            traceback.print_exc()
            return False

    def setup_safe_typing_area(self):
        """Set up a safe area for typing by clicking Bongo Cat taskbar icon"""
        try:
            print("Setting up safe typing area...")
            
            # Find and click Bongo Cat taskbar icon
            if self.find_bongo_cat_taskbar_icon():
                print("✅ Bongo Cat window activated for safe typing")
                return True
            else:
                print("❌ Could not find Bongo Cat taskbar icon, typing may be visible")
                return False
                
        except Exception as e:
            print(f"Error setting up safe typing area: {e}")
            return False
    
    def cleanup_typing_area(self):
        """Clean up the typing area after completion"""
        try:
            print("Cleaning up typing area...")
            # Since we're typing directly into Bongo Cat, no cleanup needed
            # The typing will be processed by the game and not visible
            print("✅ Typing area cleanup completed (Bongo Cat handles input)")
        except Exception as e:
            print(f"Error cleaning up: {e}")

    def start_countdown_with_typing(self, cycle_number, target_chars):
        """Start countdown with typing for Operation 1"""
        print(f"Starting Bongo Cat session - Cycle {cycle_number}...")
        print(f"Target: {target_chars:,} characters this cycle")
        
        print("Setting up safe typing area...")
        
        # Set up safe typing area
        safe_area_ready = self.setup_safe_typing_area()
        if not safe_area_ready:
            print("Warning: Could not set up safe typing area. Typing may be recorded.")
        
        # Get smart countdown duration using OCR
        countdown_duration = self.get_smart_countdown_duration()
        
        print(f"Random words will be typed during the countdown.")
        print(f"After {countdown_duration//60} minutes, the program will take a screenshot and open the chest!")
        print("Press Ctrl+C to stop the program.")
        
        self.countdown_active = True
        self.stop_typing = False
        
        # Start typing thread with character target
        self.typing_thread = threading.Thread(target=self.type_random_words_with_target, args=(target_chars,))
        self.typing_thread.daemon = True
        self.typing_thread.start()
        
        # Smart countdown using OCR timer
        for remaining in range(countdown_duration, 0, -1):
            if not self.countdown_active:
                break
                
            minutes = remaining // 60
            seconds = remaining % 60
            print(f"\rCycle {cycle_number} - Time remaining: {minutes:02d}:{seconds:02d}", end="", flush=True)
            time.sleep(1)
        
        if self.countdown_active:
            print(f"\n\nCycle {cycle_number} completed! Taking screenshot and opening chest...")
            self.stop_typing = True
            
            # Clean up the typing area
            self.cleanup_typing_area()
            
            # Take screenshot and find chest
            chest_found = self.take_screenshot_and_find_chest()
            if not chest_found:
                print("🛑 Program stopped due to chest detection failure.")
                return 0
            
            # Return characters typed this cycle
            return getattr(self, 'chars_typed_this_cycle', 0)
        
        return 0

    def start_countdown_chest_only(self, cycle_number):
        """Start countdown without typing for Operation 2"""
        print(f"Starting Bongo Cat session - Cycle {cycle_number}...")
        print("CHEST-ONLY MODE: No typing will occur")
        
        print("Setting up safe typing area...")
        
        # Set up safe typing area (just to activate Bongo Cat window)
        safe_area_ready = self.setup_safe_typing_area()
        if not safe_area_ready:
            print("Warning: Could not set up safe typing area.")
        
        # Get smart countdown duration using OCR
        countdown_duration = self.get_smart_countdown_duration()
        
        print(f"Waiting {countdown_duration//60} minutes before clicking chest...")
        print("Press Ctrl+C to stop the program.")
        
        self.countdown_active = True
        
        # No typing thread - just wait
        for remaining in range(countdown_duration, 0, -1):
            if not self.countdown_active:
                break
                
            minutes = remaining // 60
            seconds = remaining % 60
            print(f"\rCycle {cycle_number} - Time remaining: {minutes:02d}:{seconds:02d}", end="", flush=True)
            time.sleep(1)
        
        if self.countdown_active:
            print(f"\n\nCycle {cycle_number} completed! Taking screenshot and opening chest...")
            
            # Take screenshot and find chest with retry mechanism
            chest_found = self.take_screenshot_and_find_chest()
            if not chest_found:
                print("🛑 Program stopped due to chest detection failure after 6 attempts.")
                # Set a flag to indicate program should stop
                self.countdown_active = False
                return

    def start_countdown(self, cycle_number=None):
        """Legacy method - kept for backward compatibility"""
        if cycle_number:
            self.start_countdown_chest_only(cycle_number)
        else:
            self.start_countdown_chest_only(1)
    
    def take_screenshot_and_find_chest(self, attempt=1, max_attempts=7):
        """Take screenshot and find bongo cat chest icon using template matching with retry mechanism"""
        try:
            print("📸 Taking screenshot for chest detection...")
            
            # Take screenshot
            screenshot = pyautogui.screenshot()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(self.screenshot_dir, f"chest_search_{timestamp}.png")
            screenshot.save(screenshot_path)
            print(f"Screenshot saved as {screenshot_path}")
            
            # Load the screenshot and chest template
            img = cv2.imread(screenshot_path)
            if img is None:
                print("❌ Failed to load screenshot")
                return
            
            print(f"📏 Screenshot dimensions: {img.shape[1]}x{img.shape[0]}")
            
            # Load chest template
            chest_template_path = "chest.png"
            if not os.path.exists(chest_template_path):
                print(f"❌ Chest template image not found at {chest_template_path}")
                return
            
            template = cv2.imread(chest_template_path)
            if template is None:
                print("❌ Failed to load chest template image")
                return
            
            print(f"📏 Template dimensions: {template.shape[1]}x{template.shape[0]}")
            
            # Convert both images to grayscale for template matching
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            # Get template dimensions
            template_h, template_w = template_gray.shape
            
            print(f"🔍 Starting template matching...")
            
            # Perform template matching
            result = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            
            # Find the best match location
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            print(f"🎯 Best match confidence: {max_val:.4f}")
            
            # Set threshold for matching (start with lower threshold)
            threshold = 0.5  # Lowered from 0.7
            
            if max_val >= threshold:
                # Get the top-left corner of the matched area
                top_left = max_loc
                bottom_right = (top_left[0] + template_w, top_left[1] + template_h)
                
                # Calculate center point for clicking
                center_x = top_left[0] + template_w // 2
                center_y = top_left[1] + template_h // 2
                
                print(f"🎁 Chest found! Confidence: {max_val:.4f}")
                print(f"📍 Chest location: top_left=({top_left[0]}, {top_left[1]}), bottom_right=({bottom_right[0]}, {bottom_right[1]})")
                print(f"🖱️ Clicking on chest at position ({center_x}, {center_y})")
                
                # Move mouse and click
                pyautogui.moveTo(center_x, center_y, duration=0.5)
                time.sleep(0.2)
                pyautogui.click()
                time.sleep(0.2)
                pyautogui.click()  # Double click for better reliability
                
                print("✅ Chest clicked!")
                
                # Draw rectangle around the found chest for verification
                cv2.rectangle(img, top_left, bottom_right, (0, 255, 0), 2)
                cv2.putText(img, f"Chest (Conf: {max_val:.3f})", 
                           (top_left[0], top_left[1] - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Save verification screenshot
                verification_path = os.path.join(self.screenshot_dir, f"chest_found_{timestamp}.png")
                cv2.imwrite(verification_path, img)
                print(f"✅ Screenshot with detected chest saved as {verification_path}")
                
                # Clean up old screenshots to keep only 10 most recent
                self.cleanup_old_screenshots()
                return True
                
            else:
                print(f"❌ No chest found. Best match confidence: {max_val:.4f} (threshold: {threshold})")
                print("💡 Try adjusting the threshold or check if the chest image is visible in the screenshot")
                
                # Try with even lower threshold
                lower_threshold = 0.3
                if max_val >= lower_threshold:
                    print(f"🔍 Trying with lower threshold {lower_threshold}...")
                    top_left = max_loc
                    bottom_right = (top_left[0] + template_w, top_left[1] + template_h)
                    center_x = top_left[0] + template_w // 2
                    center_y = top_left[1] + template_h // 2
                    
                    print(f"🎁 Chest found with lower threshold! Confidence: {max_val:.4f}")
                    print(f"🖱️ Clicking on chest at position ({center_x}, {center_y})")
                    
                    pyautogui.moveTo(center_x, center_y, duration=0.5)
                    time.sleep(0.2)
                    pyautogui.click()
                    time.sleep(0.2)
                    pyautogui.click()
                    
                    print("✅ Chest clicked with lower threshold!")
                    
                    # Draw rectangle around the found chest for verification
                    cv2.rectangle(img, top_left, bottom_right, (0, 255, 0), 2)
                    cv2.putText(img, f"Chest (Conf: {max_val:.3f})", 
                               (top_left[0], top_left[1] - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Save verification screenshot
                    verification_path = os.path.join(self.screenshot_dir, f"chest_found_low_thresh_{timestamp}.png")
                    cv2.imwrite(verification_path, img)
                    print(f"✅ Screenshot with detected chest saved as {verification_path}")
                    
                    # Clean up old screenshots to keep only 10 most recent
                    self.cleanup_old_screenshots()
                    return True
                else:
                    # Still save the screenshot for manual inspection
                    verification_path = os.path.join(self.screenshot_dir, f"chest_not_found_{timestamp}.png")
                    cv2.imwrite(verification_path, img)
                    print(f"📸 Screenshot saved for inspection: {verification_path}")
                    print("🔍 Please check the screenshot to see if the chest is visible and adjust the template image if needed")
                    
                    # Handle chest not found with retry mechanism
                    if attempt < max_attempts:
                        print(f"\n⚠️ CHEST NOT FOUND - Attempt {attempt}/{max_attempts}")
                        print("🔄 Possible reasons:")
                        print("1. Game timer hasn't reached 30 minutes yet")
                        print("2. Chest template image needs updating") 
                        print("3. Chest is in a different location")
                        print(f"\n⏰ Waiting 5 minutes before retry {attempt + 1}/{max_attempts}...")
                        
                        # Wait 5 minutes (300 seconds)
                        for remaining in range(300, 0, -1):
                            minutes = remaining // 60
                            seconds = remaining % 60
                            print(f"\r⏰ Waiting: {minutes:02d}:{seconds:02d} remaining", end="", flush=True)
                            time.sleep(1)
                        
                        print(f"\n🔄 Retrying chest detection (Attempt {attempt + 1}/{max_attempts})...")
                        return self.take_screenshot_and_find_chest(attempt + 1, max_attempts)
                    else:
                        print(f"\n❌ CHEST NOT FOUND after {max_attempts} attempts!")
                        print("🛑 Stopping program due to repeated chest detection failures.")
                        print("💡 Possible solutions:")
                        print("1. Check if Bongo Cat game is running properly")
                        print("2. Update chest template image (chest.png)")
                        print("3. Verify game timer synchronization")
                        print("4. Check if chest spawns in different location")
                        return False
                
        except Exception as e:
            print(f"❌ Error during screenshot and detection: {e}")
            import traceback
            traceback.print_exc()
    
    def run_typing_mode(self, max_cycles):
        """Operation 1: Typing mode with user-specified cycles and character calculation"""
        print(f"📝 TYPING MODE STARTED")
        print(f"Target: {max_cycles} cycles × 1000 characters = {max_cycles * 1000:,} total characters")
        print("Press Ctrl+C to stop the program at any time.")
        
        cycle_count = 0
        total_chars_typed = 0
        target_chars = max_cycles * 1000
        
        try:
            while cycle_count < max_cycles and total_chars_typed < target_chars:
                is_running, processes = self.is_bongo_cat_running()
                
                if is_running and not self.is_game_running:
                    cycle_count += 1
                    remaining_chars = target_chars - total_chars_typed
                    chars_this_cycle = min(1000, remaining_chars)
                    
                    print(f"\n🎮 Bongo Cat detected! Starting cycle {cycle_count}/{max_cycles}")
                    print(f"Running processes: {[p['name'] for p in processes]}")
                    print(f"📊 Characters this cycle: {chars_this_cycle:,}")
                    print(f"📊 Total progress: {total_chars_typed:,}/{target_chars:,} characters")
                    
                    self.is_game_running = True
                    chars_typed = self.start_countdown_with_typing(cycle_count, chars_this_cycle)
                    if chars_typed == 0:  # Program stopped due to chest detection failure
                        print("🛑 Program stopped due to chest detection failure.")
                        break
                    total_chars_typed += chars_typed
                    
                    # Reset for next cycle
                    self.is_game_running = False
                    self.countdown_active = False
                    self.stop_typing = True
                    
                    if cycle_count < max_cycles and total_chars_typed < target_chars:
                        print(f"\n⏳ Cycle {cycle_count} completed. Total typed: {total_chars_typed:,}/{target_chars:,}")
                        print("Press Ctrl+C to stop, or wait for next cycle...")
                        time.sleep(5)  # Brief pause between cycles
                    
                elif not is_running and self.is_game_running:
                    print("\n❌ Bongo Cat stopped during cycle.")
                    self.is_game_running = False
                    self.countdown_active = False
                    self.stop_typing = True
                
                time.sleep(2)  # Check every 2 seconds
            
            if total_chars_typed >= target_chars:
                print(f"\n🎉 TARGET ACHIEVED! Typed {total_chars_typed:,} characters in {cycle_count} cycles!")
            else:
                print(f"\n🎉 All {max_cycles} cycles completed! Total typed: {total_chars_typed:,} characters")
            print("Program finished.")
                
        except KeyboardInterrupt:
            print(f"\n\n⏹️ Program stopped by user after {cycle_count} cycles")
            print(f"📊 Total characters typed: {total_chars_typed:,}/{target_chars:,}")
            self.countdown_active = False
            self.stop_typing = True
            if self.typing_thread:
                self.typing_thread.join(timeout=1)

    def run_chest_only_mode(self):
        """Operation 2: Chest-only mode - clicks chest every 30 minutes without typing"""
        print(f"🎯 CHEST-ONLY MODE STARTED")
        print("This mode will only click chest every 30 minutes (no typing)")
        print("Press Ctrl+C to stop the program at any time.")
        
        cycle_count = 0
        
        try:
            while True:  # Run indefinitely until stopped
                is_running, processes = self.is_bongo_cat_running()
                
                if is_running and not self.is_game_running:
                    cycle_count += 1
                    print(f"\n🎮 Bongo Cat detected! Starting chest-only cycle {cycle_count}")
                    print(f"Running processes: {[p['name'] for p in processes]}")
                    
                    self.is_game_running = True
                    self.start_countdown_chest_only(cycle_count)
                    
                    # Check if program stopped due to chest detection failure
                    if not self.countdown_active:
                        print("🛑 Program stopped due to chest detection failure.")
                        break
                    
                    # Reset for next cycle
                    self.is_game_running = False
                    self.countdown_active = True  # Reset for next cycle
                    
                    print(f"\n⏳ Cycle {cycle_count} completed. Waiting for next 30-minute cycle...")
                    print("Press Ctrl+C to stop, or wait for next cycle...")
                    time.sleep(5)  # Brief pause between cycles
                    
                elif not is_running and self.is_game_running:
                    print("\n❌ Bongo Cat stopped during cycle.")
                    self.is_game_running = False
                    self.countdown_active = False
                
                time.sleep(2)  # Check every 2 seconds
                
        except KeyboardInterrupt:
            print(f"\n\n⏹️ Program stopped by user after {cycle_count} cycles")
            self.countdown_active = False

    def run(self):
        """Legacy method - kept for backward compatibility"""
        self.run_typing_mode(30)

def display_menu():
    """Display the main menu for user selection"""
    print("\n" + "="*60)
    print("🎮 BONGO CAT AUTOMATION TOOL")
    print("="*60)
    print("Choose your operation:")
    print()
    print("1. 📝 TYPING MODE")
    print("   - Specify number of cycles to run")
    print("   - Automatically calculates characters needed (cycles × 1000)")
    print("   - Continuously types until target is reached")
    print("   - Clicks chest every 30 minutes")
    print()
    print("2. 🎯 CHEST-ONLY MODE")
    print("   - Only clicks chest every 30 minutes")
    print("   - No typing involved")
    print("   - Perfect for passive monitoring")
    print()
    print("="*60)
    print("Your choice: ", end="")

def get_user_choice():
    """Get and validate user choice"""
    while True:
        try:
            choice = input().strip()
            if choice in ['1', '2']:
                return int(choice)
            else:
                print("❌ Invalid choice. Please enter 1 or 2.")
                print("Your choice: ", end="")
        except KeyboardInterrupt:
            print("\n\n👋 Program cancelled by user.")
            return None

def get_cycle_count():
    """Get number of cycles from user for Operation 1"""
    while True:
        try:
            print("\n📊 TYPING MODE CONFIGURATION")
            print("="*40)
            print("How many cycles would you like to run?")
            print("(Each cycle = 30 minutes + 1000 characters)")
            print()
            cycles = int(input("Number of cycles: "))
            if cycles > 0:
                total_chars = cycles * 1000
                print(f"\n✅ Configuration:")
                print(f"   - Cycles: {cycles}")
                print(f"   - Total characters to type: {total_chars:,}")
                print(f"   - Estimated time: {cycles * 30} minutes")
                print()
                confirm = input("Proceed with this configuration? (y/n): ").lower().strip()
                if confirm in ['y', 'yes']:
                    return cycles
                else:
                    print("Let's try again...")
            else:
                print("❌ Please enter a positive number.")
        except ValueError:
            print("❌ Please enter a valid number.")
        except KeyboardInterrupt:
            print("\n\n👋 Program cancelled by user.")
            return None

def main():
    # Check if required packages are installed
    package_mapping = {
        'psutil': 'psutil',
        'pyautogui': 'pyautogui', 
        'opencv-python': 'cv2',
        'Pillow': 'PIL',
        'numpy': 'numpy'
    }
    missing_packages = []
    
    for package_name, import_name in package_mapping.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("Missing required packages. Please install them using:")
        print(f"pip install {' '.join(missing_packages)}")
        return
    
    # Disable pyautogui failsafe for continuous typing
    pyautogui.FAILSAFE = True  # Keep failsafe enabled for safety
    
    monitor = SteamGameMonitor()
    
    # Check if Bongo Cat is running
    print("🔍 Checking for Bongo Cat game...")
    is_bongo_running, bongo_processes = monitor.is_bongo_cat_running()
    
    if not is_bongo_running:
        print("❌ Bongo Cat not detected.")
        print("\nLet's scan for all game processes to help identify Bongo Cat...")
        monitor.list_all_running_processes()
        print("\nPlease start Bongo Cat and run this program again.")
        return
    
    print(f"✅ Bongo Cat detected! Found {len(bongo_processes)} process(es):")
    for proc in bongo_processes:
        print(f"  - {proc['name']} (PID: {proc['pid']})")
        if proc['exe']:
            print(f"    Path: {proc['exe']}")
    
    # Display menu and get user choice
    display_menu()
    choice = get_user_choice()
    
    if choice is None:
        return
    
    if choice == 1:
        # Operation 1: Typing Mode
        cycles = get_cycle_count()
        if cycles is None:
            return
        
        print(f"\n🚀 Starting TYPING MODE with {cycles} cycles...")
        print("Press Ctrl+C to stop the program at any time.")
        monitor.run_typing_mode(cycles)
        
    elif choice == 2:
        # Operation 2: Chest-Only Mode
        print(f"\n🚀 Starting CHEST-ONLY MODE...")
        print("Press Ctrl+C to stop the program at any time.")
        monitor.run_chest_only_mode()

def test_process_detection():
    """Test function to help identify Bongo Cat process"""
    monitor = SteamGameMonitor()
    print("=== PROCESS DETECTION TEST ===")
    print("This will help you identify how Bongo Cat appears in the process list.")
    print("Please start Bongo Cat game and press Enter to continue...")
    input()
    
    print("\nScanning for Bongo Cat...")
    is_bongo_running, bongo_processes = monitor.is_bongo_cat_running()
    
    if is_bongo_running:
        print(f"✅ Bongo Cat detected! Found {len(bongo_processes)} process(es):")
        for proc in bongo_processes:
            print(f"  - {proc['name']} (PID: {proc['pid']})")
            if proc['exe']:
                print(f"    Path: {proc['exe']}")
    else:
        print("❌ Bongo Cat not detected with current search terms.")
        print("\nScanning all game-related processes...")
        monitor.list_all_running_processes()
        print("\nLook for the Bongo Cat process in the list above.")
        print("Note the exact process name and we can update the detection.")

def test_chest_detection():
    """Test function to test chest detection immediately"""
    monitor = SteamGameMonitor()
    print("=== CHEST DETECTION TEST ===")
    print("This will test chest detection immediately.")
    print("Make sure you have a chest visible in Bongo Cat and press Enter to continue...")
    input()
    
    print("\nTesting chest detection...")
    monitor.take_screenshot_and_find_chest()

def test_taskbar_icon_detection():
    """Test function to test taskbar icon detection"""
    monitor = SteamGameMonitor()
    print("=== TASKBAR ICON DETECTION TEST ===")
    print("This will test the Bongo Cat taskbar icon detection.")
    print("Make sure Bongo Cat is running and visible in the taskbar, then press Enter to continue...")
    input()
    
    print("\nTesting taskbar icon detection...")
    if monitor.find_bongo_cat_taskbar_icon():
        print("✅ Taskbar icon detection successful!")
    else:
        print("❌ Taskbar icon detection failed")

def test_ocr_timer():
    """Test function to test OCR timer reading"""
    monitor = SteamGameMonitor()
    print("=== OCR TIMER TEST ===")
    print("This will test the OCR timer reading functionality.")
    print("Make sure Bongo Cat is running and visible, then press Enter to continue...")
    input()
    
    print("\nTesting window detection...")
    if monitor.find_bongo_cat_window():
        print("✅ Window found successfully!")
        
        print("\nTesting timer area clicking...")
        if monitor.click_timer_area():
            print("✅ Timer area clicked successfully!")
        else:
            print("❌ Could not click timer area")
        
        print("\nTesting OCR timer reading...")
        remaining_seconds = monitor.read_timer_with_ocr()
        
        if remaining_seconds is not None:
            minutes = remaining_seconds // 60
            seconds = remaining_seconds % 60
            print(f"✅ OCR timer reading successful!")
            print(f"⏰ Detected time: {minutes:02d}:{seconds:02d} ({remaining_seconds} seconds)")
        else:
            print("❌ OCR timer reading failed")
    else:
        print("❌ Could not find Bongo Cat window")
    
    print("\nTesting smart countdown duration...")
    duration = monitor.get_smart_countdown_duration()
    minutes = duration // 60
    seconds = duration % 60
    print(f"📊 Smart countdown duration: {minutes:02d}:{seconds:02d} ({duration} seconds)")

def test_full_workflow():
    """Test the complete workflow with a short countdown"""
    monitor = SteamGameMonitor()
    print("=== FULL WORKFLOW TEST ===")
    print("This will test the complete workflow with a 30-second countdown.")
    print("Make sure Bongo Cat is running and has a chest visible, then press Enter to continue...")
    input()
    
    print("\nStarting full workflow test...")
    
    # Override the countdown to 30 seconds for testing
    original_start_countdown = monitor.start_countdown
    
    def test_start_countdown(self):
        """Test version with 30-second countdown"""
        print("Starting 30-second test countdown...")
        print("Setting up safe typing area...")
        
        # Set up safe typing area
        safe_area_ready = self.setup_safe_typing_area()
        if not safe_area_ready:
            print("Warning: Could not set up safe typing area. Typing may be recorded.")
        
        # Get smart countdown duration using OCR
        countdown_duration = self.get_smart_countdown_duration()
        
        # Override to 30 seconds for testing
        countdown_duration = 30
        print(f"Using test countdown: {countdown_duration} seconds")
        
        print(f"[TYPING DISABLED] Random words would be typed during the countdown.")
        print(f"After {countdown_duration} seconds, the program will take a screenshot and open the chest!")
        print("Press Ctrl+C to stop the program.")
        
        self.countdown_active = True
        self.stop_typing = False
        
        # TEMPORARILY COMMENTED OUT - TYPING DISABLED
        # Start typing thread
        # self.typing_thread = threading.Thread(target=self.type_random_words)
        # self.typing_thread.daemon = True
        # self.typing_thread.start()
        
        # Test countdown (30 seconds)
        for remaining in range(countdown_duration, 0, -1):
            if not self.countdown_active:
                break
                
            minutes = remaining // 60
            seconds = remaining % 60
            print(f"\rTime remaining: {minutes:02d}:{seconds:02d}", end="", flush=True)
            time.sleep(1)
        
        if self.countdown_active:
            print(f"\n\nCountdown completed! Taking screenshot and opening chest...")
            self.stop_typing = True
            
            # Clean up the typing area
            self.cleanup_typing_area()
            
            # Take screenshot and find chest
            self.take_screenshot_and_find_chest()
    
    # Replace the method temporarily
    monitor.start_countdown = test_start_countdown.__get__(monitor, SteamGameMonitor)
    
    # Run the test
    monitor.start_countdown()

if __name__ == "__main__":
    main()
