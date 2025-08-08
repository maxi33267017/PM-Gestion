from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static


from . import views

app_name = 'gestionDeTaller'

urlpatterns = [
        path('', views.gestion_de_taller, name='gestion_de_taller'),
        path('dashboard-tecnico/', views.dashboard_tecnico, name='dashboard_tecnico'),
        path('dashboard-gerente/', views.dashboard_gerente, name='dashboard_gerente'),
        path('dashboard-administrador/', views.dashboard_administrador, name='dashboard_administrador'),
        path('servicios/', views.lista_servicios, name='lista_servicios'),
        path('calendario_preordenes/', views.calendario_preordenes, name='calendario_preordenes'),
        path('calendario_semanal_tecnicos/', views.calendario_semanal_tecnicos, name='calendario_semanal_tecnicos'),
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
        path('servicio/<int:servicio_id>/agregar_gasto_asistencia_simplificado/', views.agregar_gasto_asistencia_simplificado, name='agregar_gasto_asistencia_simplificado'),
        path('servicio/<int:servicio_id>/agregar_venta_repuestos_simplificada/', views.agregar_venta_repuestos_simplificada, name='agregar_venta_repuestos_simplificada'),
        path('servicio/<int:servicio_id>/agregar_gasto_insumos_terceros/', views.agregar_gasto_insumos_terceros, name='agregar_gasto_insumos_terceros'),
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
        path('5s/plan-accion/<int:plan_id>/', views.detalle_plan_accion_5s, name='detalle_plan_accion_5s'),
        path('5s/plan-accion/<int:plan_id>/editar/', views.editar_plan_accion_5s, name='editar_plan_accion_5s'),
        path('5s/item-plan-accion/<int:item_id>/editar/', views.editar_item_plan_accion_5s, name='editar_item_plan_accion_5s'),

        # URLs para encuestas
        path('encuestas/', views.lista_encuestas, name='lista_encuestas'),
        path('encuestas/enviar/<int:servicio_id>/', views.enviar_encuesta, name='enviar_encuesta'),
        path('encuestas/<int:encuesta_id>/reenviar/', views.reenviar_encuesta, name='reenviar_encuesta'),
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
        
        # URLs para gestión de repuestos
        path('repuestos/', views.gestionar_repuestos, name='gestionar_repuestos'),
        path('repuestos/crear/', views.crear_repuesto, name='crear_repuesto'),
        path('repuestos/obtener/', views.obtener_repuesto, name='obtener_repuesto'),
        path('repuestos/lista/', views.obtener_lista_repuestos, name='obtener_lista_repuestos'),
        path('repuestos/importar-jd/', views.importar_repuestos_jd, name='importar_repuestos_jd'),
        path('repuestos/seguimiento/<str:task_id>/', views.seguimiento_importacion, name='seguimiento_importacion'),
        path('repuestos/api/estado/<str:task_id>/', views.api_estado_importacion, name='api_estado_importacion'),

        # URLs para Herramientas Especiales
        path('herramientas-especiales/', views.herramientas_especiales_list, name='herramientas_especiales_list'),
        path('herramientas-especiales/<int:herramienta_id>/', views.herramienta_especial_detail, name='herramienta_especial_detail'),
        path('herramientas-especiales/<int:herramienta_id>/reservar/', views.reservar_herramienta, name='reservar_herramienta'),
        path('reservas/<int:reserva_id>/retirar/', views.retirar_herramienta, name='retirar_herramienta'),
        path('reservas/<int:reserva_id>/devolver/', views.devolver_herramienta, name='devolver_herramienta'),
        path('reservas/<int:reserva_id>/cancelar/', views.cancelar_reserva, name='cancelar_reserva'),
        path('herramientas-especiales/<int:herramienta_id>/retirar-sin-reserva/', views.retirar_sin_reserva, name='retirar_sin_reserva'),
        
        # URLs para importación de herramientas especiales
        path('herramientas-especiales/importar/', views.importar_herramientas_especiales, name='importar_herramientas_especiales'),
        path('herramientas-especiales/descargar-template/', views.descargar_template_excel, name='descargar_template_excel'),
        
        # URLs para Herramientas Personales
        path('herramientas-personales/', views.personal_tools_list, name='personal_tools_list'),
        path('herramientas-personales/dashboard/', views.personal_tools_dashboard, name='personal_tools_dashboard'),
        path('herramientas-personales/reportes/', views.personal_tools_reports, name='personal_tools_reports'),
        path('herramientas-personales/<int:tool_id>/', views.personal_tool_detail, name='personal_tool_detail'),
        path('herramientas-personales/<int:tool_id>/asignar/', views.assign_personal_tool, name='assign_personal_tool'),
        path('herramientas-personales/<int:tool_id>/devolver/', views.return_personal_tool, name='return_personal_tool'),
        path('herramientas-personales/<int:tool_id>/auditar/', views.audit_personal_tool, name='audit_personal_tool'),
        path('herramientas-personales/<int:tool_id>/certificacion/', views.update_certification, name='update_certification'),
        path('herramientas-personales/<int:tool_id>/items/', views.add_item, name='add_item'),
        
        # URLs para el sistema de tarifario
        path('tarifario/', views.ver_tarifario, name='ver_tarifario'),
        path('gestionar-tarifario/', views.gestionar_tarifario, name='gestionar_tarifario'),
        path('crear-tipo-equipo/', views.crear_tipo_equipo, name='crear_tipo_equipo'),
        path('crear-modelo-equipo/', views.crear_modelo_equipo, name='crear_modelo_equipo'),
        path('crear-tarifario/', views.crear_tarifario, name='crear_tarifario'),
        path('eliminar-tarifario/', views.eliminar_tarifario, name='eliminar_tarifario'),
        path('eliminar-modelo-equipo/', views.eliminar_modelo_equipo, name='eliminar_modelo_equipo'),
        path('eliminar-tipo-equipo/', views.eliminar_tipo_equipo, name='eliminar_tipo_equipo'),

        # URLs para Checklists de Inspección JD Protect
        path('checklists-inspeccion/', views.lista_checklists_inspeccion, name='lista_checklists_inspeccion'),
        path('servicio/<int:servicio_id>/crear-checklist/', views.crear_checklist_inspeccion, name='crear_checklist_inspeccion'),
        path('servicio/<int:servicio_id>/crear-equipo-rapido/', views.crear_equipo_rapido, name='crear_equipo_rapido'),
        path('obtener-modelos-equipo/', views.obtener_modelos_equipo, name='obtener_modelos_equipo'),
        path('checklist-inspeccion/<int:checklist_id>/', views.detalle_checklist_inspeccion, name='detalle_checklist_inspeccion'),
        path('elemento-checklist/<int:elemento_id>/actualizar/', views.actualizar_elemento_checklist, name='actualizar_elemento_checklist'),
        path('checklist-inspeccion/<int:checklist_id>/actualizar/', views.actualizar_checklist, name='actualizar_checklist'),
        path('checklist-inspeccion/<int:checklist_id>/descargar-pdf/', views.descargar_checklist_pdf, name='descargar_checklist_pdf'),
        path('checklist-inspeccion/<int:checklist_id>/enviar-email/', views.enviar_checklist_email, name='enviar_checklist_email'),
        path('checklist-inspeccion/<int:checklist_id>/guardar-todo/', views.guardar_todo_checklist, name='guardar_todo_checklist'),
    ]