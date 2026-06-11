import ssl
import smtplib
from django.core.mail.backends.smtp import EmailBackend

class CustomEmailBackend(EmailBackend):
    def open(self):
        if self.connection:
            return False
        connection_params = {}
        if self.timeout is not None:
            connection_params['timeout'] = self.timeout
        try:
            self.connection = smtplib.SMTP(self.host, self.port, **connection_params)
            if self.use_tls:
                self.connection.ehlo()
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                self.connection.starttls(context=context)
                self.connection.ehlo()
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except Exception:
            if not self.fail_silently:
                raise