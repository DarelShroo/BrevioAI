import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

class EmailService:
    def __init__(self, email_to, subject):
        self.email_to = "cls18drl@gmail.com"
        self.subject = subject
        self.email_from = os.getenv("EMAIL_FROM")
        self.password = os.getenv("EMAIL_PASSWORD")
        
        self.message = MIMEMultipart("alternative")
        self.message["Subject"] = self.subject
        self.message["From"] = self.email_from
        self.message["To"] = self.email_to

        texto_plano = "Hola, este es un mensaje de prueba."
        html = """\
        <html>
        <body>
            <p>Hola,<br>
            Este es un <strong>correo de prueba</strong>.
            </p>
        </body>
        </html>
        """
        parte_texto = MIMEText(texto_plano, "plain")
        parte_html = MIMEText(html, "html")

        self.message.attach(parte_texto)
        self.message.attach(parte_html)

    def send_email(self):
        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
                servidor.starttls()
                servidor.login(self.email_from, self.password)
                servidor.sendmail(self.email_from, self.email_to, self.message.as_string())
            print("Correo enviado exitosamente.")
        except Exception as e:
            print(f"Error al enviar el correo: {e}")

if __name__ == "__main__":
    email_to = "destinatario@example.com"
    subject = "Prueba de Correo Electrónico"

    email_service = EmailService(email_to, subject)
    email_service.send_email()