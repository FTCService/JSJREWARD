from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from business.models import BusinessRewardRule,BusinessMember, CardTransaction, BusinessCardDesign, CumulativePoints
from .serializers import (
                          BusinessRewardRuleSerializer, 
                          BusinessMemberSerializer,
                          CardTransactionSerializer,
                          BusinessCardDesignSerializer,
                          NewMemberSerializer,
                          FetchMemberDetailsSerializer,
                          RedeemPointsSerializer,
                          SpecificCardTransactionSerializer,
                          CheckMemberActiveSerializer
                          )
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from helpers.utils import send_sms
from datetime import datetime, timedelta
from django.db.models import Q
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Avg, Count
from rest_framework.exceptions import ValidationError
from .authentication import SSOBusinessTokenAuthentication

# -------------------  business setup rules for reward cards of members  ------------------------
class BusinessRewardRuleListCreateApi(APIView):
    """
    API to list and create Business Reward Rules.
    """
    authentication_classes = [SSOBusinessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve a list of all Business Reward Rules.",
        responses={200: BusinessRewardRuleSerializer(many=True)},tags=["business"]
    )
    def get(self, request):
        """Retrieve all Business Reward Rules for the logged-in business."""
        if not hasattr(request.user, "business_id") or not request.user.business_id:
            return Response(
                {"success": False, "error": "Only businesses with a valid business_id can access this API."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # ✅ Filter using business_id instead of the default primary key
        reward_rules = BusinessRewardRule.objects.filter(RewardRuleBizId__business_id=request.user.business_id)
        serializer = BusinessRewardRuleSerializer(reward_rules, many=True)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=BusinessRewardRuleSerializer,
        operation_description="Create a new Business Reward Rule.",tags=["business"]
    )
    def post(self, request):
        """Create a new Business Reward Rule for the logged-in business."""
        if isinstance(request.data, list):  # ✅ Prevent list format errors
            return Response(
                {"success": False, "error": "Invalid data format. Expected an object, got a list."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = BusinessRewardRuleSerializer(data=request.data, context={"request": request})  # ✅ Pass request context
        
        if serializer.is_valid():
            rule = serializer.save()
            return Response(
                {"success": True, "message": "Business Reward Rule created successfully.", "data": serializer.data}, 
                status=status.HTTP_201_CREATED
            )
        
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    

# ----------------  get details of rules ------------------------
class BusinessRewardRuleDetailApi(APIView):
    """
    API to retrieve, update, or delete a specific Business Reward Rule.
    """
    authentication_classes = [SSOBusinessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve details of a specific Business Reward Rule.",
        responses={200: BusinessRewardRuleSerializer()},tags=["business"]
    )
    def get(self, request, pk):
        try:
            reward_rule = BusinessRewardRule.objects.get(pk=pk)
            serializer = BusinessRewardRuleSerializer(reward_rule)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except BusinessRewardRule.DoesNotExist:
            return Response({"error": "Reward Rule not found."}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        request_body=BusinessRewardRuleSerializer,
        operation_description="Update an existing Business Reward Rule.",tags=["business"]
    )
    def put(self, request, pk):
        try:
            reward_rule = BusinessRewardRule.objects.get(pk=pk)
            serializer = BusinessRewardRuleSerializer(reward_rule, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"message": "Reward Rule updated successfully.", "data": serializer.data}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except BusinessRewardRule.DoesNotExist:
            return Response({"error": "Reward Rule not found."}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="Delete a specific Business Reward Rule.",
        responses={204: "Deleted successfully"},tags=["business"]
    )
    def delete(self, request, pk):
        try:
            reward_rule = BusinessRewardRule.objects.get(pk=pk)
            reward_rule.delete()
            return Response({"message": "Reward Rule deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except BusinessRewardRule.DoesNotExist:
            return Response({"error": "Reward Rule not found."}, status=status.HTTP_404_NOT_FOUND)
        
        

class SetDefaultRewardRuleAPI(APIView):
    """
    API to set a specific Business Reward Rule as the default one.
    """
    authentication_classes = [SSOBusinessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Set a specific reward rule as the default for the logged-in business.",
        responses={
            200: openapi.Response(description="Successfully set as default"),
            403: openapi.Response(description="User not authorized"),
            404: openapi.Response(description="Rule or business not found"),
        },
        operation_summary="Set Default Reward Rule",tags=["business"]
    )
    def post(self, request, pk):
        if not hasattr(request.user, "business_id") or not request.user.business_id:
            return Response({"success": False, "error": "Invalid business user."}, status=status.HTTP_403_FORBIDDEN)

        business_id = request.user.business_id

        
        try:
            rule_to_set_default = BusinessRewardRule.objects.get(pk=pk, RewardRuleBizId=business_id)
        except BusinessRewardRule.DoesNotExist:
            return Response({"success": False, "error": "Reward Rule not found for this business."}, status=status.HTTP_404_NOT_FOUND)

        BusinessRewardRule.objects.filter(RewardRuleBizId=business_id).update(RewardRuleIsDefault=False)

        rule_to_set_default.RewardRuleIsDefault = True
        rule_to_set_default.save()

        return Response({"success": True, "message": "Default reward rule updated successfully."}, status=status.HTTP_200_OK)
    
    
    

class BusinessRewardRuleDetailApi(APIView):
    """
    API to retrieve, update, or delete a specific Business Reward Rule.
    """
    authentication_classes = [SSOBusinessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve details of a specific Business Reward Rule.",
        responses={200: BusinessRewardRuleSerializer()},tags=["business"]
    )
    def get(self, request, pk):
        try:
            reward_rule = BusinessRewardRule.objects.get(pk=pk)
            serializer = BusinessRewardRuleSerializer(reward_rule)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except BusinessRewardRule.DoesNotExist:
            return Response({"error": "Reward Rule not found."}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        request_body=BusinessRewardRuleSerializer,
        operation_description="Update an existing Business Reward Rule.",tags=["business"]
    )
    def put(self, request, pk):
        try:
            reward_rule = BusinessRewardRule.objects.get(pk=pk)
            serializer = BusinessRewardRuleSerializer(reward_rule, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"message": "Reward Rule updated successfully.", "data": serializer.data}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except BusinessRewardRule.DoesNotExist:
            return Response({"error": "Reward Rule not found."}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="Delete a specific Business Reward Rule.",
        responses={204: "Deleted successfully"},tags=["business"]
    )
    def delete(self, request, pk):
        try:
            reward_rule = BusinessRewardRule.objects.get(pk=pk)
            reward_rule.delete()
            return Response({"message": "Reward Rule deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except BusinessRewardRule.DoesNotExist:
            return Response({"error": "Reward Rule not found."}, status=status.HTTP_404_NOT_FOUND)
        
        
        

class BusinessCardDesignAPI(APIView):
    """
    API to perform CRUD operations on Business Card Design.
    """

    authentication_classes = [SSOBusinessTokenAuthentication]  # Custom authentication
    permission_classes = [IsAuthenticated]  # Only authenticated users allowed

    @swagger_auto_schema(
        request_body=BusinessCardDesignSerializer,
        operation_description="Create or update a Business Card Design.",tags=["business"]
    )
    def post(self, request):
        """
        Create a new Business Card Design or update the existing one for the authenticated business.
        """
        if not hasattr(request.user, "business_id") or not request.user.business_id:
            return Response(
                {"error": "Only businesses can create Business Card Designs."},
                status=status.HTTP_403_FORBIDDEN
            )

       
        business_instance = request.user.business_id
        

        # Copy request data and assign business ID
        data = request.data.copy()
        data["CardDsgBizId"] = business_instance  

        # Try to get the existing business card or create a new one
        business_card, created = BusinessCardDesign.objects.update_or_create(
            CardDsgBizId=business_instance,  # Ensure linking to business instance
            defaults=data  # Update fields if exists, otherwise create
        )

        return Response(
            {
                "message": "Business Card Design created successfully" if created else "Business Card Design updated successfully",
                "id": business_card.id,
                "business_id": business_instance,  
                "business_name": business_instance 
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    @swagger_auto_schema(
        operation_description="Retrieve the Business Card Design for the logged-in business.",tags=["business"]
    )
    def get(self, request):
        """
        Retrieve the Business Card Design for the authenticated business.
        """
        if not hasattr(request.user, "business_id") or not request.user.business_id:
            return Response(
                {"error": "Only businesses can view Business Card Designs."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            business_instance = request.user.business_id
            business_card = BusinessCardDesign.objects.get(CardDsgBizId=business_instance)
        except BusinessCardDesign.DoesNotExist:
            return Response({"error": "No Business Card Design found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = BusinessCardDesignSerializer(business_card)
        return Response(serializer.data, status=status.HTTP_200_OK)