# WhatsApp Web Broadcast Dashboard

A modern local web dashboard to automate sending images and caption messages together to multiple WhatsApp contacts or groups simultaneously. 

Built with **Flask**, **HTML5/CSS3/JavaScript**, and **Selenium WebDriver**.

---

## 🚀 Features

* **Drag & Drop Image Upload:** Easily drag-and-drop or select an image file to broadcast.
* **Caption Message Box:** Fully supports styled text, emojis, and multiline text.
* **Combined Message:** Sends the image and caption text together in a single message (does not split them).
* **Target Contact Manager:** Easily add, edit, select, or remove target contacts and groups. Saved lists are persisted locally.
* **Live Execution Logs:** Real-time log terminal streaming status updates directly to the web dashboard.
* **Robust Automation:** Uses active elements and state-based wait thresholds to avoid stale elements or WhatsApp loading lags.

---

## 🛠️ Setup & Installation

1. **Clone the Repository:**
   ```bash
   git clone <your-repository-url>
   cd <repository-folder>
   ```

2. **Set up Virtual Environment:**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Launcher:**
   ```bash
   python main.py
   ```
   *The script will launch the local web server and automatically open the dashboard in your default browser at `http://127.0.0.1:5000`.*

---

## ⚠️ Important Security Warning

> [!CAUTION]
> **Never upload your WhatsApp login session folder to GitHub!**
> This project is configured to ignore the `whatsapp_profile_copy/` directory using `.gitignore`. This folder contains your active session cookies, local storage tokens, and private login credentials. Pushing this folder publicly will compromise your WhatsApp account.
