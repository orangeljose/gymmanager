"""
Servicio de conexión y operaciones con Firebase
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore, auth
from google.cloud.firestore_v1.base_query import FieldFilter

logger = logging.getLogger(__name__)

class FirebaseService:
    """Servicio principal para interactuar con Firebase"""
    
    _instance = None
    _db = None
    _auth = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Inicializa Firebase Admin SDK"""
        if FirebaseService._db is not None:
            return  # Ya está inicializado
        
        try:
            # Cargar credenciales desde variable de entorno
            cred_json = os.environ.get('FIREBASE_CREDENTIALS_JSON')
            if not cred_json:
                raise ValueError("FIREBASE_CREDENTIALS_JSON no está configurado")
            
            # Convertir JSON string a diccionario
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            logger.info("Credenciales cargadas desde variable de entorno FIREBASE_CREDENTIALS_JSON")
            
            # Inicializar Firebase Admin
            firebase_admin.initialize_app(cred)
            
            # Inicializar servicios
            FirebaseService._db = firestore.client()
            FirebaseService._auth = auth
            
            logger.info("Firebase Admin SDK inicializado correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando Firebase: {str(e)}")
            raise
    
    @property
    def db(self) -> firestore.Client:
        """Obtiene cliente de Firestore"""
        if FirebaseService._db is None:
            self.__init__()
        return FirebaseService._db
    
    @property
    def auth_client(self) -> auth.Client:
        """Obtiene cliente de Auth"""
        if FirebaseService._auth is None:
            self.__init__()
        return FirebaseService._auth
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verifica un token de Firebase Auth
        
        Args:
            token: Token JWT de Firebase
            
        Returns:
            Dict con información del usuario decodificada
            
        Raises:
            ValueError: Si el token es inválido o expiró
        """
        try:
            decoded_token = self.auth_client.verify_id_token(token)
            logger.info(f"Token verificado para UID: {decoded_token.get('uid')}")
            return decoded_token
            
        except auth.ExpiredIdTokenError:
            logger.warning("Token expirado")
            raise ValueError("Token expirado")
        except auth.InvalidIdTokenError as e:
            logger.warning(f"Token inválido: {str(e)}")
            raise ValueError("Token inválido")
        except Exception as e:
            logger.error(f"Error verificando token: {str(e)}")
            raise ValueError(f"Error de autenticación: {str(e)}")
    
    def get_user_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de usuario desde Firestore por UID
        
        Args:
            uid: UID del usuario
            
        Returns:
            Dict con datos del usuario o None si no existe
        """
        try:
            doc_ref = self.db.collection('users').document(uid)
            doc = doc_ref.get()
            
            if doc.exists:
                user_data = doc.to_dict()
                user_data['id'] = doc.id
                logger.info(f"Usuario encontrado: {uid}")
                return user_data
            else:
                logger.warning(f"Usuario no encontrado: {uid}")
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo usuario {uid}: {str(e)}")
            return None
    
    def query_firestore(
        self, 
        collection: str, 
        filters: List[Dict[str, Any]] = None,
        order_by: str = None,
        direction: str = 'ASC',
        limit: int = None,
        offset: int = None
    ) -> List[Dict[str, Any]]:
        """
        Query genérico a Firestore con logging
        
        Args:
            collection: Nombre de la colección
            filters: Lista de filtros [{'field': 'value', 'operator': '==', 'value': 'xxx'}]
            order_by: Campo para ordenar
            direction: Dirección del orden ('ASC' o 'DESC')
            limit: Límite de resultados
            offset: Offset para paginación
            
        Returns:
            Lista de documentos
        """
        try:
            query = self.db.collection(collection)
            
            # Aplicar filtros
            if filters:
                for filter_item in filters:
                    field = filter_item.get('field')
                    operator = filter_item.get('operator', '==')
                    value = filter_item.get('value')
                    
                    if operator == 'array-contains':
                        query = query.where(field, 'array-contains', value)
                    else:
                        query = query.where(field, operator, value)
            
            # Ordenamiento
            if order_by:
                from firebase_admin.firestore import DESCENDING, ASCENDING
                direction = DESCENDING if direction.upper() == 'DESC' else ASCENDING
                query = query.order_by(order_by, direction=direction)
            
            # Paginación
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            # Ejecutar query
            docs = query.stream()
            
            results = []
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['id'] = doc.id
                results.append(doc_data)
            
            logger.info(f"Query a {collection}: {len(results)} documentos")
            return results
            
        except Exception as e:
            logger.error(f"Error en query a {collection}: {str(e)}")
            return []
    
    def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un documento específico
        
        Args:
            collection: Nombre de la colección
            doc_id: ID del documento
            
        Returns:
            Dict con datos del documento o None si no existe
        """
        try:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc = doc_ref.get()
            
            if doc.exists:
                doc_data = doc.to_dict()
                doc_data['id'] = doc.id
                logger.info(f"Documento encontrado: {collection}/{doc_id}")
                return doc_data
            else:
                logger.warning(f"Documento no encontrado: {collection}/{doc_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo documento {collection}/{doc_id}: {str(e)}")
            return None
    
    def create_document(self, collection: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crea un nuevo documento
        
        Args:
            collection: Nombre de la colección
            data: Datos del documento
            
        Returns:
            Dict con datos del documento creado (incluyendo ID)
        """
        try:
            # Agregar timestamp de creación
            data['createdAt'] = firestore.SERVER_TIMESTAMP
            
            doc_ref = self.db.collection(collection).add(data)
            doc_data = data.copy()
            doc_data['id'] = doc_ref[1].id
            
            logger.info(f"Documento creado: {collection}/{doc_ref[1].id}")
            return doc_data
            
        except Exception as e:
            logger.error(f"Error creando documento en {collection}: {str(e)}")
            raise
    
    def update_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> bool:
        """
        Actualiza un documento
        
        Args:
            collection: Nombre de la colección
            doc_id: ID del documento
            data: Datos a actualizar
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.update(data)
            
            logger.info(f"Documento actualizado: {collection}/{doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error actualizando documento {collection}/{doc_id}: {str(e)}")
            return False
    
    def delete_document(self, collection: str, doc_id: str) -> bool:
        """
        Elimina un documento
        
        Args:
            collection: Nombre de la colección
            doc_id: ID del documento
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.delete()
            
            logger.info(f"Documento eliminado: {collection}/{doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error eliminando documento {collection}/{doc_id}: {str(e)}")
            return False
    
    def transaction(self, callback):
        """
        Ejecuta una transacción en Firestore
        
        Args:
            callback: Función que recibe la transacción
            
        Returns:
            Resultado de la transacción
        """
        try:
            result = self.db.transaction(callback)
            logger.info("Transacción ejecutada correctamente")
            return result
            
        except Exception as e:
            logger.error(f"Error en transacción: {str(e)}")
            raise
