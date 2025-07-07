from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static


from . import views

app_name = 'gestionDeTaller'

urlpatterns = [
        path('', views.gestion_de_taller, name='gestion_de_taller'),
        path('servicios/', views.lista_servicios, name='lista_servicios'),
        path('calendario_preordenes/', views.calendario_preordenes, name='calendario_preordenes'),
        path('preordenes_json/', views.preordenes_json, name='preordenes_json'),
        path('preorden/<int:preorden_id>/detalle/', views.detalle_preorden, name='detalle_preorden'),
        path('crear_preorden/', views.crear_preorden, name='crear_preorden'),
        path('equipos-por-cliente/<int:cliente_id>/', views.equipos_por_cliente, name='equipos_por_cliente'),
        path('servicio/<int:servicio_id>/', views.detalle_servicio, name='detalle_servicio'), 
        path('servicio/<int:servicio_id>/editar/', views.editar_servicio, name='editar_servicio'),
        path('servicio/<int:servicio_id>/cambiar_estado/', views.cambiar_estado_servicio, name='cambiar_estado_servicio'),
        path('servicio/<int:servicio_id>/historial_cambios/', views.historial_cambios_servicio, name='historial_cambios_servicio'),
        path('servicio/<int:servicio_id>/historial_cambios_informe/', views.historial_cambios_informe, name='historial_cambios_informe'),
        path('get-preorden-horometro/', views.get_preorden_horometro, name='get_preorden_horometro'),
        path('servicio/<int:servicio_id>/editar_documentos/', views.editar_servicio_documentos, name='editar_servicio_documentos'),
        path('servicio/<int:servicio_id>/editar_valor_mano_obra/', views.editar_valor_mano_obra, name='editar_valor_mano_obra'),
        path('servicio/<int:servicio_id>/agregar_pedido/', views.agregar_pedido, name='agregar_pedido'),
        path('actualizar-estado-pedido/', views.actualizar_estado_pedido, name='actualizar_estado_pedido'),
        path('servicio/<int:servicio_id>/agregar_gasto/', views.agregar_gasto_asistencia, name='agregar_gasto'),
        path('servicio/<int:servicio_id>/agregar_repuesto/', views.agregar_venta_repuesto, name='agregar_repuesto'),
        path('servicio/<int:servicio_id>/enviar_documentacion/', views.enviar_documentacion, name='enviar_documentacion'),
        path('servicio/<int:servicio_id>/editar_informe/', views.editar_informe, name='editar_informe'),
        path('servicio/<int:servicio_id>/generar_informe_pdf/', views.generar_informe_pdf, name='generar_informe_pdf'),
        path('servicio/<int:servicio_id>/ver_informe/', views.ver_informe, name='ver_informe'),
        path('lista_preordenes/', views.lista_preordenes, name='lista_preordenes'),
        path('editar_preorden/<int:preorden_id>/', views.editar_preorden, name='editar_preorden'),
        path('servicio/<int:servicio_id>/checklist_salida_campo/', views.crear_checklist_campo, name='crear_checklist_campo'),

        path('tecnicos/', views.tecnicos, name='tecnicos'),
        path('tecnicos/<int:tecnico_id>/', views.detalle_tecnico, name='detalle_tecnico'),
        path('tecnicos/<int:tecnico_id>/registrar_horas/', views.registrar_horas, name="registrar_horas"),
        path('tecnicos/<int:tecnico_id>/revisar_horas/<str:fecha>/', views.revisar_horas, name="revisar_horas"),

        # URLs para el sistema 5S
        path('5s/', views.lista_revisiones_5s, name='lista_revisiones_5s'),
        path('5s/crear/', views.crear_revision_5s, name='crear_revision_5s'),
        path('5s/<int:revision_id>/', views.detalle_revision_5s, name='detalle_revision_5s'),
        path('5s/<int:revision_id>/plan-accion/', views.crear_plan_accion_5s, name='crear_plan_accion_5s'),
        path('5s/planes-accion/', views.lista_planes_accion_5s, name='lista_planes_accion_5s'),

        # URLs para encuestas
        path('encuestas/', views.lista_encuestas, name='lista_encuestas'),
        path('encuestas/enviar/<int:servicio_id>/', views.enviar_encuesta, name='enviar_encuesta'),
        path('encuestas/estadisticas/', views.estadisticas_encuestas, name='estadisticas_encuestas'),
        path('encuestas/<int:encuesta_id>/cargar_respuesta/', views.cargar_respuesta_encuesta, name='cargar_respuesta_encuesta'),
        path('encuestas/<int:encuesta_id>/ver_respuesta/', views.ver_respuesta_encuesta, name='ver_respuesta_encuesta'),
        path('encuestas/<int:encuesta_id>/registrar_insatisfaccion/', views.registrar_insatisfaccion, name='registrar_insatisfaccion'),
        path('insatisfaccion/<int:insatisfaccion_id>/', views.ver_insatisfaccion, name='ver_insatisfaccion'),
        path('insatisfaccion/<int:insatisfaccion_id>/editar/', views.editar_insatisfaccion, name='editar_insatisfaccion'),
        path('insatisfacciones/', views.lista_insatisfacciones, name='lista_insatisfacciones'),
        
        # URLs para observaciones de servicios
        path('servicio/<int:servicio_id>/agregar_observacion/', views.agregar_observacion, name='agregar_observacion'),
        path('observacion/<int:observacion_id>/eliminar/', views.eliminar_observacion, name='eliminar_observacion'),
    ]