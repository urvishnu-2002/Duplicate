
import ssl
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend

class EmailBackend(SMTPBackend):
    def open(self):
        if self.connection:
            return False
        try:
            # Create a context that doesn't verify certificates
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
            self.connection = self.connection_class(self.host, self.port, **self.connection_kwargs)
            # Proceed with the rest of the connection logic (starttls, login)
            # We must manually call open() logic because we can't easily inject context into super().open()
            # So instead, we just override how the context is used if we could.
            # However, simpler approach: blindly trust the connection.
            # But django's open() creates the connection.
            # Let's use a simpler override that sets the ssl_context on the instance before calling open.
            pass
        except:
            pass
        return super().open()

# Wait, the above logic is flawed because super().open() creates the context itself if not provided.
# Correct approach:

class DataFlownEmailBackend(SMTPBackend):
    def _get_ssl_context(self):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def open(self):
        # We override open to inject our context if needed, but actually 
        # Django's SMTPBackend doesn't easily allow injecting context unless we pass it to __init__.
        # But we can override the ssl_context property if it existed, or just patch ssl.
        
        # Method 2: Patch ssl.create_default_context strictly for this call (risky).
        # Method 3 (Best for Django): Pass ssl_context to the connection.
        
        # Django < 3.0: didn't make this easy.
        # Django >= 3.0: explicit support?
        
        # Actually, let's just use the standard workaround for "535" which is ensuring settings are perfect.
        # If 535 is AUTH error, SSL bypass won't fix it (SSL error would be "Certificate Verify Failed").
        # You are getting "Username and Password not accepted".
        # This means SSL *worked*.
        
        return super().open()
