from django.urls import path
from . import views




urlpatterns = [

path("business-reward-rules/", views.BusinessRewardRuleListCreateApi.as_view(), name="business-reward-rules"),
path('reward-rule/<int:pk>/set-default/', views.SetDefaultRewardRuleAPI.as_view(), name='set-default-reward-rule'),
path("reward-rules/<int:pk>/details/", views.BusinessRewardRuleDetailApi.as_view(), name="business-reward-rule-detail"),

path("business-card/", views.BusinessCardDesignAPI.as_view(), name="business-card-list"),

path('new-member/', views.NewMemberEnrollAPI.as_view(), name='new-member'),
path("member/<int:card_number>/", views.MemberDetailByCardNumberApi.as_view(), name="member-by-card"),

path("check-member-active/", views.CheckMemberActive.as_view(), name="business-check-member-active"),
path("member-active/by-mobile-no/", views.CheckMemberActiveByCardmobileNo.as_view(), name="check-member-active"),
    

    
  
]
