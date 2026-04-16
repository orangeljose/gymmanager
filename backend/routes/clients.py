"""
Rutas de gestión de clientes para GymManager
"""
import logging
from flask import Blueprint, request, jsonify, g
from flask_cors import cross_origin
from middleware.auth_middleware import require_auth, require_role, validate_branch_access
from services.firebase_service import FirebaseService
from services.membership_service import MembershipService
from models.client import ClientCreateSchema, ClientUpdateSchema
from utils.validators import validate_pagination, validate_choice

logger = logging.getLogger(__name__)

clients_bp = Blueprint('clients', __name__, url_prefix='/api/clients')

@clients_bp.route('', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5173'], 
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
             methods=['GET', 'OPTIONS'])
@require_auth
def get_clients():
    """
    Lista clientes con filtros y paginación
    
    Query Parameters:
        branchId: string (optional) - Filtrar por sede
        status: string (optional) - active, expired, suspended
        search: string (optional) - Buscar por nombre o email
        page: integer (optional) - Número de página (default: 1)
        limit: integer (optional) - Items por página (default: 20, max: 100)
    
    Response (200):
    {
        "success": true,
        "data": [...],
        "meta": {
            "total": 45,
            "page": 1,
            "limit": 20,
            "pages": 3
        }
    }
    """
    try:
        # Obtener parámetros de query
        branch_id = request.args.get('branchId')
        status = request.args.get('status')
        search = request.args.get('search', '').strip()
        
        # Validar paginación
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        pagination = validate_pagination(page, limit)
        
        # Construir filtros
        filters = []
        
        # Filtro por negocio del usuario
        user_business_id = g.current_user.get('businessId')
        filters.append({'field': 'businessId', 'operator': '==', 'value': user_business_id})
        
        # Filtro por sede (si el usuario no es super admin)
        if g.current_user.get('role') != 'super_admin':
            user_branch_id = g.current_user.get('branchId')
            filters.append({'field': 'branchId', 'operator': '==', 'value': user_branch_id})
        elif branch_id:
            # Validar acceso a la sede
            if not validate_branch_access(branch_id):
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 403,
                        'message': 'No tienes acceso a esta sede'
                    }
                }), 403
            filters.append({'field': 'branchId', 'operator': '==', 'value': branch_id})
        
        # Filtro por status
        if status:
            valid_statuses = ['active', 'expired', 'suspended']
            if status not in valid_statuses:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 400,
                        'message': f'Status debe ser uno de: {", ".join(valid_statuses)}'
                    }
                }), 400
            filters.append({'field': 'status', 'operator': '==', 'value': status})
        
        # Búsqueda por nombre o email (búsqueda simple)
        if search:
            # Firestore no soporta LIKE, así que buscamos por nombre exacto
            # En producción, se recomienda usar Algolia o similar
            filters.append({'field': 'name', 'operator': '>=', 'value': search})
            filters.append({'field': 'name', 'operator': '<=', 'value': search + '\uf8ff'})
        
        # Ejecutar query
        firebase_service = FirebaseService()
        clients = firebase_service.query_firestore(
            'clients',
            filters=filters,
            order_by='name',
            limit=pagination['limit'],
            offset=pagination['offset']
        )
        
        # Obtener total para paginación (sin límite)
        total_clients = firebase_service.query_firestore('clients', filters=filters)
        total = len(total_clients)
        
        # Calcular páginas totales
        pages = (total + pagination['limit'] - 1) // pagination['limit']
        
        logger.info(f"Listados {len(clients)} clientes (página {pagination['page']})")
        
        return jsonify({
            'success': True,
            'data': clients,
            'meta': {
                'total': total,
                'page': pagination['page'],
                'limit': pagination['limit'],
                'pages': pages
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listando clientes: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500

@clients_bp.route('/<client_id>', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5173'], 
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
             methods=['GET', 'OPTIONS'])
@require_auth
def get_client(client_id):
    """
    Obtiene un cliente por su ID
    
    Response (200):
    {
        "success": true,
        "data": {
            "id": "client-001",
            "name": "Juan Pérez",
            "email": "juan@example.com",
            ...
        }
    }
    """
    try:
        firebase_service = FirebaseService()
        
        # Obtener cliente
        client = firebase_service.get_document('clients', client_id)
        if not client:
            return jsonify({
                'success': False,
                'error': {
                    'code': 404,
                    'message': 'Cliente no encontrado'
                }
            }), 404
        
        # Validar acceso al negocio del cliente
        client_business_id = client.get('businessId')
        user_business_id = g.current_user.get('businessId')
        
        if client_business_id != user_business_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 403,
                    'message': 'No tienes acceso a este cliente'
                }
            }), 403
        
        # Validar acceso a la sede del cliente (si no es super admin)
        client_branch_id = client.get('branchId')
        if g.current_user.get('role') != 'super_admin':
            user_branch_id = g.current_user.get('branchId')
            if client_branch_id != user_branch_id:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 403,
                        'message': 'No tienes acceso a este cliente'
                    }
                }), 403
        
        logger.info(f"Cliente obtenido: {client_id}")
        
        return jsonify({
            'success': True,
            'data': client
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo cliente {client_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500

@clients_bp.route('', methods=['POST', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5173'], 
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
             methods=['POST', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'branch_admin'])
def create_client():
    """
    Crea un nuevo cliente
    
    Request Body:
    {
        "name": "María García",
        "email": "maria@example.com",
        "phone": "+1234567892",
        "documentId": "87654321",
        "branchId": "sede-norte",
        "businessId": "gimnasio-central",
        "membershipPlanId": "plan-mensual",
        "notes": "Viene por referencia"
    }
    """
    try:
        # Obtener y validar datos
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'Se requieren datos en el cuerpo del request'
                }
            }), 400
        
        # Validar datos con el schema
        schema = ClientCreateSchema(data)
        client_data = schema.to_dict()
        
        # Validar acceso a la sede
        branch_id = client_data.get('branchId')
        if g.current_user.get('role') != 'super_admin':
            user_branch_id = g.current_user.get('branchId')
            if branch_id != user_branch_id:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 403,
                        'message': 'No puedes crear clientes en esta sede'
                    }
                }), 403
        
        # Validar que el plan de membresía exista
        membership_service = MembershipService()
        plan = membership_service.get_plan_by_id(client_data.get('membershipPlanId'))
        if not plan:
            return jsonify({
                'success': False,
                'error': {
                    'code': 404,
                    'message': 'Plan de membresía no encontrado'
                }
            }), 404
        
        # Agregar información adicional
        client_data['businessId'] = g.current_user.get('businessId')
        client_data['registeredBy'] = g.current_user.get('uid')
        
        # Calcular fechas de membresía
        duration_days = plan.get('durationDays', 30)
        membership_service = MembershipService()
        membership_dates = membership_service.calculate_new_end_date(
            None,  # Nueva membresía, empieza desde hoy
            duration_days
        )
        
        client_data['membershipStart'] = membership_dates
        client_data['membershipEnd'] = membership_dates
        
        # Crear cliente
        firebase_service = FirebaseService()
        created_client = firebase_service.create_document('clients', client_data)
        
        if created_client:
            logger.info(f"Cliente creado exitosamente: {created_client.get('id')}")
            return jsonify({
                'success': True,
                'data': created_client
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 500,
                    'message': 'Error al crear cliente'
                }
            }), 500
        
    except ValueError as e:
        logger.warning(f"Error de validación creando cliente: {str(e)}")
        errors = e.args[0].get('errors', ['Error de validación'])
        return jsonify({
            'success': False,
            'error': {
                'code': 400,
                'message': '; '.join(errors)
            }
        }), 400
    except Exception as e:
        logger.error(f"Error creando cliente: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500

@clients_bp.route('/<client_id>', methods=['PUT', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5173'], 
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
             methods=['PUT', 'OPTIONS'])
@require_auth
@require_role(['super_admin', 'branch_admin'])
def update_client(client_id):
    """
    Actualiza un cliente existente
    
    Request Body:
    {
        "name": "María García López",
        "phone": "+1234567893",
        "notes": "Cambió de horario",
        "status": "suspended"
    }
    """
    try:
        # Verificar que el cliente exista
        firebase_service = FirebaseService()
        client = firebase_service.get_document('clients', client_id)
        if not client:
            return jsonify({
                'success': False,
                'error': {
                    'code': 404,
                    'message': 'Cliente no encontrado'
                }
            }), 404
        
        # Validar acceso al negocio y sede
        client_business_id = client.get('businessId')
        client_branch_id = client.get('branchId')
        user_business_id = g.current_user.get('businessId')
        user_branch_id = g.current_user.get('branchId')
        
        if client_business_id != user_business_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 403,
                    'message': 'No tienes acceso a este cliente'
                }
            }), 403
        
        if g.current_user.get('role') != 'super_admin' and client_branch_id != user_branch_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 403,
                    'message': 'No tienes acceso a este cliente'
                }
            }), 403
        
        # Obtener y validar datos de actualización
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'Se requieren datos en el cuerpo del request'
                }
            }), 400
        
        # Validar con el schema
        schema = ClientUpdateSchema(data)
        update_data = schema.to_dict()
        
        # Actualizar cliente
        success = firebase_service.update_document('clients', client_id, update_data)
        
        if success:
            logger.info(f"Cliente actualizado: {client_id}")
            return jsonify({
                'success': True,
                'data': {
                    'id': client_id,
                    **update_data
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': {
                    'code': 500,
                    'message': 'Error al actualizar cliente'
                }
            }), 500
        
    except ValueError as e:
        logger.warning(f"Error de validación actualizando cliente {client_id}: {str(e)}")
        errors = e.args[0].get('errors', ['Error de validación'])
        return jsonify({
            'success': False,
            'error': {
                'code': 400,
                'message': '; '.join(errors)
            }
        }), 400
    except Exception as e:
        logger.error(f"Error actualizando cliente {client_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500

@clients_bp.route('/<client_id>/payments', methods=['GET', 'OPTIONS'])
@cross_origin(origins=['http://localhost:3000', 'http://localhost:5173'], 
             supports_credentials=True,
             allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
             methods=['GET', 'OPTIONS'])
@require_auth
def get_client_payments(client_id):
    """
    Obtiene el historial de pagos de un cliente
    
    Response (200):
    {
        "success": true,
        "data": [
            {
                "id": "payment-001",
                "amount": 35000,
                "method": "cash",
                "receiptNumber": "P-20260414-001",
                ...
            }
        ]
    }
    """
    try:
        # Verificar que el cliente exista
        firebase_service = FirebaseService()
        client = firebase_service.get_document('clients', client_id)
        if not client:
            return jsonify({
                'success': False,
                'error': {
                    'code': 404,
                    'message': 'Cliente no encontrado'
                }
            }), 404
        
        # Validar acceso al negocio y sede
        client_business_id = client.get('businessId')
        client_branch_id = client.get('branchId')
        user_business_id = g.current_user.get('businessId')
        user_branch_id = g.current_user.get('branchId')
        
        if client_business_id != user_business_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 403,
                    'message': 'No tienes acceso a este cliente'
                }
            }), 403
        
        if g.current_user.get('role') != 'super_admin' and client_branch_id != user_branch_id:
            return jsonify({
                'success': False,
                'error': {
                    'code': 403,
                    'message': 'No tienes acceso a este cliente'
                }
            }), 403
        
        # Obtener pagos del cliente
        from services.payment_service import PaymentService
        payment_service = PaymentService()
        payments = payment_service.get_client_payments(client_id)
        
        logger.info(f"Obtenidos {len(payments)} pagos para cliente {client_id}")
        
        return jsonify({
            'success': True,
            'data': payments
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo pagos del cliente {client_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': {
                'code': 500,
                'message': 'Error interno del servidor'
            }
        }), 500
