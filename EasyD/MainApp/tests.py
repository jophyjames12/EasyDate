import smtplib
from email.mime.text import MIMEText

smtp_server = 'smtp.gmail.com'
smtp_port = 587
sender_email ="newgateonepiece34@gmail.com"
app_password ="imazxcmvdlmsqioi"

try:
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.ehlo()
    server.starttls()
    server.login(sender_email, app_password)
    # send your email
    server.quit()
except Exception as e:
    print(f"Error: {e}")