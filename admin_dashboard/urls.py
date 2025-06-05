from django.contrib import admin
from django.urls import path
from admin_dashboard.staff import staff_api

urlpatterns = [
  path('business-members/<str:business_id>/', staff_api.BusinessMemberListByBusinessID.as_view(), name='business-members-by-id'),
  
]
