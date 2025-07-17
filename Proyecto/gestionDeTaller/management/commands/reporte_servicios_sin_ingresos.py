from django.core.management.base import BaseCommand
from django.db.models import Sum, F
from decimal import Decimal
from gestionDeTaller.models import Servicio


class Command(BaseCommand):
    help = 'Genera un reporte de servicios completados que no generaron ingresos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--excel',
            action='store_true',
            help='Generar reporte en Excel',
        )

    def calcular_valor_total_servicio(self, servicio):
        """Calcula el valor total de un servicio"""
        # Mano de obra
        valor_mano_obra = servicio.valor_mano_obra or Decimal('0.00')
        
        # Gastos de asistencia
        total_gastos = servicio.gastos.aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0.00')
        
        # Ventas de repuestos
        total_repuestos = servicio.repuestos.aggregate(
            total=Sum(F('precio_unitario') * F('cantidad'))
        )['total'] or Decimal('0.00')
        
        return valor_mano_obra + total_gastos + total_repuestos

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("REPORTE DE SERVICIOS COMPLETADOS SIN INGRESOS")
        self.stdout.write("=" * 80)
        
        # Obtener servicios completados
        servicios_completados = Servicio.objects.filter(
            estado='COMPLETADO'
        ).select_related(
            'preorden__cliente',
            'preorden__equipo'
        ).prefetch_related(
            'gastos',
            'repuestos'
        ).order_by('fecha_servicio')
        
        self.stdout.write(f"Total de servicios completados: {servicios_completados.count()}")
        self.stdout.write("")
        
        # Filtrar servicios sin ingresos
        servicios_sin_ingresos = []
        
        for servicio in servicios_completados:
            valor_total = self.calcular_valor_total_servicio(servicio)
            
            if valor_total == Decimal('0.00'):
                servicios_sin_ingresos.append({
                    'servicio': servicio,
                    'valor_total': valor_total
                })
        
        self.stdout.write(f"Servicios sin ingresos: {len(servicios_sin_ingresos)}")
        if servicios_completados.count() > 0:
            porcentaje = (len(servicios_sin_ingresos) / servicios_completados.count() * 100)
            self.stdout.write(f"Porcentaje: {porcentaje:.1f}%")
        self.stdout.write("")
        
        if not servicios_sin_ingresos:
            self.stdout.write(self.style.SUCCESS("✅ No se encontraron servicios completados sin ingresos."))
            return
        
        # Mostrar detalles
        self.stdout.write("DETALLES DE SERVICIOS SIN INGRESOS:")
        self.stdout.write("-" * 80)
        
        for i, item in enumerate(servicios_sin_ingresos, 1):
            servicio = item['servicio']
            
            self.stdout.write(f"\n{i}. SERVICIO ID: {servicio.id}")
            self.stdout.write(f"   Fecha: {servicio.fecha_servicio.strftime('%d/%m/%Y')}")
            self.stdout.write(f"   Cliente: {servicio.preorden.cliente.razon_social}")
            self.stdout.write(f"   Equipo: {servicio.preorden.equipo.modelo} - {servicio.preorden.equipo.numero_serie}")
            self.stdout.write(f"   Tipo de trabajo: {servicio.get_trabajo_display()}")
            self.stdout.write(f"   Orden de servicio: {servicio.orden_servicio or 'N/A'}")
            
            if servicio.observaciones:
                self.stdout.write(f"   Observaciones: {servicio.observaciones}")
            
            # Detalles de valores
            valor_mano_obra = servicio.valor_mano_obra or Decimal('0.00')
            total_gastos = servicio.gastos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
            total_repuestos = servicio.repuestos.aggregate(
                total=Sum(F('precio_unitario') * F('cantidad'))
            )['total'] or Decimal('0.00')
            
            self.stdout.write(f"   Desglose:")
            self.stdout.write(f"     - Mano de obra: ${valor_mano_obra}")
            self.stdout.write(f"     - Gastos: ${total_gastos}")
            self.stdout.write(f"     - Repuestos: ${total_repuestos}")
            self.stdout.write(f"     - TOTAL: ${item['valor_total']}")
            
            # Mostrar gastos si existen
            gastos = servicio.gastos.all()
            if gastos.exists():
                self.stdout.write(f"   Gastos registrados:")
                for gasto in gastos:
                    self.stdout.write(f"     * {gasto.get_tipo_display()}: ${gasto.monto} - {gasto.descripcion}")
            
            # Mostrar repuestos si existen
            repuestos = servicio.repuestos.all()
            if repuestos.exists():
                self.stdout.write(f"   Repuestos registrados:")
                for repuesto in repuestos:
                    subtotal = repuesto.precio_unitario * repuesto.cantidad
                    self.stdout.write(f"     * {repuesto.codigo}: {repuesto.cantidad}x ${repuesto.precio_unitario} = ${subtotal}")
            
            self.stdout.write("-" * 80)
        
        # Resumen por cliente
        self.stdout.write("\nRESUMEN POR CLIENTE:")
        self.stdout.write("-" * 80)
        
        clientes_afectados = {}
        for item in servicios_sin_ingresos:
            cliente = item['servicio'].preorden.cliente
            if cliente not in clientes_afectados:
                clientes_afectados[cliente] = 0
            clientes_afectados[cliente] += 1
        
        for cliente, cantidad in sorted(clientes_afectados.items(), key=lambda x: x[1], reverse=True):
            self.stdout.write(f"{cliente.razon_social}: {cantidad} servicios")
        
        # Resumen por tipo de trabajo
        self.stdout.write("\nRESUMEN POR TIPO DE TRABAJO:")
        self.stdout.write("-" * 80)
        
        tipos_trabajo = {}
        for item in servicios_sin_ingresos:
            tipo = item['servicio'].get_trabajo_display()
            if tipo not in tipos_trabajo:
                tipos_trabajo[tipo] = 0
            tipos_trabajo[tipo] += 1
        
        for tipo, cantidad in sorted(tipos_trabajo.items(), key=lambda x: x[1], reverse=True):
            self.stdout.write(f"{tipo}: {cantidad} servicios")
        
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("FIN DEL REPORTE")
        self.stdout.write("=" * 80)
        
        # Generar Excel si se solicita
        if options['excel']:
            self.generar_excel(servicios_sin_ingresos)

    def generar_excel(self, servicios_sin_ingresos):
        """Genera reporte en Excel"""
        try:
            import pandas as pd
            from datetime import datetime
        except ImportError:
            self.stdout.write(self.style.ERROR("❌ Error: Se requiere pandas para generar Excel"))
            return
        
        self.stdout.write("\nGenerando reporte Excel...")
        
        datos = []
        for item in servicios_sin_ingresos:
            servicio = item['servicio']
            
            # Calcular valores
            valor_mano_obra = servicio.valor_mano_obra or Decimal('0.00')
            total_gastos = servicio.gastos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
            total_repuestos = servicio.repuestos.aggregate(
                total=Sum(F('precio_unitario') * F('cantidad'))
            )['total'] or Decimal('0.00')
            
            datos.append({
                'ID_Servicio': servicio.id,
                'Fecha_Servicio': servicio.fecha_servicio,
                'Cliente': servicio.preorden.cliente.razon_social,
                'Equipo_Modelo': servicio.preorden.equipo.modelo,
                'Equipo_Serie': servicio.preorden.equipo.numero_serie,
                'Tipo_Trabajo': servicio.get_trabajo_display(),
                'Orden_Servicio': servicio.orden_servicio or '',
                'Observaciones': servicio.observaciones or '',
                'Valor_Mano_Obra': float(valor_mano_obra),
                'Valor_Gastos': float(total_gastos),
                'Valor_Repuestos': float(total_repuestos),
                'Valor_Total': float(item['valor_total'])
            })
        
        if datos:
            df = pd.DataFrame(datos)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"servicios_sin_ingresos_{timestamp}.xlsx"
            
            df.to_excel(filename, index=False)
            self.stdout.write(self.style.SUCCESS(f"✅ Reporte Excel generado: {filename}"))
            self.stdout.write(f"   Total de registros: {len(datos)}")
        else:
            self.stdout.write("✅ No hay datos para exportar a Excel") 