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
                          CheckMemberActiveSerializer,
                          MemberByCardSerializer
                          
                          )
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from helpers.utils import send_sms, get_member_details_by_mobile, get_member_details_by_card
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
                "business_name": request.user.business_name
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
    
    
    
    
# class NewMemberEnrollAPI(APIView):
#     def post(self, request):
#         mobile_number = request.data.get("mobile_number")
#         if not mobile_number:
#             return Response({"message": "Mobile number is required."})

#         member_data = get_member_details_by_mobile(mobile_number)
#         if not member_data:
#             return Response({"message": "Member not found."}, status=200)

#         # You now have full member data from auth service
#         mbrcardno = member_data.get("mbrcardno")
#         full_name = member_data.get("full_name")
#         # ... use other fields as needed

#         return Response({"success": True, "member": member_data,"mbrcardno":mbrcardno,"full_name":full_name})
    



class NewMemberEnrollAPI(APIView):
    """
    API to generate a signup link with query parameters and send via SMS.
    """

    authentication_classes = [SSOBusinessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=NewMemberSerializer,
        operation_description="New member enrollment (Send link via SMS)."
    )
    def post(self, request):
        serializer = NewMemberSerializer(data=request.data)

        if serializer.is_valid():
            full_name = serializer.validated_data.get("full_name")
            mobile_number = serializer.validated_data.get("mobile_number")

            refer_id =request.user.business_id
            
            if not refer_id:
                return Response(
                    {"message": "User does not have a business_id"},
                    status=status.HTTP_200_OK
                )

            # Fetch member data from external AUTH service
            member_data = get_member_details_by_mobile(mobile_number)
            print(member_data)

            if member_data:
                mbrcardno = member_data.get("mbrcardno")
                print(mbrcardno)
                # Check if member is active under this business
                business_member = BusinessMember.objects.filter(
                    BizMbrCardNo=mbrcardno,
                    BizMbrBizId=refer_id
                ).first()

                if business_member:
                    return Response(
                        {
                            "is_present": True,
                            "is_active": True,
                            "mbrcardno": mbrcardno,
                            "full_name": member_data.get("full_name"),
                            "message": "This mobile number is already an active member of your business."
                        },
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        {
                            "is_present": True,
                            "is_active": False,
                            "mbrcardno": mbrcardno,
                            "full_name": member_data.get("full_name"),
                            "message": "This mobile number is registered but not active under your business."
                        },
                        status=status.HTTP_200_OK
                    )

            # If not found in AUTH service
            response_data = {
                "is_present": False,
                "is_active": False,
                "message": "This mobile number is not registered."
            }

            # Generate signup link
            base_url = "https://reward.jsjcard.com" if not settings.DEBUG else "http://127.0.0.1:8000"
            signup_url = f"{base_url}/member/sign-up/?referId={refer_id}&name={full_name}&phone={mobile_number}"

            send_sms({
                "mobile_number": mobile_number,
                "message": f"Welcome {full_name}! Complete your signup here: {signup_url}"
            })

            response_data["signup_url"] = signup_url
            response_data["message"] = "Signup link sent via SMS"

            return Response(response_data, status=status.HTTP_200_OK)

        return Response({"error": "Invalid data", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)




# -------------- this function for getting the member information through card Number -------------------     
class MemberDetailByCardNumberApi(APIView):
    authentication_classes = [SSOBusinessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve Business KYC details along with cumulative points",
        responses={200: MemberByCardSerializer()}
    )
    def get(self, request, card_number):
        if not card_number:
            return Response({"error": "Card number is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch member data from external AUTH service
        member_data = get_member_details_by_card(card_number)
        if not member_data:
            return Response({"error": "Member not found."}, status=status.HTTP_404_NOT_FOUND)

        # Extract mobile number and other details from external service response
        mobile_number = member_data.get("mobile_number")
        full_name = member_data.get("full_name")

        # Continue logic using raw card_number
        business_member = BusinessMember.objects.filter(
            BizMbrCardNo=card_number,
            BizMbrBizId=request.user.business_id
        ).first()

        milestone = (
            business_member.BizMbrRuleId.RewardRuleMilestone
            if business_member and business_member.BizMbrRuleId else None
        )

        # Fetch cumulative points
        cumulative_points = CumulativePoints.objects.filter(
            CmltvPntsMbrCardNo=card_number
        ).first()

        # Prepare response data
        response_data = {
            "mbrcardno": card_number,
            "full_name": full_name,
            "mobile_number": mobile_number,
            "business_id": request.user.business_id,
            "business_name": request.user.business_name,
            "RewardRuleMilestone": milestone,
            "cumulative_points": {
                "lifetime_earned_points": cumulative_points.LifetimeEarnedPoints if cumulative_points else 0.00,
                "lifetime_redeemed_points": cumulative_points.LifetimeRedeemedPoints if cumulative_points else 0.00,
                "current_balance": cumulative_points.CurrentBalance if cumulative_points else 0.00,
                "total_purchase_amount": cumulative_points.TotalPurchaseAmount if cumulative_points else 0.00,
                "last_updated": cumulative_points.LastUpdated if cumulative_points else None,
            },
        }

        return Response(response_data, status=status.HTTP_200_OK)



class CheckMemberActive(APIView):
    """
    API to check if a member is active based on the provided card number.
    """
    authentication_classes = [SSOBusinessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Check if a member is active based on the provided card number.",
        responses={200: CheckMemberActiveSerializer()}
    )
    def get(self, request):
        """
        Check if a member is active.
        """
        
        if not hasattr(request.user, "business_id"):
            return Response(
                {"success": False, "error": "User is not a Business.", "BizMbrIsActive": False},
                status=status.HTTP_403_FORBIDDEN
            )
        card_number = request.query_params.get("card_number")  # Get card number from request

        if not card_number:
            return Response(
                {"success": False, "error": "Card number is required.", "BizMbrIsActive": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        business_id = request.user.business_id  
        
        # Get the first active member if multiple exist
        business_member = BusinessMember.objects.filter(BizMbrCardNo=card_number,
            BizMbrBizId=business_id ).first()

        if not business_member:  # Handle case where no member is found
            return Response(
                {"success": False, "error": "No active member found for this card number.", "BizMbrIsActive": False},
                status=status.HTTP_200_OK
            )

        serializer = CheckMemberActiveSerializer(business_member)
        return Response(
            {"success": True, "message": "Member found.", "data": serializer.data},
            status=status.HTTP_200_OK
        )
        


        
class CheckMemberActiveByCardmobileNo(APIView):
    """
    API to check if a member is active based on the provided mobile number.
    """
    authentication_classes = [SSOBusinessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Check if a member is active based on the provided mobile number.",
        responses={200: CheckMemberActiveSerializer()}
    )
    def get(self, request):
        """
        Check if a member is active.
        """
        # Check if user has business_id
        if not hasattr(request.user, "business_id"):
            return Response(
                {"success": False, "error": "User is not a Business.", "BizMbrIsActive": False},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get mobile number from query params
        mobile_number = request.query_params.get("mobile_number")

        if not mobile_number:
            return Response(
                {"success": False, "error": "Mobile number is required.", "BizMbrIsActive": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Fetch member data from external AUTH service
            member_data = get_member_details_by_mobile(mobile_number)
            mbrcardno = member_data.get("mbrcardno")
            print("mbrcardno:", mbrcardno)
        except Exception:
            return Response(
                {"success": False, "message": "No member found with this mobile number.", "BizMbrIsActive": False},
                status=status.HTTP_200_OK
            )

        business_id = request.user.business_id

        # Get the first active business member linked to this member and business
        business_member = BusinessMember.objects.filter(
            BizMbrCardNo=mbrcardno,
            BizMbrBizId=business_id,
            BizMbrIsActive=True
        ).first()

        if not business_member:
            return Response(
                {"success": False, "message": "No active member found for this business.", "BizMbrIsActive": False, "card_number":mbrcardno},
                status=status.HTTP_200_OK
            )

        # Serialize the active business member
        serializer = CheckMemberActiveSerializer(business_member)
        return Response(
            {"success": True, "message": "Active member found.", "data": serializer.data, "BizMbrIsActive": True, "card_number":card_number},
            status=status.HTTP_200_OK
        )
