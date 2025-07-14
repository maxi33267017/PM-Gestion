import requests
import json
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from .models import (
    OperationsCenterConfig, Machine, MachineLocation, MachineEngineHours,
    MachineAlert, MachineHoursOfOperation, DeviceStateReport
)


class JohnDeereAPIService:
    """Servicio para interactuar con la API de John Deere Operations Center"""
    
    BASE_URL = "https://sandboxapi.deere.com/platform"  # URL de sandbox
    
    def __init__(self):
        self.config = OperationsCenterConfig.objects.filter(is_active=True).first()
        if not self.config:
            raise ValueError("No hay configuración activa para Operations Center")
    
    def _get_access_token(self):
        """Obtener o renovar el token de acceso"""
        if not self.config.access_token:
            raise ValueError("No hay token de acceso configurado")
        
        # Verificar si el token ha expirado
        if self.config.token_expires_at and self.config.token_expires_at <= timezone.now():
            if self.config.refresh_token:
                self._refresh_token()
            else:
                raise ValueError("Token expirado y no hay refresh token")
        
        return self.config.access_token
    
    def _refresh_token(self):
        """Renovar el token usando el refresh token"""
        url = "https://signin.johndeere.com/oauth2/aus78tnlaysMraFhC1t7/v1/token"
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.config.refresh_token,
            'client_id': self.config.client_id,
            'client_secret': self.config.client_secret,
            'redirect_uri': self.config.redirect_uri,
            'scope': 'eq1 ag1 org1 offline_access'
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        response = requests.post(url, data=data, headers=headers)
        if response.status_code == 200:
            token_data = response.json()
            self.config.access_token = token_data['access_token']
            self.config.refresh_token = token_data.get('refresh_token', self.config.refresh_token)
            self.config.token_expires_at = timezone.now() + timedelta(seconds=token_data.get('expires_in', 43200))
            self.config.save()
        else:
            raise Exception(f"Error al renovar token: {response.text}")
    
    def _make_request(self, endpoint, params=None):
        """Realizar una petición a la API"""
        headers = {
            'Authorization': f'Bearer {self._get_access_token()}',
            'Accept': 'application/vnd.deere.axiom.v3+json',
            'Content-Type': 'application/vnd.deere.axiom.v3+json'
        }
        
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            # Token expirado, intentar renovar
            self._refresh_token()
            headers['Authorization'] = f'Bearer {self._get_access_token()}'
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                return response.json()
        
        raise Exception(f"Error en API: {response.status_code} - {response.text}")
    
    def get_organizations(self):
        """Obtener organizaciones disponibles"""
        all_organizations = []
        start = 0
        count = 100  # Aumentar el límite por página
        
        while True:
            params = {
                'start': start,
                'count': count
            }
            
            print(f"Obteniendo organizaciones desde {start} con count {count}")  # Debug
            
            response = self._make_request('/organizations', params=params)
            organizations = response.get('values', [])
            
            print(f"Organizaciones obtenidas en esta página: {len(organizations)}")  # Debug
            
            if not organizations:
                break
                
            all_organizations.extend(organizations)
            
            # Si obtenemos menos del count máximo, hemos llegado al final
            if len(organizations) < count:
                break
                
            start += count
        
        print(f"Total de organizaciones obtenidas: {len(all_organizations)}")  # Debug
        return {'values': all_organizations}
    
    def get_machines(self, organization_id=None):
        """Obtener máquinas de la organización"""
        org_id = organization_id or self.config.organization_id
        if not org_id:
            raise ValueError("Organization ID no configurado")
        
        return self._make_request(f'/organizations/{org_id}/machines')
    
    def get_machine_details(self, machine_id):
        """Obtener detalles de una máquina específica"""
        return self._make_request(f'/machines/{machine_id}')
    
    def get_machine_location_history(self, machine_id, start_date=None, end_date=None):
        """Obtener historial de ubicaciones de una máquina"""
        params = {}
        if start_date:
            params['startDate'] = start_date.isoformat()
        if end_date:
            params['endDate'] = end_date.isoformat()
        
        return self._make_request(f'/machines/{machine_id}/locationHistory', params=params)
    
    def get_machine_engine_hours(self, machine_id, start_date=None, end_date=None):
        """Obtener horas de motor de una máquina"""
        params = {}
        if start_date:
            params['startDate'] = start_date.isoformat()
        if end_date:
            params['endDate'] = end_date.isoformat()
        
        return self._make_request(f'/machines/{machine_id}/engineHours', params=params)
    
    def get_machine_alerts(self, machine_id, start_date=None, end_date=None):
        """Obtener alertas de una máquina"""
        params = {}
        if start_date:
            params['startDate'] = start_date.isoformat()
        if end_date:
            params['endDate'] = end_date.isoformat()
        
        return self._make_request(f'/machines/{machine_id}/alerts', params=params)
    
    def get_machine_hours_of_operation(self, machine_id, start_date=None, end_date=None):
        """Obtener horas de operación de una máquina"""
        params = {}
        if start_date:
            params['startDate'] = start_date.isoformat()
        if end_date:
            params['endDate'] = end_date.isoformat()
        
        return self._make_request(f'/machines/{machine_id}/hoursOfOperation', params=params)
    
    def get_device_state_reports(self, machine_id, start_date=None, end_date=None):
        """Obtener reportes de estado del dispositivo"""
        params = {}
        if start_date:
            params['startDate'] = start_date.isoformat()
        if end_date:
            params['endDate'] = end_date.isoformat()
        
        return self._make_request(f'/machines/{machine_id}/deviceStateReports', params=params)


