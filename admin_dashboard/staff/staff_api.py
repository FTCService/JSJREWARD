from rest_framework.exceptions import NotFound
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.shortcuts import get_object_or_404

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from admin_dashboard.authentication import SSOUserTokenAuthentication
from business.models import  BusinessMember
from .serializers import  BusinessMemberClubSerializer
from helpers.utils import get_member_details_by_card



class BusinessMemberListByBusinessID(APIView):
    @swagger_auto_schema(
        operation_description="Get all Business Members by Business ID",
        manual_parameters=[
            openapi.Parameter(
                "business_id",
                openapi.IN_PATH,
                description="ID of the business to fetch members for",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={200: BusinessMemberClubSerializer(many=True)}
    )
    def get(self, request, business_id):
        members = BusinessMember.objects.filter(BizMbrBizId=business_id)
        serializer = BusinessMemberClubSerializer(members, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)