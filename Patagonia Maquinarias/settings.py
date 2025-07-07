# Configuración de correo electrónico
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'patagoniamaquinarias@gmail.com'  # Reemplaza con tu correo de Gmail
EMAIL_HOST_PASSWORD = 'tu_contraseña_de_aplicacion'  # Reemplaza con tu contraseña de aplicación de Gmail
DEFAULT_FROM_EMAIL = 'Patagonia Maquinarias <patagoniamaquinarias@gmail.com>' 