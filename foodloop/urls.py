from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API application
    path('api/', include('api.urls')),
    
    # Core application
    path('', include('core.urls')),    
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

# Configure admin site
admin.site.site_header = "FoodLoop Administration"
admin.site.site_title = "FoodLoop Admin"
admin.site.index_title = "Welcome to FoodLoop Administration"