"""
Tests para el modelo de Plan
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.plan import PlanModel, PlanCreateSchema, PlanUpdateSchema


class TestPlanModelValidateCreateData:
    """Tests para PlanModel.validate_create_data"""

    def test_valid_minimal_data(self):
        """Datos mínimos válidos"""
        data = {
            'name': 'Mensual',
            'price': 35000,
            'durationDays': 30,
            'businessId': 'test-business'
        }
        result = PlanModel.validate_create_data(data.copy())
        assert result['name'] == 'Mensual'
        assert result['price'] == 35000
        assert result['durationDays'] == 30
        assert result['isActive'] is True
        assert result['benefits'] == []

    def test_valid_full_data(self):
        """Datos completos válidos"""
        data = {
            'name': ' Trimestral ',
            'price': 90000,
            'durationDays': 90,
            'businessId': 'test-business',
            'description': ' Plan de 3 meses ',
            'benefits': ['Beneficio 1', 'Beneficio 2']
        }
        result = PlanModel.validate_create_data(data)
        assert result['name'] == 'Trimestral'
        assert result['description'] == 'Plan de 3 meses'
        assert len(result['benefits']) == 2

    def test_missing_required_field_name(self):
        """Falta campo requerido 'name'"""
        data = {
            'price': 35000,
            'durationDays': 30,
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("name" in e for e in errors)

    def test_missing_required_field_price(self):
        """Falta campo requerido 'price'"""
        data = {
            'name': 'Mensual',
            'durationDays': 30,
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("price" in e for e in errors)

    def test_missing_required_field_durationDays(self):
        """Falta campo requerido 'durationDays'"""
        data = {
            'name': 'Mensual',
            'price': 35000,
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("durationDays" in e for e in errors)

    def test_invalid_price_not_integer(self):
        """price debe ser entero"""
        data = {
            'name': 'Mensual',
            'price': '35000',
            'durationDays': 30,
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("precio" in e.lower() for e in errors)

    def test_invalid_price_negative(self):
        """price no puede ser negativo"""
        data = {
            'name': 'Mensual',
            'price': -1000,
            'durationDays': 30,
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("precio" in e.lower() for e in errors)

    def test_invalid_price_zero(self):
        """price no puede ser cero"""
        data = {
            'name': 'Mensual',
            'price': 0,
            'durationDays': 30,
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("precio" in e.lower() for e in errors)

    def test_invalid_duration_not_integer(self):
        """durationDays debe ser entero"""
        data = {
            'name': 'Mensual',
            'price': 35000,
            'durationDays': '30',
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("duración" in e.lower() for e in errors)

    def test_invalid_duration_negative(self):
        """durationDays no puede ser negativo"""
        data = {
            'name': 'Mensual',
            'price': 35000,
            'durationDays': -1,
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("duración" in e.lower() for e in errors)

    def test_name_too_short(self):
        """name debe tener al menos 2 caracteres"""
        data = {
            'name': 'A',
            'price': 35000,
            'durationDays': 30,
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("nombre" in e.lower() for e in errors)

    def test_name_too_long(self):
        """name no puede exceder 100 caracteres"""
        data = {
            'name': 'A' * 101,
            'price': 35000,
            'durationDays': 30,
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("nombre" in e.lower() for e in errors)

    def test_description_too_long(self):
        """description no puede exceder 500 caracteres"""
        data = {
            'name': 'Mensual',
            'price': 35000,
            'durationDays': 30,
            'businessId': 'test-business',
            'description': 'A' * 501
        }
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("descripción" in e.lower() for e in errors)

    def test_benefits_not_list(self):
        """benefits debe ser lista"""
        data = {
            'name': 'Mensual',
            'price': 35000,
            'durationDays': 30,
            'businessId': 'test-business',
            'benefits': 'no es lista'
        }
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("benefits" in e.lower() for e in errors)

    def test_benefits_too_many(self):
        """No puede tener más de 20 beneficios"""
        data = {
            'name': 'Mensual',
            'price': 35000,
            'durationDays': 30,
            'businessId': 'test-business',
            'benefits': [f'Benefit {i}' for i in range(21)]
        }
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("beneficio" in e.lower() for e in errors)

    def test_price_exceeds_maximum(self):
        """price no puede exceder 1,000,000 cents ($10,000)"""
        data = {
            'name': 'Mensual',
            'price': 100000001,
            'durationDays': 30,
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("precio" in e.lower() for e in errors)

    def test_duration_exceeds_maximum(self):
        """durationDays no puede exceder 3650 días (10 años)"""
        data = {
            'name': 'Vitalicio',
            'price': 1000000,
            'durationDays': 3651,
            'businessId': 'test-business'
        }
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_create_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("duración" in e.lower() for e in errors)


class TestPlanModelValidateUpdateData:
    """Tests para PlanModel.validate_update_data"""

    def test_update_valid_name(self):
        """Actualización válida de name"""
        data = {'name': 'Nuevo Nombre'}
        result = PlanModel.validate_update_data(data)
        assert result['name'] == 'Nuevo Nombre'

    def test_update_valid_price(self):
        """Actualización válida de price"""
        data = {'price': 45000}
        result = PlanModel.validate_update_data(data)
        assert result['price'] == 45000

    def test_update_valid_isActive(self):
        """Actualización válida de isActive"""
        data = {'isActive': False}
        result = PlanModel.validate_update_data(data)
        assert result['isActive'] is False

    def test_update_invalid_field(self):
        """Campo no permitido causa error"""
        data = {'invalidField': 'value'}
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_update_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("no permitidos" in e.lower() for e in errors)

    def test_update_invalid_price_type(self):
        """price debe ser entero"""
        data = {'price': 'not integer'}
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_update_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("precio" in e.lower() for e in errors)

    def test_update_invalid_isActive_type(self):
        """isActive debe ser booleano"""
        data = {'isActive': 'yes'}
        with pytest.raises(ValueError) as exc_info:
            PlanModel.validate_update_data(data)
        errors = exc_info.value.args[0]['errors']
        assert any("booleano" in e.lower() for e in errors)


class TestPlanCreateSchema:
    """Tests para PlanCreateSchema"""

    def test_schema_valid_data(self, sample_plan_data):
        """Schema procesa datos válidos"""
        schema = PlanCreateSchema(sample_plan_data)
        result = schema.to_dict()
        assert result['name'] == 'Mensual'
        assert result['isActive'] is True

    def test_schema_invalid_data(self):
        """Schema lanza error en datos inválidos"""
        data = {'name': 'A', 'price': -1, 'durationDays': 0, 'businessId': 'x'}
        with pytest.raises(ValueError):
            PlanCreateSchema(data)


class TestPlanFromFirestore:
    """Tests para PlanModel.from_firestore"""

    def test_from_firestore_adds_id(self):
        """Convierte documento y agrega id"""
        doc = {
            'name': 'Mensual',
            'price': 35000,
            'durationDays': 30
        }
        result = PlanModel.from_firestore(doc, 'plan-123')
        assert result['id'] == 'plan-123'
        assert result['name'] == 'Mensual'

    def test_from_firestore_converts_timestamp(self):
        """Convierte timestamps a string"""
        from datetime import datetime
        doc = {
            'name': 'Mensual',
            'createdAt': datetime(2026, 5, 13, 10, 0, 0)
        }
        result = PlanModel.from_firestore(doc, 'plan-123')
        assert 'createdAt' in result
        assert isinstance(result['createdAt'], str)