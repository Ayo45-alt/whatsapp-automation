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
        search_box_xpath = "//input[@aria-label='Search or start a new chat']"
        use_here_xpath = "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'use here')]"
        
        success = False
        start_time = time.time()
        while time.time() - start_time < 300:  # 5 minutes timeout
            # 1. Check if logged in successfully
            search_elements = driver.find_elements(By.XPATH, search_box_xpath)
            if len(search_elements) > 0:
                log_status("✅ WhatsApp Web loaded successfully!")
                success = True
                break
                
            # 2. Check for "Use here" dialog
            use_here_elements = driver.find_elements(By.XPATH, use_here_xpath)
            if len(use_here_elements) > 0:
                log_status("⚠️ Detected 'Use here' popup. Activating session in this window...")
                try:
                    use_here_elements[0].click()
                except Exception:
                    try:
                        driver.execute_script("arguments[0].click();", use_here_elements[0])
                    except Exception:
                        pass
                time.sleep(2)
                continue
                
            time.sleep(2)
            
        if not success:
            raise TimeoutError("Timed out waiting for WhatsApp Web. If you saw a QR code, 300 seconds was not enough to scan it. Please try again.")
        
        for idx, group_name in enumerate(groups_to_send):
            try:
                log_status(f"💬 [{idx+1}/{len(groups_to_send)}] Processing: {group_name}")
                
                # Search for chat
                search_box = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, search_box_xpath))
                )
                search_box.click()
                time.sleep(0.5)
                
                active_el = driver.switch_to.active_element
                active_el.clear()
                active_el.send_keys(group_name)
                time.sleep(3.0) # Wait for search results
                
                # Check if search returned any contacts/groups in the side pane
                list_items = driver.find_elements(By.XPATH, '//div[@id="pane-side"]//div[@role="listitem"]')
                if len(list_items) == 0:
                    log_status(f"⚠️ No matches found in search for: {group_name}")
                    continue
                    
                # Click the first search result to open the chat
                try:
                    list_items[0].click()
                except Exception:
                    # Fallback to pressing ENTER
                    active_el = driver.switch_to.active_element
                    active_el.send_keys(Keys.ENTER)
                
                time.sleep(2)
                
                # Copy and paste image
                copy_image_to_clipboard(image_path)
                time.sleep(1)
                
                msg_box = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@data-testid='conversation-compose-box-input']"))
                )
                msg_box.click()
                time.sleep(0.5)
                msg_box.send_keys(Keys.CONTROL, 'v')
                
                # Caption box
                caption_box = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.XPATH, "//div[@data-testid='media-caption-input-container']"))
                )
                caption_box.click()
                time.sleep(0.5)
                
                # Paste caption
                pyperclip.copy(message_text)
                caption_box.send_keys(Keys.CONTROL, 'v')
                time.sleep(1)
                
                # Send
                caption_box.send_keys(Keys.ENTER)
                log_status(f"✅ Successfully sent to {group_name}!")
                
                # Wait for upload
                time.sleep(4)
                
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
