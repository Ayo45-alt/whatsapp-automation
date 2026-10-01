from flask import Flask, render_template, request, jsonify, Response
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import win32clipboard
import pyperclip
import io
import time
import os
import sys
import json
import queue
import threading

# Force UTF-8 on Windows command line streams to avoid charmap encode errors with emojis
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

GROUPS_FILE = os.path.join(os.getcwd(), 'groups.json')
log_queue = queue.Queue()
is_running = False

def log_status(msg):
    log_queue.put(str(msg))
    try:
        print(msg)
    except Exception:
        try:
            print(str(msg).encode('ascii', errors='replace').decode('ascii'))
        except Exception:
            pass

# --- Copy image to clipboard function ---
def copy_image_to_clipboard(path):
    image = Image.open(path)
    output = io.BytesIO()
    image.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:]
    output.close()
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    win32clipboard.CloseClipboard()

# --- Load and Save Groups ---
def load_groups():
    if os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_groups(groups):
    with open(GROUPS_FILE, 'w') as f:
        json.dump(groups, f, indent=2)

# --- Selenium Broadcast Task ---
def run_selenium_broadcast(groups_to_send, message_text, image_path):
    global is_running
    is_running = True
    
    driver = None
    try:
        log_status("🚀 Launching Chrome browser...")
        options = Options()
        options.add_argument(r"user-data-dir=C:\Users\USER\Desktop\whatsapp_profile_copy")
        options.add_argument("profile-directory=Profile 11")
        options.add_argument("--start-maximized")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--window-position=0,0")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        local_driver_path = os.path.join(os.getcwd(), "chromedriver.exe")
        if not os.path.exists(local_driver_path):
            local_driver_path = os.path.join(os.getcwd(), "chromedriver-win64", "chromedriver.exe")

        try:
            if os.path.exists(local_driver_path):
                service = Service(executable_path=local_driver_path)
                driver = webdriver.Chrome(service=service, options=options)
            else:
                driver = webdriver.Chrome(options=options)
        except Exception:
            driver = webdriver.Chrome(options=options)
            
        try:
            driver.maximize_window()
            driver.switch_to.window(driver.current_window_handle)
        except Exception:
            pass

        try:
            import win32gui
            import win32con
            def bring_chrome_to_front(hwnd, _):
                title = win32gui.GetWindowText(hwnd)
                if 'WhatsApp' in title or 'Chrome' in title:
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                    win32gui.SetForegroundWindow(hwnd)
            win32gui.EnumWindows(bring_chrome_to_front, None)
        except Exception:
            pass

        driver.get("https://web.whatsapp.com")
        
        log_status("⏳ Waiting for WhatsApp Web to load...")
        
        search_box_selectors = [
            "//input[@aria-label='Search or start a new chat']",
            "//div[@data-testid='chat-list-search']//input",
            "//div[@data-testid='chat-list-search']//div[@contenteditable='true']",
            "//div[@id='side']//input",
            "//div[@id='side']//div[@role='textbox']",
            "//input[contains(translate(@aria-label, 'SEARCH', 'search'), 'search')]",
            "//div[contains(translate(@aria-label, 'SEARCH', 'search'), 'search')]",
            "//div[@contenteditable='true'][@data-tab='3']"
        ]
        
        use_here_xpath = "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'use here')]"
        reconnect_xpath = "//*[contains(text(), 'Computer not connected')]//following::*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reconnect')] | //button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reconnect')]"
        qr_selectors = [
            "//canvas[@aria-label='Scan me!']",
            "//div[@data-ref]",
            "//*[contains(text(), 'Scan to log in')]",
            "//*[contains(text(), 'To use WhatsApp on your computer')]"
        ]
        
        success = False
        start_time = time.time()
        last_reconnect_click = 0
        qr_notified = False
        
        while time.time() - start_time < 300:  # 5 minutes timeout
            # 1. Primary check: Is WhatsApp Web already loaded and logged in?
            found_search = False
            for sel in search_box_selectors:
                elements = driver.find_elements(By.XPATH, sel)
                if len(elements) > 0:
                    found_search = True
                    break
            
            pane_side = driver.find_elements(By.ID, "pane-side")
            if found_search or len(pane_side) > 0:
                log_status("✅ WhatsApp Web loaded successfully!")
                log_status("[HIDE_QR_CODE]")
                success = True
                break
                
            # 2. Check for "Use here" session conflict popup
            use_here_elements = driver.find_elements(By.XPATH, use_here_xpath)
            if len(use_here_elements) > 0:
                log_status("⚠️ Detected 'Use here' popup. Activating session in this window...")
                try:
                    driver.execute_script("arguments[0].click();", use_here_elements[0])
                except Exception:
                    pass
                time.sleep(2)
                continue
                
            # 3. Check for QR Code login prompt & Auto-reload expired QR
            qr_found = False
            for qr_sel in qr_selectors:
                qr_elements = driver.find_elements(By.XPATH, qr_sel)
                if len(qr_elements) > 0:
                    qr_found = True
                    break
                    
            if qr_found:
                # Check if QR expired button is shown
                reload_btns = driver.find_elements(By.XPATH, "//div[@data-ref]//button | //button[contains(., 'reload')] | //span[contains(text(), 'Click to reload')] | //div[contains(@class, 'qr-wrapper')]//button")
                if len(reload_btns) > 0:
                    try:
                        driver.execute_script("arguments[0].click();", reload_btns[0])
                        time.sleep(1.5)
                    except Exception:
                        pass
                
                # Save screenshot of QR code to static/qr_code.png
                try:
                    qr_img_path = os.path.join(os.getcwd(), 'static', 'qr_code.png')
                    driver.save_screenshot(qr_img_path)
                except Exception:
                    pass
                    
                if not qr_notified:
                    log_status("📱 WhatsApp requires login. Scan the QR code shown on your dashboard screen!")
                    qr_notified = True
                    
                log_status("[SHOW_QR_CODE]")
                        
            # 4. Check for "Reconnect" button if disconnected (throttled to once every 10s)
            if time.time() - last_reconnect_click > 10:
                reconnect_elements = driver.find_elements(By.XPATH, reconnect_xpath)
                if len(reconnect_elements) > 0:
                    log_status("⚠️ Detected network reconnect prompt. Clicking Reconnect...")
                    try:
                        driver.execute_script("arguments[0].click();", reconnect_elements[0])
                    except Exception:
                        pass
                    last_reconnect_click = time.time()
            
            time.sleep(2)
            
        if not success:
            raise TimeoutError("Timed out waiting for WhatsApp Web. If you saw a QR code, 300 seconds was not enough to scan it. Please try again.")
        
        # Helper to find search box element dynamically
        def get_search_box():
            for sel in search_box_selectors:
                try:
                    el = driver.find_element(By.XPATH, sel)
                    if el.is_displayed():
                        return el
                except Exception:
                    continue
            return None

        # Loop through target groups
        for idx, group_name in enumerate(groups_to_send):
            try:
                log_status(f"💬 [{idx+1}/{len(groups_to_send)}] Processing: {group_name}")
                
                # 1. Locate search box
                search_box = None
                for _ in range(5):
                    search_box = get_search_box()
                    if search_box:
                        break
                    time.sleep(1)
                    
                if not search_box:
                    raise Exception("Could not locate WhatsApp search bar.")

                # Focus and clear the search box thoroughly
                try:
                    search_box.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", search_box)
                time.sleep(0.2)
                
                # Select all and delete to clear existing text
                search_box.send_keys(Keys.CONTROL + "a")
                search_box.send_keys(Keys.BACKSPACE)
                time.sleep(0.3)
                
                # Paste group name via clipboard for accurate typing
                pyperclip.copy(group_name)
                search_box.send_keys(Keys.CONTROL + "v")
                
                # 2. Wait for search results and select the chat
                time.sleep(1.5)
                
                # Send ENTER to select top match from search
                search_box.send_keys(Keys.ENTER)
                time.sleep(0.5)
                
                # Also try direct click on any matching chat item in the sidebar
                try:
                    chat_items = driver.find_elements(By.XPATH, "//div[@id='pane-side']//div[@tabindex='-1'] | //div[@id='pane-side']//span[@title]")
                    if len(chat_items) > 0:
                        driver.execute_script("arguments[0].click();", chat_items[0])
                except Exception:
                    pass
                    
                time.sleep(0.5)
                
                # 3. Locate message input compose box to confirm chat is open
                msg_box_selectors = [
                    "//div[@data-testid='conversation-compose-box-input']",
                    "//footer//div[@contenteditable='true']",
                    "//div[@role='textbox'][@data-tab='10']",
                    "//footer//p"
                ]
                msg_box = None
                for _ in range(5):
                    for sel in msg_box_selectors:
                        try:
                            el = driver.find_element(By.XPATH, sel)
                            if el.is_displayed():
                                msg_box = el
                                break
                        except Exception:
                            continue
                    if msg_box:
                        break
                    time.sleep(0.5)
                    
                if not msg_box:
                    log_status(f"⚠️ Could not open chat for: {group_name} (Chat not found or failed to load)")
                    try:
                        search_box.send_keys(Keys.CONTROL + "a", Keys.BACKSPACE)
                    except Exception:
                        pass
                    continue
                
                # 3. Attach Image (Direct File Input -> Attach Button -> Clipboard Fallback)
                abs_img_path = os.path.abspath(image_path)
                image_attached = False
                
                # Method A: Direct File Input
                file_inputs = driver.find_elements(By.XPATH, "//input[@type='file']")
                if len(file_inputs) > 0:
                    try:
                        file_inputs[0].send_keys(abs_img_path)
                        image_attached = True
                        log_status("📎 Image attached (Method A)")
                    except Exception as e:
                        pass
                        
                # Method B: Click Plus/Attach button then send to file input
                if not image_attached:
                    attach_btns = driver.find_elements(By.XPATH, "//div[@title='Attach'] | //span[@data-icon='plus'] | //span[@data-icon='attach-menu-plus'] | //button[@title='Attach'] | //div[@role='button'][@aria-label='Attach']")
                    if len(attach_btns) > 0:
                        try:
                            driver.execute_script("arguments[0].click();", attach_btns[0])
                            time.sleep(0.8)
                            file_inputs = driver.find_elements(By.XPATH, "//input[@type='file']")
                            if len(file_inputs) > 0:
                                file_inputs[0].send_keys(abs_img_path)
                                image_attached = True
                                log_status("📎 Image attached (Method B)")
                        except Exception:
                            pass
                            
                # Method C: Clipboard Paste Fallback
                if not image_attached:
                    copy_image_to_clipboard(image_path)
                    time.sleep(0.3)
                    try:
                        driver.execute_script("arguments[0].focus();", msg_box)
                        msg_box.click()
                    except Exception:
                        pass
                    time.sleep(0.3)
                    msg_box.send_keys(Keys.CONTROL, 'v')
                    log_status("📎 Image attached (Method C)")
                
                # 4. Wait for Image Media Preview Modal
                media_preview_found = False
                for _ in range(10):
                    media_containers = driver.find_elements(By.XPATH, 
                        "//div[@data-testid='media-caption-input-container'] | "
                        "//div[@data-testid='image-preview'] | "
                        "//div[@data-testid='media-editor'] | "
                        "//div[contains(@class, 'media-panel')]"
                    )
                    if len(media_containers) > 0:
                        media_preview_found = True
                        break
                    time.sleep(0.5)
                
                if not media_preview_found:
                    raise Exception("Image preview modal NEVER appeared. Skipping to avoid text-only send.")
                
                # Find the caption input inside the media preview
                caption_selectors = [
                    "//div[@data-testid='media-caption-input-container']//div[@contenteditable='true']",
                    "//div[@data-testid='media-caption-input-container']//p",
                    "//div[contains(@class, 'media-caption')]//div[@contenteditable='true']",
                    "//div[contains(@aria-label, 'caption') or contains(@aria-label, 'Caption')]"
                ]
                caption_box = None
                for _ in range(4):
                    for sel in caption_selectors:
                        try:
                            el = driver.find_element(By.XPATH, sel)
                            if el.is_displayed():
                                caption_box = el
                                break
                        except Exception:
                            continue
                    if caption_box:
                        break
                    time.sleep(0.5)
                    
                if not caption_box:
                    raise Exception("Caption input not found in image preview.")
                    
                try:
                    driver.execute_script("arguments[0].focus();", caption_box)
                    caption_box.click()
                except Exception:
                    pass
                time.sleep(0.2)
                
                # Paste caption text
                pyperclip.copy(message_text)
                caption_box.send_keys(Keys.CONTROL, 'v')
                time.sleep(0.3)
                
                # Send (Enter + Send Button)
                caption_box.send_keys(Keys.ENTER)
                time.sleep(0.3)
                
                send_btn_selectors = [
                    "//span[@data-icon='send']",
                    "//div[@role='button'][@aria-label='Send']",
                    "//span[@data-testid='send']",
                    "//button[@aria-label='Send']"
                ]
                for sel in send_btn_selectors:
                    send_btns = driver.find_elements(By.XPATH, sel)
                    if len(send_btns) > 0:
                        try:
                            driver.execute_script("arguments[0].click();", send_btns[0])
                        except Exception:
                            pass
                        break
                
                # 5. Wait for upload to finish (preview modal disappears)
                for _ in range(15):
                    previews = driver.find_elements(By.XPATH, "//div[@data-testid='media-caption-input-container']")
                    if len(previews) == 0:
                        break
                    time.sleep(0.5)
                    
                time.sleep(1)
                log_status(f"✅ Sent to {group_name}!")
                
            except Exception as e:
                log_status(f"❌ Failed for {group_name}: {str(e)}")
                time.sleep(2)
                continue
                
        log_status("🎉 Broadcast complete! All done.")
        
    except Exception as e:
        log_status(f"💥 Critical Error: {str(e)}")
    finally:
        if driver:
            driver.quit()
        is_running = False
        log_status("🛑 Browser closed.")

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/groups', methods=['GET', 'POST'])
def handle_api_groups():
    if request.method == 'POST':
        groups = request.json
        save_groups(groups)
        return jsonify({"status": "success"})
    return jsonify(load_groups())

