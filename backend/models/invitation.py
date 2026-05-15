"""
Modelos y validaciones para Invitaciones
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import uuid

class InvitationModel:
    """Modelo de invitación para Firestore"""

    # Roles que pueden invitar según jerarquía
    ROLE_CAN_INVITE = {
        'super_admin': ['admin'],
        'admin': ['branch_admin', 'cashier', 'trainer'],
        'branch_admin': [],
        'cashier': [],
        'trainer': []
    }

    # Duración del link de invitación (72 horas)
    INVITATION_EXPIRY_HOURS = 72

    @staticmethod
    def can_invite_role(inviter_role: str, target_role: str) -> bool:
        """Verifica si un rol puede invitar a otro"""
        allowed = InvitationModel.ROLE_CAN_INVITE.get(inviter_role, [])
        return target_role in allowed

    @staticmethod
    def create_invitation_data(
        email: str,
        inviter_data: Dict[str, Any],
        target_role: str,
        invited_name: str = None
    ) -> Dict[str, Any]:
        """
        Crea los datos para una nueva invitación

        Args:
            email: Email del invitado
            inviter_data: Datos del usuario que invita (uid, role, businessId, branchId, name)
            target_role: Rol que se asignará al invitado
            invited_name: Nombre del invitado (opcional)

        Returns:
            Dict con datos de la invitación
        """
        inviter_role = inviter_data.get('role')

        # Validar que puede invitar
        if not InvitationModel.can_invite_role(inviter_role, target_role):
            raise ValueError(f"'{inviter_role}' no puede invitar a '{target_role}'")

        # Generar token único
        token = str(uuid.uuid4())

        # Calcular fecha de expiración
        expires_at = datetime.now() + timedelta(hours=InvitationModel.INVITATION_EXPIRY_HOURS)

        # Construir datos de la invitación
        invitation_data = {
            'token': token,
            'email': email.lower().strip(),
            'name': invited_name,
            'role': target_role,
            'invitedBy': inviter_data.get('uid'),
            'invitedByName': inviter_data.get('name', 'Usuario'),
            'status': 'pending',
            'expiresAt': expires_at.isoformat(),
            'createdAt': datetime.now().isoformat()
        }

        # Agregar businessId y branchId según quien invite
        if inviter_role == 'super_admin':
            # super_admin invita a admin - no tiene negocio aún
            # El admin creará su negocio al registrarse
            invitation_data['businessId'] = None
            invitation_data['branchId'] = None
        else:
            # admin o inferior invita - ya tienen negocio y sucursal
            invitation_data['businessId'] = inviter_data.get('businessId')
            invitation_data['branchId'] = inviter_data.get('branchId')

        return invitation_data

    @staticmethod
    def validate_token(invitation: Dict[str, Any]) -> tuple[bool, str]:
        """
        Valida si un token de invitación es válido

        Args:
            invitation: Documento de invitación de Firestore

        Returns:
            Tuple (is_valid, error_message)
        """
        if not invitation:
            return False, 'Invitación no encontrada'

        if invitation.get('status') != 'pending':
            return False, 'La invitación ya fue usada o expiró'

        expires_at_str = invitation.get('expiresAt')
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if datetime.now() > expires_at:
                return False, 'La invitación ha expirado'

        return True, ''

    @staticmethod
    def mark_as_used(invitation: Dict[str, Any]) -> Dict[str, Any]:
        """Marca la invitación como usada"""
        return {
            **invitation,
            'status': 'accepted',
            'usedAt': datetime.now().isoformat()
        }