# WhatsApp Web Broadcast Dashboard

A local Flask web application that automates sending images with captions to multiple WhatsApp contacts or groups at the same time.

It uses Python, Flask, and Selenium WebDriver.

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Ayo45-alt/whatsapp-automation.git
   cd whatsapp-automation
   ```

2. Set up the virtual environment and install dependencies:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```
   This will start the Flask server and open the dashboard in your default browser at http://127.0.0.1:5000.

## Warning
The whatsapp_profile_copy/ folder is listed in .gitignore to prevent uploading your active login session data to GitHub. Do not remove it from the ignore list.
