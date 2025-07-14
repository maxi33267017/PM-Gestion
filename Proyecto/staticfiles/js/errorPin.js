document.addEventListener('DOMContentLoaded', function () {
    const equipoForm = document.getElementById('equipo-form');
    const mensajeError = document.getElementById('mensaje-error');
    const cerrarMensajeError = document.getElementById('cerrar-mensaje-error');

    equipoForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        // Obtener el valor del PIN ingresado por el usuario
        const pinInput = document.getElementById('id_pin');
        const pinValue = pinInput.value;

        // Verificar si el PIN ya existe en la base de datos (puedes usar una petición AJAX)
        const response = await fetch(`/verificar_pin/${pinValue}/`);
        const data = await response.json();

        if (data.existe_pin) {
            // Mostrar el mensaje de error y evitar que el formulario se envíe
            mensajeError.style.display = 'block';
        } else {
            // Enviar el formulario si el PIN no existe
            equipoForm.submit();
        }
    });

    cerrarMensajeError.addEventListener('click', function () {
        // Ocultar el mensaje de error al hacer clic en el botón "Cerrar"
        mensajeError.style.display = 'none';
    });
});