from django.urls import path
from . import views




urlpatterns = [

path("business-reward-rules/", views.BusinessRewardRuleListCreateApi.as_view(), name="business-reward-rules"),
    

    
  
]