class OperationsCenterSyncService:
    """Servicio para sincronizar datos con Operations Center"""
    
    def __init__(self):
        self.api_service = JohnDeereAPIService()
    
    def sync_machines(self):
        """Sincronizar máquinas desde Operations Center"""
        try:
            machines_data = self.api_service.get_machines()
            
            for machine_data in machines_data.get('values', []):
                machine_id = machine_data.get('id')
                if not machine_id:
                    continue
                
                # Buscar o crear la máquina
                machine, created = Machine.objects.get_or_create(
                    machine_id=machine_id,
                    defaults={
                        'equipment_id': machine_data.get('equipmentId'),
                        'serial_number': machine_data.get('serialNumber'),
                        'model_name': machine_data.get('modelName'),
                        'make_name': machine_data.get('makeName'),
                        'year': machine_data.get('year'),
                        'description': machine_data.get('description'),
                    }
                )
                
                if not created:
                    # Actualizar datos existentes
                    machine.equipment_id = machine_data.get('equipmentId')
                    machine.serial_number = machine_data.get('serialNumber')
                    machine.model_name = machine_data.get('modelName')
                    machine.make_name = machine_data.get('makeName')
                    machine.year = machine_data.get('year')
                    machine.description = machine_data.get('description')
                
                machine.last_sync = timezone.now()
                machine.save()
            
            return True, f"Sincronizadas {len(machines_data.get('values', []))} máquinas"
        
        except Exception as e:
            return False, f"Error al sincronizar máquinas: {str(e)}"
    
    def sync_machine_location(self, machine_id, days_back=7):
        """Sincronizar ubicaciones de una máquina"""
        try:
            machine = Machine.objects.get(machine_id=machine_id)
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days_back)
            
            location_data = self.api_service.get_machine_location_history(
                machine_id, start_date, end_date
            )
            
            for location in location_data.get('values', []):
                timestamp = datetime.fromisoformat(location.get('timestamp').replace('Z', '+00:00'))
                
                # Verificar si ya existe esta ubicación
                if not MachineLocation.objects.filter(
                    machine=machine,
                    timestamp=timestamp
                ).exists():
                    MachineLocation.objects.create(
                        machine=machine,
                        latitude=location.get('latitude'),
                        longitude=location.get('longitude'),
                        timestamp=timestamp,
                        altitude=location.get('altitude'),
                        speed=location.get('speed'),
                        heading=location.get('heading'),
                    )
            
            # Actualizar última ubicación
            if location_data.get('values'):
                latest_location = location_data['values'][0]
                machine.last_location_lat = latest_location.get('latitude')
                machine.last_location_lng = latest_location.get('longitude')
                machine.last_location_timestamp = datetime.fromisoformat(
                    latest_location.get('timestamp').replace('Z', '+00:00')
                )
                machine.save()
            
            return True, f"Sincronizadas ubicaciones para máquina {machine_id}"
        
        except Exception as e:
            return False, f"Error al sincronizar ubicaciones: {str(e)}"
    
    def sync_machine_engine_hours(self, machine_id, days_back=7):
        """Sincronizar horas de motor de una máquina"""
        try:
            machine = Machine.objects.get(machine_id=machine_id)
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days_back)
            
            hours_data = self.api_service.get_machine_engine_hours(
                machine_id, start_date, end_date
            )
            
            for hours in hours_data.get('values', []):
                timestamp = datetime.fromisoformat(hours.get('timestamp').replace('Z', '+00:00'))
                
                # Verificar si ya existe este registro
                if not MachineEngineHours.objects.filter(
                    machine=machine,
                    timestamp=timestamp
                ).exists():
                    MachineEngineHours.objects.create(
                        machine=machine,
                        timestamp=timestamp,
                        engine_hours=hours.get('engineHours'),
                    )
            
            return True, f"Sincronizadas horas de motor para máquina {machine_id}"
        
        except Exception as e:
            return False, f"Error al sincronizar horas de motor: {str(e)}"
    
    def sync_machine_alerts(self, machine_id, days_back=30):
        """Sincronizar alertas de una máquina"""
        try:
            machine = Machine.objects.get(machine_id=machine_id)
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days_back)
            
            alerts_data = self.api_service.get_machine_alerts(
                machine_id, start_date, end_date
            )
            
            for alert in alerts_data.get('values', []):
                alert_id = alert.get('id')
                if not alert_id:
                    continue
                
                timestamp = datetime.fromisoformat(alert.get('timestamp').replace('Z', '+00:00'))
                
                # Buscar o crear la alerta
                machine_alert, created = MachineAlert.objects.get_or_create(
                    alert_id=alert_id,
                    defaults={
                        'machine': machine,
                        'severity': alert.get('severity', 'MEDIUM'),
                        'status': alert.get('status', 'ACTIVE'),
                        'category': alert.get('category'),
                        'description': alert.get('description'),
                        'timestamp': timestamp,
                    }
                )
                
                if not created:
                    # Actualizar alerta existente
                    machine_alert.severity = alert.get('severity', machine_alert.severity)
                    machine_alert.status = alert.get('status', machine_alert.status)
                    machine_alert.description = alert.get('description', machine_alert.description)
                    machine_alert.save()
            
            return True, f"Sincronizadas alertas para máquina {machine_id}"
        
        except Exception as e:
            return False, f"Error al sincronizar alertas: {str(e)}"
    
    def sync_all_machine_data(self, days_back=7):
        """Sincronizar todos los datos de todas las máquinas"""
        results = []
        
        # Primero sincronizar la lista de máquinas
        success, message = self.sync_machines()
        results.append(('Máquinas', success, message))
        
        if success:
            # Luego sincronizar datos de cada máquina
            machines = Machine.objects.filter(is_active=True)
            for machine in machines:
                # Ubicaciones
                success, message = self.sync_machine_location(machine.machine_id, days_back)
                results.append((f'Ubicaciones {machine}', success, message))
                
                # Horas de motor
                success, message = self.sync_machine_engine_hours(machine.machine_id, days_back)
                results.append((f'Horas motor {machine}', success, message))
                
                # Alertas (más días hacia atrás)
                success, message = self.sync_machine_alerts(machine.machine_id, 30)
                results.append((f'Alertas {machine}', success, message))
        
        return results 