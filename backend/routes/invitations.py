"""
Rutas de gestión de invitaciones para GymManager
"""
import logging
from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import require_auth, require_role
from services.firebase_service import FirebaseService
from services.email_service import sendInvitationEmail
from models.invitation import InvitationModel
from models.user import UserModel

logger = logging.getLogger(__name__)

invitations_bp = Blueprint('invitations', __name__, url_prefix='/api/invitations')


@invitations_bp.route('', methods=['POST', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'admin'])
def create_invitation():
    """
    Crea una nueva invitacion para un empleado
    """
    if request.method == 'OPTIONS':
        return '', 200

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
        business_id_from_request = data.get('businessId') or None
        branch_id_from_request = data.get('branchId') or None

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
            invited_name=invited_name,
            business_id_from_request=business_id_from_request,
            branch_id_from_request=branch_id_from_request
        )

        # Guardar en Firestore
        created = firebase_service.create_document('invitations', invitation_data)

        if created:
            # Generar link de invitación
            invitation_id = created.get('id')
            token = invitation_data['token']

            # Obtener nombre del negocio para el email
            business_name = None
            if invitation_data.get('businessId'):
                business = firebase_service.get_document('businesses', invitation_data['businessId'])
                if business:
                    business_name = business.get('name')

            # Enviar email de invitación
            frontend_url = request.environ.get('HTTP_ORIGIN', 'https://gymmanager-pink.vercel.app')
            invitation_link = f"{frontend_url}/invite?token={token}"

            email_result = sendInvitationEmail(to_email=email, invitation_data={
                'role': target_role,
                'invitedByName': inviter_data['name'],
                'businessName': business_name or 'GymManager',
                'invitationLink': invitation_link,
                'expiresAt': invitation_data.get('expiresAt')
            })

            if not email_result.get('success'):
                logger.warning(f"Email no enviado a {email}, pero invitación creada: {invitation_id}")

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
                    'invitationLink': invitation_link,
                    'emailSent': email_result.get('success', False)
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
    Valida un token de invitacion
    """
    if request.method == 'OPTIONS':
        return '', 200

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
    Registra un usuario desde una invitacion (despues de crear Firebase Auth)
    """
    if request.method == 'OPTIONS':
        return '', 200

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
        # Precedencia del nombre: nombre ingresado → nombre de la invitación → ''
        entered_name = (data.get('name') or '').strip() or None
        stored_name = entered_name or invitation.get('name') or ''

        user_data = {
            'id': uid,
            'email': invitation.get('email'),
            'name': stored_name,
            'role': invitation.get('role'),
            'businessId': invitation.get('businessId'),
            'branchId': invitation.get('branchId'),
            'isActive': True,
            'permissions': UserModel.get_permissions(invitation.get('role')),
            'createdAt': invitation.get('createdAt'),
            'invitedBy': invitation.get('invitedBy'),
            'invitedVia': 'invitation_token'
        }

        # Usar UID de Firebase Auth como ID del documento en Firestore
        user_data.pop('id', None)
        created_user = firebase_service.set_document('users', uid, user_data)

        if not created_user:
            return jsonify({
                'success': False,
                'error': {
                    'code': 500,
                    'message': 'Error al crear usuario en Firestore'
                }
            }), 500

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
                'name': stored_name,
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