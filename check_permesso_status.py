import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

from check_permesso_accounts import accounts  # Your login info

# --- EMAIL SETTINGS ---
email_sender = "joespinelle@gmail.com"
import os
email_password = os.environ.get("EMAIL_PASSWORD")
always_send = ["joespinelle@gmail.com"]
dad_email = "briggsjs@earthlink.net"
sue_email = "susib50@yahoo.com"
alisa_email = "shadowcat1017@yahoo.com"

# --- LOG START ---
import os
script_dir = os.path.dirname(__file__)
log_path = os.path.join(script_dir, "dad_task_log.txt")

with open(log_path, "a", encoding="utf-8") as log:
    log.write(f"{datetime.now()}: Task started\n")

# --- URL ---
login_url = "https://www.portaleimmigrazione.it/ELI2ImmigrazioneWEB/Pagine/StartPage.aspx"
iframe_url = "https://www.portaleimmigrazione.it/ELI2ImmigrazioneWEB/Pagine/VisualizzaIstanza.aspx"

# --- INIT ---
results = []
status_changed = False  # Track if either Dad or Sue had a change

# --- MAIN LOOP ---
for account in accounts:
    print(f"🔐 Logging in for {account['name']}...")
    session = requests.Session()

    # Step 1: GET login page
    response = session.get(login_url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Step 2: Collect all hidden input fields
    form_data = {}
    for inp in soup.find_all("input", type="hidden"):
        name = inp.get("name")
        value = inp.get("value", "")
        if name:
            form_data[name] = value

    # Step 3: Add login credentials
    form_data.update({
        "UC_LogIn1:txtUtente": account["username"],
        "UC_LogIn1:txtPassword": account["password"],
        "UC_LogIn1:btnConferma": "Accedi"
    })

    # Step 4: POST login form
    login_response = session.post(login_url, data=form_data)
    with open(f"debug_login_{account['name']}.html", "w", encoding="utf-8") as f:
        f.write(login_response.text)

    # Step 5: Check login success
    if "logout" in login_response.text.lower() or "Benvenuto" in login_response.text:
        print(f"✅ Login successful for {account['name']}")

        # Step 6: GET iframe status page
        iframe_response = session.get(iframe_url)
        iframe_soup = BeautifulSoup(iframe_response.text, "html.parser")

        # Step 7: Extract "Stato Attuale"
        status_span = iframe_soup.find("span", id="txtTRACCIATURA_STATOATTUALE")
        status = status_span.text.strip() if status_span else "⚠️ Stato non trovato"

        # Step 8: Load previous status and compare
        status_file = f"status_{account['name'].lower()}.txt"
        previous_status = ""
        has_changed = False

        if os.path.exists(status_file):
            with open(status_file, "r", encoding="utf-8") as f:
                previous_status = f.read().strip()
            has_changed = (status != previous_status)

        else:
            previous_status = "(first check)"
            has_changed = True

        # Save current status
        with open(status_file, "w", encoding="utf-8") as f:
            f.write(status)

        # Flag if Dad or Sue changed
        if has_changed and account['name'].lower() in ["dad", "sue"]:
            status_changed = True

        # Add to subject line
        status_display = f"{status} 🆕" if has_changed else status
        account['status_subject'] = status_display

        # Step 9: Extract "Convocazione"
        convocazione_li = iframe_soup.select_one("li[id]")
        convocazione_text = convocazione_li.get_text(separator="\n").strip() if convocazione_li else "Nessuna convocazione trovata."

        # Step 10: Format result
        user_result = f"{account['name']}\n📄 Stato: {status}\n📍 Convocazione:\n{convocazione_text}"
        results.append(user_result)

    else:
        print(f"❌ Login failed for {account['name']}")
        account["status_subject"] = "❌ Login failed"
        results.append(f"{account['name']}: ❌ Login failed")

# --- EMAIL ---
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
email_body = f"Permesso check at {timestamp}\n\n" + "\n\n".join(results)

# Compose subject line with all statuses
subject_parts = [f"{acc['name']}: {acc.get('status_subject', '❓')}" for acc in accounts]
email_subject = "; ".join(subject_parts)

msg = MIMEText(email_body)
msg["Subject"] = email_subject
msg["From"] = email_sender

# Determine recipients
conditional_recipients = []
if status_changed:
    conditional_recipients = [dad_email, sue_email, alisa_email]

# Combine all unique recipients
all_recipients = list(set(always_send + conditional_recipients))
msg["To"] = ", ".join(all_recipients)

with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
    server.login(email_sender, email_password)
    server.send_message(msg)

print("📬 Email sent with login results.")
