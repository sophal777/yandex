import imaplib
import email
from email.header import decode_header
import re
import time

IMAP_SERVER = "imap.yandex.com"
EMAIL = "XXXXXXXX@yandex.com"
PASSWORD = "XXXXXXX" 


def decode_str(val):
    if not val:
        return ""
    txt, enc = decode_header(val)[0]
    return txt.decode(enc or "utf-8", errors="ignore") if isinstance(txt, bytes) else str(txt)


def get_all_fb_codes_yandex():
    results = []

    with imaplib.IMAP4_SSL(IMAP_SERVER, 993) as mail:
        mail.login(EMAIL, PASSWORD)
        mail.select("INBOX")

        # ស្វែងរកសារទាំងអស់ដែលមកពី Facebook
        _, data = mail.search(None, '(FROM "facebookmail.com")')
        ids = data[0].split()

        total_messages = len(ids)
        print(f"ចំនួនសារសរុបដែលរកឃើញ: {total_messages}")

        # អានសារម្តងមួយៗតាមចំនួនសារទាំងអស់ដែលមាន
        for msg_id in ids:
            # ទាញយកតែ Subject និង To មកមើល (ដំណើរការលឿន មិនបាច់ទាញ Body ទាំងមូល)
            _, header_data = mail.fetch(msg_id, "(BODY.PEEK[HEADER.FIELDS (SUBJECT TO)])")
            msg = email.message_from_bytes(header_data[0][1])

            subject = decode_str(msg.get("Subject"))
            to_header = decode_str(msg.get("To"))

            # ចាប់យកលេខកូដ ៥ ខ្ទង់
            code_match = re.search(r"\b(\d{5})\b", subject)
            # ចាប់យក Email (Yandex)
            email_match = re.search(r"[\w\.-]+\+?[\w\.-]*@yandex\.com", to_header)

            # ប្រសិនបើសារនោះមានកូដបញ្ជាក់ Facebook
            if code_match:
                item = {
                    "email": email_match.group(0) if email_match else "រកមិនឃើញ Email",
                    "code": code_match.group(1),
                    "subject": subject
                }
                results.append(item)

    return results


# ដំណើរការអានទិន្នន័យ
codes_list = get_all_fb_codes_yandex()
unique_accounts = {}
for item in codes_list:
    email_key = item["email"]
    code_val = item["code"]
    # បើអ៊ីមែលដូចគ្នា វានឹង Update យកកូដថ្មីចុងក្រោយដោយស្វ័យប្រវត្តិ
    unique_accounts[email_key] = code_val
# សរសេរទិន្នន័យចូល File (ប្រើ mode 'w' ដើម្បីសរសេរជាន់ថ្មី ឬ 'a' បន្ថែម)
with open("accounts.txt", "w", encoding="utf-8") as file:
    for idx, (email_addr, code) in enumerate(unique_accounts.items(), 1):
        print(f"[{idx}] {email_addr}  ==>  {code}")
        file.write(f"{email_addr}|{code}\n")







def count_emails():
    try:
        mail = imaplib.IMAP4_SSL("imap.yandex.com", 993)
        mail.login(EMAIL, PASSWORD)
        mail.select("INBOX", readonly=True)

        _, total = mail.search(None, "ALL")
        _, unread = mail.search(None, "UNSEEN")

        total_count = len(total[0].split())
        unread_count = len(unread[0].split())

        print(f"[*] Total: {total_count}")
        print(f"[*] Unread: {unread_count}")

        mail.logout()
        return total_count, unread_count

    except Exception as e:
        print(f"[-] Error: {e}")
        return 0, 0


# ==================== DELETE ALL EMAILS ====================

def delete_all_emails():
    try:
        mail = imaplib.IMAP4_SSL("imap.yandex.com", 993)
        mail.login(EMAIL, PASSWORD)
        mail.select("INBOX")

        _, data = mail.search(None, "ALL")
        ids = data[0].split()

        if ids:
            mail.store(b",".join(ids), "+FLAGS", "\\Deleted")
            mail.expunge()

        print(f"[+] Deleted: {len(ids)} Emails")

        mail.logout()

    except Exception as e:
        print(f"[-] Error: {e}")








