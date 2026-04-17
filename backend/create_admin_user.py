#!/usr/bin/env python3
"""
Script para crear usuario admin en Firestore
"""
import os
import json
from services.firebase_service import FirebaseService

def create_admin_user():
    """Crea el documento del usuario admin en Firestore"""
    
    # Datos del usuario admin
    admin_data = {
        "email": "admin@test.com",
        "name": "Administrador Principal", 
        "role": "super_admin",
        "businessId": "gymmanager-v1",  # Cambia esto por tu business ID real
        "branchId": None,  # Super admin puede acceder a todas las sedes
        "permissions": ["*"],  # Todos los permisos
        "isActive": True,
        "createdAt": None  # Se agregará automáticamente
    }
    
    try:
        firebase_service = FirebaseService()
        
        # El UID del usuario lo obtienes desde Firebase Console
        # Ve a Authentication → Users → admin@test.com → copia el User UID
        user_uid = input("Ingresa el User UID del usuario admin@test.com: ").strip()
        
        if not user_uid:
            print("❌ Debes proporcionar el User UID del usuario")
            return
        
        # Crear documento en la colección users
        doc_ref = firebase_service.db.collection('users').document(user_uid)
        doc_ref.set(admin_data)
        
        print(f"✅ Usuario admin creado exitosamente!")
        print(f"📧 Email: {admin_data['email']}")
        print(f"👤 Nombre: {admin_data['name']}")
        print(f"🔑 Rol: {admin_data['role']}")
        print(f"🏢 Business ID: {admin_data['businessId']}")
        print(f"📄 Document ID: {user_uid}")
        
    except Exception as e:
        print(f"❌ Error creando usuario: {str(e)}")

if __name__ == "__main__":
    print("=== Crear Usuario Admin en Firestore ===")
    print("1. Ve a Firebase Console → Authentication → Users")
    print("2. Busca admin@test.com y copia su User UID")
    print("3. Pega el User UID aquí:\n")
    
    create_admin_user()
