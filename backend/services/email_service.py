import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

class EmailService:
    def __init__(self, email_to, subject):
        self.email_to = email_to
        self.subject = subject
        self.email_from = os.getenv("EMAIL_FROM")
        self.password = os.getenv("EMAIL_PASSWORD")

        self.message = MIMEMultipart("alternative")
        self.message["Subject"] = self.subject
        self.message["From"] = self.email_from
        self.message["To"] = self.email_to

    def send_register_email(self):
        texto_plano = "Bienvenido a nuestra plataforma. ¡Gracias por registrarte!"
        html = """\
<html>
<head>
  <style>
    /* Estilos generales */
    body {
      background-color: #f4f4f4;
      margin: 0;
      padding: 0;
      font-family: Arial, sans-serif;
    }
    .email-container {
      width: 100%;
      margin: 0;
      background-color: #ffffff;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    .header {
      background: linear-gradient(135deg, #073642, #002B36);
      padding: 20px;
      text-align: center;
    }
    .header h1 {
      margin: 0;
      color: #ffffff;
      font-size: 24px;
      font-weight: normal;
    }
    .content {
      padding: 20px;
      color: #333333;
      line-height: 1.6;
    }
    .content p {
      margin: 0 0 15px;
      font-size: 16px;
    }
    .highlight {
      color: #2AA198;
      font-weight: bold;
    }
    .cta-button {
      display: inline-block;
      background-color: #2AA198;
      color: #ffffff !important;
      text-decoration: none;
      padding: 12px 20px;
      border-radius: 4px;
      font-size: 16px;
      margin-top: 10px;
    }
    .footer {
      background-color: #f4f4f4;
      text-align: center;
      padding: 15px;
      font-size: 14px;
      color: #777777;
      border-top: 1px solid #e0e0e0;
    }
  </style>
</head>
<body>
  <div class="email-container">
    <div class="header">
      <h1>Bienvenido a Brevio</h1>
    </div>
    <div class="content">
      <p>Hola,</p>
      <p><span class="highlight">¡Gracias por registrarte!</span></p>
      <p>Explora algunas de nuestras funcionalidades...</p>
      <p><a href="#" class="cta-button">Acceder a Mi Cuenta</a></p>
    </div>
    <div class="footer">
      <p>© 2025 Brevio. Todos los derechos reservados.</p>
    </div>
  </div>
</body>
</html>
        """
        parte_texto = MIMEText(texto_plano, "plain")
        parte_html = MIMEText(html, "html")
        self.message.attach(parte_texto)
        self.message.attach(parte_html)

        self.send_email()

    def send_recovery_password_email(self, otp: str):
        texto_plano = f"Tu código de recuperación es: {otp}. Este código es válido por 10 minutos."
        html = f"""\
<html>
<head>
  <style>
    /* Estilos generales */
    body {{
      background-color: #f4f4f4;
      margin: 0;
      padding: 0;
      font-family: Arial, sans-serif;
    }}
    .email-container {{
      width: 100%;
      margin: 0;
      background-color: #ffffff;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }}
    .header {{
      background: linear-gradient(135deg, #073642, #002B36);
      padding: 20px;
      text-align: center;
    }}
    .header h1 {{
      margin: 0;
      color: #ffffff;
      font-size: 24px;
      font-weight: normal;
    }}
    .content {{
      padding: 20px;
      color: #333333;
      line-height: 1.6;
    }}
    .content p {{
      margin: 0 0 15px;
      font-size: 16px;
    }}
    .cta-button {{
      display: inline-block;
      background-color: #2AA198;
      color: #ffffff !important;
      text-decoration: none;
      padding: 12px 20px;
      border-radius: 4px;
      font-size: 16px;
      margin-top: 10px;
    }}
    .footer {{
      background-color: #f4f4f4;
      text-align: center;
      padding: 15px;
      font-size: 14px;
      color: #777777;
      border-top: 1px solid #e0e0e0;
    }}
  </style>
</head>
<body>
  <div class="email-container">
    <div class="header">
      <h1>Recuperación de Contraseña</h1>
    </div>
    <div class="content">
      <p>Recupera tu contraseña utilizando el siguiente código:</p>
      <p><span class="highlight" style="font-size: 20px;">{otp}</span></p>
      <p>Este código es válido por 10 minutos.</p>
    </div>
    <div class="footer">
      <p>© 2025 Brevio. Todos los derechos reservados.</p>
    </div>
  </div>
</body>
</html>
        """
        parte_texto = MIMEText(texto_plano, "plain")
        parte_html = MIMEText(html, "html")
        self.message.attach(parte_texto)
        self.message.attach(parte_html)

        self.send_email()

    def send_email(self):
        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
                servidor.starttls()
                servidor.login(self.email_from, self.password)
                servidor.sendmail(self.email_from, self.email_to,
                                  self.message.as_string())
            print("Correo enviado exitosamente.")
        except Exception as e:
            print(f"Error al enviar el correo: {e}")

    def send_password_changed_email(self):
      texto_plano = "Tu contraseña ha sido cambiada exitosamente. Si no realizaste este cambio, por favor contacta con nuestro soporte."
      html = """\
  <html>
  <head>
    <style>
      /* Estilos generales */
      body {{
        background-color: #f4f4f4;
        margin: 0;
        padding: 0;
        font-family: Arial, sans-serif;
      }}
      .email-container {{
        width: 100%;
        margin: 0;
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      }}
      .header {{
        background: linear-gradient(135deg, #073642, #002B36);
        padding: 20px;
        text-align: center;
      }}
      .header h1 {{
        margin: 0;
        color: #ffffff;
        font-size: 24px;
        font-weight: normal;
      }}
      .content {{
        padding: 20px;
        color: #333333;
        line-height: 1.6;
      }}
      .content p {{
        margin: 0 0 15px;
        font-size: 16px;
      }}
      .footer {{
        background-color: #f4f4f4;
        text-align: center;
        padding: 15px;
        font-size: 14px;
        color: #777777;
        border-top: 1px solid #e0e0e0;
      }}
    </style>
  </head>
  <body>
    <div class="email-container">
      <div class="header">
        <h1>Contraseña Actualizada</h1>
      </div>
      <div class="content">
        <p>Hola,</p>
        <p><strong>Tu contraseña ha sido cambiada exitosamente.</strong></p>
        <p>Si no realizaste este cambio, por favor contacta inmediatamente con nuestro soporte.</p>
      </div>
      <div class="footer">
        <p>© 2025 Brevio. Todos los derechos reservados.</p>
      </div>
    </div>
  </body>
  </html>
      """
      parte_texto = MIMEText(texto_plano, "plain")
      parte_html = MIMEText(html, "html")
      self.message.attach(parte_texto)
      self.message.attach(parte_html)

      self.send_email()