@app.route('/api/broadcast', methods=['POST'])
def start_broadcast():
    global is_running
    if is_running:
        return jsonify({"status": "error", "message": "Broadcast is already running."}), 400
        
    message_text = request.form.get('message', '')
    
    # Handle image upload
    if 'image' not in request.files:
        return jsonify({"status": "error", "message": "No image file uploaded."}), 400
        
    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({"status": "error", "message": "Empty file name."}), 400
        
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'broadcast_image.png')
    image_file.save(image_path)
    
    # Get list of selected groups
    groups = load_groups()
    active_groups = [g['name'] for g in groups if g.get('selected', False)]
    
    if not active_groups:
        return jsonify({"status": "error", "message": "No groups selected."}), 400
        
    # Start thread
    thread = threading.Thread(target=run_selenium_broadcast, args=(active_groups, message_text, image_path))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "success", "message": "Broadcast started in background."})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({"is_running": is_running})

@app.route('/stream')
def stream_logs():
    def event_stream():
        # Clear queue
        while not log_queue.empty():
            try:
                log_queue.get_nowait()
            except queue.Empty:
                break
        while True:
            try:
                msg = log_queue.get(timeout=2.0)
                yield f"data: {msg}\n\n"
            except queue.Empty:
                yield "data: \n\n"
    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == '__main__':
    app.run(debug=True, port=5000)
