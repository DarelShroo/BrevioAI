import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from fastapi import HTTPException, status
from jinja2 import Environment, FileSystemLoader


class EmailService:
    def __init__(self, email_to: str, subject: str) -> None:
        self.email_to: str = email_to
        self.subject: str = subject
        template_folder: str = os.path.join(os.path.dirname(__file__), "../templates")
        self.env = Environment(loader=FileSystemLoader(template_folder))

        email_from: Optional[str] = os.getenv("EMAIL_FROM")
        password: Optional[str] = os.getenv("EMAIL_PASSWORD")

        if email_from is None:
            raise ValueError("EMAIL_FROM environment variable is not set")
        if password is None:
            raise ValueError("EMAIL_PASSWORD environment variable is not set")

        self.email_from: str = email_from
        self.password: str = password

        self.message: MIMEMultipart = MIMEMultipart("alternative")
        self.message["Subject"] = self.subject
        self.message["From"] = self.email_from
        self.message["To"] = self.email_to

    def render_template(self, template_name: str, context: dict) -> str:
        template = self.env.get_template(template_name)
        return template.render(context)

    async def send_register_email(self) -> None:
        texto_plano: str = "Bienvenido a nuestra plataforma. ¡Gracias por registrarte!"
        html: str = self.render_template("send_register_email.html", {})
        parte_texto: MIMEText = MIMEText(texto_plano, "plain")
        parte_html: MIMEText = MIMEText(html, "html")
        self.message.attach(parte_texto)
        self.message.attach(parte_html)

        await self.send_email()

    async def send_recovery_password_email(self, otp: str) -> None:
        texto_plano: str = f"Tu código de recuperación es: {otp}. Este código es válido por 10 minutos."
        html: str = self.render_template("send_register_email.html", {})
        parte_texto: MIMEText = MIMEText(texto_plano, "plain")
        parte_html: MIMEText = MIMEText(html, "html")
        self.message.attach(parte_texto)
        self.message.attach(parte_html)

        await self.send_email()

    async def send_password_changed_email(self) -> None:
        texto_plano: str = "Tu contraseña ha sido cambiada exitosamente. Si no realizaste este cambio, por favor contacta con nuestro soporte."
        html: str = self.render_template("send_password_changed_email.html", {})
        parte_texto: MIMEText = MIMEText(texto_plano, "plain")
        parte_html: MIMEText = MIMEText(html, "html")
        self.message.attach(parte_texto)
        self.message.attach(parte_html)

        await self.send_email()

    async def send_email(self) -> None:
        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
                servidor.starttls()
                servidor.login(self.email_from, self.password)
                servidor.sendmail(
                    self.email_from, self.email_to, self.message.as_string()
                )
        except smtplib.SMTPException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error en el envío del correo",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error inesperado al enviar el correo",
            )
