from django.urls import path
from . import views


app_name = "member"

urlpatterns = [

    path("business-store/", views.BusinessStoreListApi.as_view(), name="business-member-list-create"),
    path("business-store/details/<int:biz_id>/", views.BusinessStoreDetailsApi.as_view(), name="business-member-list-create"),

    path('member/scan-qr/', views.MemberQRScanAPIView.as_view(), name='member-scan-qr'),
    
    path('transactions/<int:biz_id>/', views.MemberTransactionHistoryApi.as_view(), name='member-transactions'),
    path('transaction/<int:biz_id>/<int:transaction_id>/', views.TransactionDetailApi.as_view(), name='transaction-detail'),
    
     
]
