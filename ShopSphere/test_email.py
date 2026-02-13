
import smtplib
import ssl

port = 587  # For starttls
smtp_server = "smtp.gmail.com"
sender_email = "nandhuuppalapati@gmail.com"
password = "gwojlfspeggsrasr"
receiver_email = "nandhuuppalapati@gmail.com"
message = """\
Subject: Hi there

This message is sent from Python."""

context = ssl.create_default_context()
try:
    server = smtplib.SMTP(smtp_server, port)
    server.ehlo() # Can be omitted
    server.starttls(context=context) # Secure the connection
    server.ehlo() # Can be omitted
    print("Connection established. Attempting login...")
    server.login(sender_email, password)
    print("Login successful! Sending email...")
    server.sendmail(sender_email, receiver_email, message)
    print("Email sent successfully!")
except Exception as e:
    print(f"Error: {e}")
finally:
    try:
        server.quit()
    except:
        pass
