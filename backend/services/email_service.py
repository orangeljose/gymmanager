"""
Servicio de envío de emails usando Resend
"""
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Resend API key - configurar en variables de entorno
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
RESEND_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL', 'onboarding@resend.dev')

# Intentar importar resend (opcional)
try:
    import resend
    HAS_RESEND = True
except ImportError:
    HAS_RESEND = False
    logger.warning("Resend no instalado - los emails no se enviarán")


def sendInvitationEmail(to_email: str, invitation_data: dict) -> dict:
    """
    Envía email de invitación a un nuevo usuario.

    Args:
        to_email: Email del invitado
        invitation_data: Diccionario con:
            - role: rol asignado (admin, cashier, etc.)
            - invitedByName: nombre de quien invitó
            - invitationLink: link completo de aceptación
            - businessName: nombre del negocio (opcional)
            - expiresAt: fecha de expiración (opcional)

    Returns:
        Dict con 'success' y datos o 'error'
    """
    if not RESEND_API_KEY:
        logger.warning(f"Email de invitación no enviado a {to_email} - RESEND_API_KEY no configurado")
        return {'success': False, 'error': 'Email service not configured'}

    if not HAS_RESEND:
        logger.warning(f"Email de invitación no enviado a {to_email} - resend no instalado")
        return {'success': False, 'error': 'Resend package not installed'}

    # Configurar la API key de resend
    resend.api_key = RESEND_API_KEY

    role_labels = {
        'admin': 'Administrador',
        'branch_admin': 'Encargado de Sucursal',
        'cashier': 'Cajero',
        'trainer': 'Entrenador'
    }
    role_label = role_labels.get(invitation_data.get('role', ''), invitation_data.get('role', ''))
    business_name = invitation_data.get('businessName', 'Gimnasio')
    invited_by = invitation_data.get('invitedByName', 'Un administrador')
    invitation_link = invitation_data.get('invitationLink', '')

    try:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f4f4f5; margin: 0; padding: 40px 20px; }}
                .container {{ max-width: 560px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
                .header {{ background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 32px; text-align: center; }}
                .header h1 {{ margin: 0 0 8px 0; font-size: 24px; font-weight: 600; }}
                .header p {{ margin: 0; opacity: 0.9; font-size: 14px; }}
                .body {{ padding: 32px; }}
                .body h2 {{ margin: 0 0 16px 0; color: #1f2937; font-size: 18px; }}
                .body p {{ color: #6b7280; line-height: 1.6; margin: 0 0 16px 0; font-size: 15px; }}
                .role-badge {{ display: inline-block; background: #eef2ff; color: #6366f1; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 500; margin-bottom: 20px; }}
                .cta-button {{ display: inline-block; background: #6366f1; color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 15px; margin: 24px 0; }}
                .cta-button:hover {{ background: #5558e3; }}
                .footer {{ background: #f9fafb; padding: 20px 32px; border-top: 1px solid #e5e7eb; }}
                .footer p {{ color: #9ca3af; font-size: 12px; margin: 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>GymManager</h1>
                    <p>Has sido invitado a unirte</p>
                </div>
                <div class="body">
                    <span class="role-badge">Rol: {role_label}</span>
                    <h2>¡Hola! Te han invitado a {business_name}</h2>
                    <p><strong>{invited_by}</strong> te ha invitado a unirte a GymManager como <strong>{role_label}</strong>.</p>
                    <p>Hace clic en el botón de abajo para crear tu cuenta y comenzar a usar la plataforma.</p>
                    <center>
                        <a href="{invitation_link}" class="cta-button">Aceptar Invitación</a>
                    </center>
                    <p style="font-size: 13px; color: #9ca3af;">Si no puedes hacer clic en el botón, copia y pega este enlace en tu navegador:<br>
                    <a href="{invitation_link}" style="color: #6366f1; word-break: break-all;">{invitation_link}</a></p>
                </div>
                <div class="footer">
                    <p>Este enlace expira en 72 horas. Si no solicitaste esta invitación, puedes ignorar este email.</p>
                </div>
            </div>
        </body>
        </html>
        """

        params: resend.Emails.SendParams = {
            'from': RESEND_FROM_EMAIL,
            'to': [to_email],
            'subject': f'Invitación para unirte a {business_name} como {role_label}',
            'html': html_content
        }

        response = resend.Emails.send(params)

        logger.info(f"Email de invitación enviado a {to_email}: {response.get('id')}")
        return {'success': True, 'id': response.get('id')}

    except Exception as e:
        logger.error(f"Error enviando email a {to_email}: {str(e)}")
        return {'success': False, 'error': str(e)}