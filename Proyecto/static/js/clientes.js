$(document).ready(function () {
    // Inicializa DataTable con Bootstrap 5 y guarda la referencia en 'tabla'
    var tabla = $('#tablaClientes').DataTable({
        "language": {
            "url": "",
            "search": "Buscar:",
            "lengthMenu": "Mostrar _MENU_ clientes",
            "info": "Mostrando _START_ a _END_ de _TOTAL_ clientes",
            "infoEmpty": "Mostrando 0 a 0 de 0 clientes",
            "infoFiltered": "(filtrado de _MAX_ clientes en total)",
            "paginate": {
                "first": "Primero",
                "previous": "Anterior",
                "next": "Siguiente",
                "last": "Último"
            }
        },
        "scrollX": false,
    });

    // Manejar clics en filas con la clase 'fila-servicio' usando delegación de eventos
    $('#tablaClientes tbody').on('click', 'tr.fila-servicio', function () {
        var url = $(this).data('url');
        if (url) {
            window.location.href = url;
        }
    });
});
