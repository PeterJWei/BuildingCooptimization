import requests

def SendEmail(title, body):
	# TODO: verify sending API
    return requests.post(
        "https://api.mailgun.net/v3/sandbox5c480a7a94d14b3f9e4c7b1a52c3440b.mailgun.org/messages",
        auth=("api", "key-e9e526b55efd83ffe1c6a0b2200a5ea8"),
        data={"from": "Mailgun Sandbox <postmaster@sandbox5c480a7a94d14b3f9e4c7b1a52c3440b.mailgun.org>",
              "to": ", Peter <pw2428@columbia.edu>",
              "subject": title,
              "text": body})