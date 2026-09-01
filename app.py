from flask import Flask, render_template, request, jsonify, Response
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import win32clipboard
import pyperclip
import io
import time
import os
import json
import queue
import threading

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

GROUPS_FILE = os.path.join(os.getcwd(), 'groups.json')
log_queue = queue.Queue()
is_running = False

def log_status(msg):
    log_queue.put(msg)
    print(msg)

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
        options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        
        driver = webdriver.Chrome(options=options)
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
        reconnect_xpath = "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reconnect')]"
        
        success = False
        start_time = time.time()
        while time.time() - start_time < 300:  # 5 minutes timeout
            # Check for "Use here" dialog
            use_here_elements = driver.find_elements(By.XPATH, use_here_xpath)
            if len(use_here_elements) > 0:
                log_status("⚠️ Detected 'Use here' popup. Activating session in this window...")
                try:
                    driver.execute_script("arguments[0].click();", use_here_elements[0])
                except Exception:
                    pass
                time.sleep(3)
                continue
                
            # Check for Reconnect button
            reconnect_elements = driver.find_elements(By.XPATH, reconnect_xpath)
            if len(reconnect_elements) > 0:
                log_status("⚠️ Detected network disconnect. Clicking Reconnect...")
                try:
                    driver.execute_script("arguments[0].click();", reconnect_elements[0])
                except Exception:
                    pass
                time.sleep(3)
                continue

            # Check if search box or chat pane is loaded
            found_search = False
            for sel in search_box_selectors:
                elements = driver.find_elements(By.XPATH, sel)
                if len(elements) > 0:
                    found_search = True
                    break
            
            # Also check if sidebar chat pane exists
            pane_side = driver.find_elements(By.ID, "pane-side")
            if found_search or len(pane_side) > 0:
                log_status("✅ WhatsApp Web loaded successfully!")
                success = True
                break
                
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
                time.sleep(0.5)
                
                # Select all and delete to clear existing text
                search_box.send_keys(Keys.CONTROL + "a")
                time.sleep(0.2)
                search_box.send_keys(Keys.BACKSPACE)
                time.sleep(0.5)
                
                # Paste group name via clipboard for accurate typing
                pyperclip.copy(group_name)
                search_box.send_keys(Keys.CONTROL + "v")
                
                # 2. Wait dynamically for search results to load
                time.sleep(3.5)
                
                # Check for matching list items
                list_items = driver.find_elements(By.XPATH, '//div[@id="pane-side"]//div[@role="listitem"]')
                if len(list_items) == 0:
                    log_status(f"⚠️ No matches found in search for: {group_name}")
                    # Clear search bar before continuing
                    search_box.send_keys(Keys.CONTROL + "a", Keys.BACKSPACE)
                    continue
                    
                # Click the first search result item
                try:
                    driver.execute_script("arguments[0].click();", list_items[0])
                except Exception:
                    try:
                        list_items[0].click()
                    except Exception:
                        search_box.send_keys(Keys.ENTER)
                
                time.sleep(2)
                
                # 3. Copy image to clipboard and paste
                copy_image_to_clipboard(image_path)
                time.sleep(1)
                
                # Locate message input compose box
                msg_box_selectors = [
                    "//div[@data-testid='conversation-compose-box-input']",
                    "//footer//div[@contenteditable='true']",
                    "//div[@role='textbox'][@data-tab='10']"
                ]
                msg_box = None
                for sel in msg_box_selectors:
                    try:
                        msg_box = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, sel))
                        )
                        if msg_box:
                            break
                    except Exception:
                        continue
                        
                if not msg_box:
                    raise Exception("Could not open chat input box for group.")
                    
                msg_box.click()
                time.sleep(0.5)
                msg_box.send_keys(Keys.CONTROL, 'v')
                
                # 4. Wait for image caption preview box
                caption_selectors = [
                    "//div[@data-testid='media-caption-input-container']",
                    "//div[contains(@class, 'caption')]//div[@contenteditable='true']",
                    "//div[@contenteditable='true'][@data-tab='10']"
                ]
                caption_box = None
                for sel in caption_selectors:
                    try:
                        caption_box = WebDriverWait(driver, 10).until(
                            EC.visibility_of_element_located((By.XPATH, sel))
                        )
                        if caption_box:
                            break
                    except Exception:
                        continue
                        
                if not caption_box:
                    raise Exception("Image preview modal did not appear.")
                    
                caption_box.click()
                time.sleep(0.5)
                
                # Paste caption text
                pyperclip.copy(message_text)
                caption_box.send_keys(Keys.CONTROL, 'v')
                time.sleep(1)
                
                # Send the message
                caption_box.send_keys(Keys.ENTER)
                
                # 5. Wait dynamically for upload to finish (preview modal disappears)
                upload_done = False
                for _ in range(15):
                    previews = driver.find_elements(By.XPATH, "//div[@data-testid='media-caption-input-container']")
                    if len(previews) == 0:
                        upload_done = True
                        break
                    time.sleep(1)
                    
                time.sleep(3)
                log_status(f"✅ Successfully sent to {group_name}!")
                
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
