"""
Rutas de gestión de invitaciones para GymManager
"""
import logging
from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_auth, require_role
from services.firebase_service import FirebaseService
from models.invitation import InvitationModel

logger = logging.getLogger(__name__)

invitations_bp = Blueprint('invitations', __name__, url_prefix='/api/invitations')


@invitations_bp.route('', methods=['POST', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'admin'])
def create_invitation():
    """
    Crea una nueva invitación para un empleado

    Request Body:
    {
        "email": "nuevo@empleado.com",
        "name": "Juan Pérez",  // opcional
        "role": "cashier"
    }

    Response (201):
    {
        "success": true,
        "data": {
            "invitationId": "inv-123",
            "token": "abc-123-xyz",
            "email": "nuevo@empleado.com",
            "role": "cashier",
            "expiresAt": "2026-05-18T...",
            "invitationLink": "https://app.com/invite?token=abc-123-xyz"
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'Se requieren datos en el cuerpo del request'
                }
            }), 400

        email = data.get('email', '').strip().lower()
        target_role = data.get('role', '').strip()
        invited_name = data.get('name', '').strip() or None

        # Validar campos requeridos
        if not email:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'El email es requerido'
                }
            }), 400

        if not target_role:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'El rol es requerido'
                }
            }), 400

        # Validar que el email sea válido
        import re
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'El email no es válido'
                }
            }), 400

        # Verificar que no exista ya una invitación pendiente para este email
        firebase_service = FirebaseService()
        existing = firebase_service.query_firestore(
            'invitations',
            filters=[
                {'field': 'email', 'operator': '==', 'value': email},
                {'field': 'status', 'operator': '==', 'value': 'pending'}
            ]
        )

        if existing:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'Ya existe una invitación pendiente para este email'
                }
            }), 400

        # Preparar datos del invitador
        inviter_data = {
            'uid': g.current_user.get('uid'),
            'role': g.current_user.get('role'),
            'businessId': g.current_user.get('businessId'),
            'branchId': g.current_user.get('branchId'),
            'name': g.current_user.get('name', 'Usuario')
        }

        # Crear datos de la invitación
        invitation_data = InvitationModel.create_invitation_data(
            email=email,
            inviter_data=inviter_data,
            target_role=target_role,
            invited_name=invited_name
        )

        # Guardar en Firestore
        created = firebase_service.create_document('invitations', invitation_data)

        if created:
            # Generar link de invitación
            invitation_id = created.get('id')
            token = invitation_data['token']

            logger.info(f"Invitación creada: {email} -> {target_role} por {g.current_user.get('uid')}")

            return jsonify({
                'success': True,
                'data': {
                    'invitationId': invitation_id,
                    'token': token,
                    'email': email,
                    'role': target_role,
                    'name': invited_name,
                    'expiresAt': invitation_data['expiresAt'],
                    'invitationLink': f"/invite?token={token}"
                }
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 500,
                    'message': 'Error al crear la invitación'
                }
            }), 500

    except ValueError as e:
        logger.warning(f"Error validando invitación: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 400,
                'message': str(e)
            }
        }), 400
    except Exception as e:
        logger.error(f"Error creando invitación: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500


@invitations_bp.route('/validate/<token>', methods=['GET', 'OPTIONS'])
def validate_invitation(token):
    """
    Valida un token de invitación y devuelve los datos del invitado

    Response (200):
    {
        "success": true,
        "data": {
            "valid": true,
            "email": "nuevo@empleado.com",
            "role": "cashier",
            "name": "Juan Pérez",
            "businessId": "biz-456",
            "branchId": "branch-789",
            "businessName": "Gimnasio Central",
            "invitedByName": "Carlos Dueño",
            "requiresOnboarding": false  // true solo si super_admin->admin
        }
    }
    """
    try:
        firebase_service = FirebaseService()

        # Buscar invitación por token
        invitations = firebase_service.query_firestore(
            'invitations',
            filters=[
                {'field': 'token', 'operator': '==', 'value': token},
                {'field': 'status', 'operator': '==', 'value': 'pending'}
            ]
        )

        if not invitations:
            return jsonify({
                'success': False,
                'error': {
                    'code': 404,
                    'message': 'Invitación no encontrada o ya usada'
                }
            }), 404

        invitation = invitations[0]

        # Validar token
        is_valid, error_msg = InvitationModel.validate_token(invitation)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': error_msg
                }
            }), 400

        # Obtener nombre del negocio si existe
        business_name = None
        if invitation.get('businessId'):
            business = firebase_service.get_document('businesses', invitation['businessId'])
            if business:
                business_name = business.get('name')

        # Determinar si requiere onboarding (super_admin->admin)
        requires_onboarding = invitation.get('role') == 'admin' and not invitation.get('businessId')

        logger.info(f"Token validado para: {invitation.get('email')}")

        return jsonify({
            'success': True,
            'data': {
                'valid': True,
                'email': invitation.get('email'),
                'role': invitation.get('role'),
                'name': invitation.get('name'),
                'businessId': invitation.get('businessId'),
                'branchId': invitation.get('branchId'),
                'businessName': business_name,
                'invitedByName': invitation.get('invitedByName'),
                'requiresOnboarding': requires_onboarding
            }
        }), 200

    except Exception as e:
        logger.error(f"Error validando token: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500


@invitations_bp.route('/accept', methods=['POST', 'OPTIONS'])
def accept_invitation():
    """
    Registra un usuario desde una invitación ( después de crear Firebase Auth )

    Request Body:
    {
        "token": "abc-123-xyz",
        "uid": "firebase-uid-123"  // UID de Firebase Auth
    }

    Response (201):
    {
        "success": true,
        "data": {
            "userId": "firebase-uid-123",
            "email": "nuevo@empleado.com",
            "role": "cashier",
            "businessId": "biz-456",
            "branchId": "branch-789"
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'Se requieren datos en el cuerpo del request'
                }
            }), 400

        token = data.get('token', '').strip()
        uid = data.get('uid', '').strip()

        if not token or not uid:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'Token y UID son requeridos'
                }
            }), 400

        firebase_service = FirebaseService()

        # Buscar invitación por token
        invitations = firebase_service.query_firestore(
            'invitations',
            filters=[
                {'field': 'token', 'operator': '==', 'value': token},
                {'field': 'status', 'operator': '==', 'value': 'pending'}
            ]
        )

        if not invitations:
            return jsonify({
                'success': False,
                'error': {
                    'code': 404,
                    'message': 'Invitación no encontrada o ya usada'
                }
            }), 404

        invitation = invitations[0]

        # Validar token
        is_valid, error_msg = InvitationModel.validate_token(invitation)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': error_msg
                }
            }), 400

        # Crear documento de usuario en Firestore usando el mismo UID de Firebase
        user_data = {
            'id': uid,
            'email': invitation.get('email'),
            'name': invitation.get('name') or '',
            'role': invitation.get('role'),
            'businessId': invitation.get('businessId'),
            'branchId': invitation.get('branchId'),
            'isActive': True,
            'permissions': [],  # Se calculan con el rol
            'createdAt': invitation.get('createdAt'),
            'invitedBy': invitation.get('invitedBy'),
            'invitedVia': 'invitation_token'
        }

        created_user = firebase_service.create_document('users', user_data)

        # Marcar invitación como aceptada
        invitation_id = invitation.get('id') or token
        firebase_service.update_document(
            'invitations',
            invitation_id,
            {
                'status': 'accepted',
                'usedAt': datetime.now().isoformat(),
                'userId': uid
            }
        )

        logger.info(f"Usuario creado desde invitación: {uid}")

        return jsonify({
            'success': True,
            'data': {
                'userId': uid,
                'email': invitation.get('email'),
                'role': invitation.get('role'),
                'name': invitation.get('name'),
                'businessId': invitation.get('businessId'),
                'branchId': invitation.get('branchId')
            }
        }), 201

    except Exception as e:
        logger.error(f"Error aceptando invitación: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500


from datetime import datetime