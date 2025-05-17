from django.contrib import admin
from django.urls import path, include
from helpers import swagger_documentation

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('reward/', include('business.urls')),
    path('admin/', include('admin_dashboard.urls')),
    path('member/reward/', include('member.urls')),
    path('swagger/', swagger_documentation.schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', swagger_documentation.schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

]
