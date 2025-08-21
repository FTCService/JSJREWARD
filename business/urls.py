from django.urls import path
from . import views




urlpatterns = [
    
    path('member/active_in_clube/', views.BusinessMembercheckActiveAPI.as_view(), name='member-active_in_clube'),

    path("business-reward-rules/", views.BusinessRewardRuleListCreateApi.as_view(), name="business-reward-rules"),
    path('reward-rule/<int:pk>/set-default/', views.SetDefaultRewardRuleAPI.as_view(), name='set-default-reward-rule'),
    path("reward-rules/<int:pk>/details/", views.BusinessRewardRuleDetailApi.as_view(), name="business-reward-rule-detail"),

    
    path("business-card/", views.BusinessCardDesignAPI.as_view(), name="business-card-list"),

    path('new-member/', views.NewMemberEnrollAPI.as_view(), name='new-member'),
    path("member/<int:card_number>/", views.MemberDetailByCardNumberApi.as_view(), name="member-by-card"),

    path("check-member-active/", views.CheckMemberActive.as_view(), name="business-check-member-active"),
    path("member-active/by-mobile-no/", views.CheckMemberActiveByCardmobileNo.as_view(), name="check-member-active"),
    path("business-members/", views.BusinessMemberListCreateApi.as_view(), name="business-member-list-create"),
    path("business-members/<int:pk>/", views.BusinessMemberDetailApi.as_view(), name="business-member-detail"),
    path("transactions/", views.CardTransactionApi.as_view(), name="card-transactions"),

    path("transactions/<int:transaction_id>/", views.CardTransactionDetailApi.as_view(), name="card-transaction-detail"),

    path("member/specific/transactions/<str:card_number>", views.SpecificCardTransactionApi.as_view(), name="specific_card_transactions"),
    
    path('redeem/', views.RedeemPointsAPIView.as_view(), name="redeem-points"),
    
    path("business-reports/", views.BusinessReportsAPIView.as_view(), name="business_reports"),
    
    path('member/join-requests/', views.MemberRequestListApi.as_view(), name='list-join-requests'),
    path('member/join-requests/approve/<int:request_id>/', views.ApproveJoinRequestView.as_view(), name='approve-join-request'),
  
]
