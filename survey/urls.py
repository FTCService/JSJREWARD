from django.urls import path
from . import views


app_name = "survey"

urlpatterns = [

     path('feedback/', views.SurveySubmitAPI.as_view(), name='feedback'),
]
