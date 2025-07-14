"""
Middleware personalizado para servir archivos media en producción
"""

import os
import mimetypes
from django.conf import settings
from django.http import HttpResponse, Http404
from django.utils.deprecation import MiddlewareMixin

class MediaFilesMiddleware(MiddlewareMixin):
    """
    Middleware para servir archivos media en producción
    """
    
    def process_request(self, request):
        # Verificar si la URL comienza con MEDIA_URL
        if request.path.startswith(settings.MEDIA_URL):
            # Obtener la ruta del archivo relativa a MEDIA_URL
            relative_path = request.path[len(settings.MEDIA_URL):]
            
            # Construir la ruta completa del archivo
            file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
            
            # Verificar que el archivo existe y está dentro del directorio media
            if os.path.exists(file_path) and os.path.isfile(file_path):
                # Verificar que el archivo está dentro del directorio media (seguridad)
                real_path = os.path.realpath(file_path)
                media_root_real = os.path.realpath(settings.MEDIA_ROOT)
                
                if not real_path.startswith(media_root_real):
                    raise Http404("Archivo no encontrado")
                
                # Determinar el tipo MIME
                content_type, _ = mimetypes.guess_type(file_path)
                if content_type is None:
                    content_type = 'application/octet-stream'
                
                # Leer y servir el archivo
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    
                    response = HttpResponse(content, content_type=content_type)
                    response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
                    return response
                    
                except Exception as e:
                    raise Http404(f"Error leyendo archivo: {str(e)}")
            else:
                raise Http404("Archivo no encontrado")
        
        # Si no es un archivo media, continuar con el procesamiento normal
        return None 