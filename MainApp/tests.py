import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from pprint import pprint

# Configure API key authorization
configuration = sib_api_v3_sdk.Configuration()


# Create an instance of the API class
api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

# Define email
send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
    to=[{"email": "fusuy2307@gmail.com", "name": "Recipient"}],
    sender={"email": "newgateonepiece34@gmail.com", "name": "Your Name"},
    subject="Hello from Brevo API",
    html_content="<html><body><h1>This is a test email via Brevo API</h1></body></html>"
)

try:
    # Send the email
    api_response = api_instance.send_transac_email(send_smtp_email)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling TransactionalEmailsApi->send_transac_email: %s\n" % e)
