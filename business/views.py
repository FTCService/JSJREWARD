from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from business.models import BusinessRewardRule,BusinessMember, CardTransaction, BusinessCardDesign, CumulativePoints, MemberJoinRequest
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
                          MemberByCardSerializer,
                          BusinessMemberSerializer,
                          MemberJoinRequestSerializer
                          
                          )
from helpers.utils import send_sms, get_member_details_by_mobile, get_member_details_by_card
from helpers.card_utils import get_primary_card_from_remote
from datetime import datetime, timedelta
from django.db.models import Q
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Avg, Count
from rest_framework.exceptions import ValidationError
from .authentication import SSOBusinessTokenAuthentication
import csv, io
from django.utils import timezone
from helpers.emails import send_template_email


class BulkBusinessRewardRuleUpload(APIView):
    def post(self, request, *args, **kwargs):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "CSV file is required"}, status=status.HTTP_400_BAD_REQUEST)

        data_set = file.read().decode("UTF-8")
        io_string = io.StringIO(data_set)
        csv_reader = csv.DictReader(io_string)

        created_rules = []

        for row in csv_reader:
            try:
                reward_rule = BusinessRewardRule.objects.create(
                    id=row.get("id"),
                    RewardRuleBizId=int(row.get("RewardRuleBizId")),
                    RewardRuleType=row.get("RewardRuleType"),
                    RewardRuleNotionalValue=row.get("RewardRuleNotionalValue"),
                    RewardRuleValue=row.get("RewardRuleValue") or None,
                    RewardRuleValidityPeriodYears=row.get("RewardRuleValidityPeriodYears") or None,
                    RewardRuleMilestone=row.get("RewardRuleMilestone") or None,
                    RewardRuleIsDefault=row.get("RewardRuleIsDefault", "False").lower() in ["true", "1"]
                )
                created_rules.append(reward_rule.id)

            except Exception as e:
                return Response({
                    "error": f"Failed to process row: {row}",
                    "details": str(e)
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": f"{len(created_rules)} reward rules uploaded successfully.",
            "reward_rule_ids": created_rules
        }, status=status.HTTP_201_CREATED)


class BulkBusinessMemberUpload(APIView):
    def post(self, request, *args, **kwargs):
        file = request.FILES.get("file")
        if not file:
            return Response({"error": "CSV file is required"}, status=status.HTTP_400_BAD_REQUEST)

        data_set = file.read().decode("UTF-8")
        io_string = io.StringIO(data_set)
        csv_reader = csv.DictReader(io_string)

        created_members = []

        for row in csv_reader:
            try:
                # Validate Rule ID exists
                rule_id = row.get("BizMbrRuleId")
                try:
                    reward_rule = BusinessRewardRule.objects.get(id=rule_id)
                except BusinessRewardRule.DoesNotExist:
                    return Response({
                        "error": f"Reward Rule with ID {rule_id} does not exist.",
                        "row": row
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Parse BizMbrValidityEnd date if provided
                validity_end = row.get("BizMbrValidityEnd")
                validity_end_date = None
                if validity_end:
                    validity_end_date = datetime.fromisoformat(validity_end)

                # Create BusinessMember object
                member = BusinessMember.objects.create(
                    id = row.get("id"),
                    BizMbrBizId=int(row.get("BizMbrBizId")),
                    BizMbrCardNo=int(row.get("BizMbrCardNo")),
                    BizMbrRuleId=reward_rule,
                    BizMbrIsActive=row.get("BizMbrIsActive", "False").lower() in ["true", "1"],
                    BizMbrValidityEnd=validity_end_date
                )

                created_members.append(member.id)

            except Exception as e:
                return Response({
                    "error": f"Failed to process row: {row}",
                    "details": str(e)
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": f"{len(created_members)} business members uploaded successfully.",
            "member_ids": created_members
        }, status=status.HTTP_201_CREATED)



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
        reward_rules = BusinessRewardRule.objects.filter(RewardRuleBizId=request.user.business_id).order_by("id") 
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
            return Response({"message": "Please Setup Your Card."}, status=status.HTTP_200_OK)

        serializer = BusinessCardDesignSerializer(business_card)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
    
    

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
            mbrcardno = member_data.get("mbrcardno")
            if mbrcardno:
                
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
            base_url = settings.SITE_BASE_URL
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
        operation_description="Retrieve Business KYC details along with cumulative points (resolves to primary card if secondary provided)",
        responses={200: MemberByCardSerializer()}
    )
    def get(self, request, card_number):
        if not card_number:
            return Response({"error": "Card number is required."}, status=status.HTTP_400_BAD_REQUEST)

        business_id = request.user.business_id

        # ✅ Step 1: Resolve primary card number from external AUTH service
        resolved = get_primary_card_from_remote(card_number, business_id)
        primary_card_number = resolved.get("primary_card_number")

        if not resolved.get("success") or not primary_card_number:
            return Response(
                {"success": False, "message": resolved.get("message", "Card is not associated with this business.")},
                status=status.HTTP_200_OK
            )

        # ✅ Step 2: Fetch member data from external AUTH service using primary card
        member_data = get_member_details_by_card(primary_card_number)
        if not member_data or not member_data.get("mbrcardno"):
            return Response({"message": "Member not found."}, status=status.HTTP_200_OK)

        # ✅ Step 3: Extract details
        mobile_number = member_data.get("mobile_number")
        full_name = member_data.get("full_name")

        # ✅ Step 4: Fetch local business member
        business_member = BusinessMember.objects.filter(
            BizMbrCardNo=primary_card_number,
            BizMbrBizId=business_id
        ).first()

        milestone = (
            business_member.BizMbrRuleId.RewardRuleMilestone
            if business_member and business_member.BizMbrRuleId else None
        )

        # ✅ Step 5: Fetch cumulative points
        cumulative_points = CumulativePoints.objects.filter(
            CmltvPntsMbrCardNo=primary_card_number,
            CmltvPntsBizId=business_id
        ).first()

        # ✅ Step 6: Prepare response
        response_data = {
            "mbrcardno": primary_card_number,  # always return primary card number
            "full_name": full_name,
            "mobile_number": mobile_number,
            "business_id": business_id,
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



# class CheckMemberActive(APIView):
#     """
#     API to check if a member is active based on the provided card number.
#     """
#     authentication_classes = [SSOBusinessTokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     @swagger_auto_schema(
#         operation_description="Check if a member is active based on the provided card number.",
#         responses={200: CheckMemberActiveSerializer()}
#     )
#     def get(self, request):
#         if not hasattr(request.user, "business_id"):
#             return Response(
#                 {"success": False, "error": "User is not a Business."},
#                 status=status.HTTP_403_FORBIDDEN
#             )

#         card_number = request.query_params.get("card_number")
#         if not card_number:
#             return Response(
#                 {"success": False, "error": "Card number is required."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         business_id = request.user.business_id

#         # Step 1: Try resolving from Server A
#         resolved = get_primary_card_from_remote(card_number, business_id)
#         primary_card_number = resolved.get("primary_card_number")

#         if not resolved.get("success") or not primary_card_number:
#             # ⛔ Fall back: maybe this is a primary card directly
#             fallback_member = BusinessMember.objects.filter(
#                 BizMbrCardNo=primary_card_number,
#                 BizMbrBizId=business_id
#             ).first()

#             if fallback_member:
#                 if not fallback_member.BizMbrIsActive:
#                     return Response(
#                         {"success": False, "message": "Member is not active."},
#                         status=status.HTTP_200_OK
#                     )
#                 serializer = CheckMemberActiveSerializer(fallback_member)
#                 return Response(
#                     {"success": True, "message": "Active member found (primary fallback).", "data": serializer.data},
#                     status=status.HTTP_200_OK
#                 )

#             return Response(
#                 {"success": False, "message": resolved.get("message", "This card is not associated with this business.")},
#                 status=status.HTTP_200_OK
#             )

#         # Step 2: Confirm with get_member_details_by_card
#         member_data = get_member_details_by_card(primary_card_number)
#         if not member_data:
#             return Response(
#                 {"success": False, "message": "Card is not associated with your business."},
#                 status=status.HTTP_200_OK
#             )

#         # Step 3: Find BusinessMember
#         business_member = BusinessMember.objects.filter(
#             BizMbrCardNo=primary_card_number,
#             BizMbrBizId=business_id
#         ).first()

#         if not business_member:
#             return Response(
#                 {"success": False, "error": "No active member found for this card number."},
#                 status=status.HTTP_200_OK
#             )

#         if not business_member.BizMbrIsActive:
#             return Response(
#                 {"success": False, "message": "Member is not active.", "BizMbrIsActive": False},
#                 status=status.HTTP_200_OK
#             )

#         # Final Step: Return success
#         serializer = CheckMemberActiveSerializer(business_member)
#         return Response(
#             {"success": True, "message": "Active member found.", "data": serializer.data},
#             status=status.HTTP_200_OK
#         )


class CheckMemberActive(APIView):
    """
    API to check if a member is active based on the provided card number.
    Handles secondary cards, primary cards, and cards from other businesses.
    """
    authentication_classes = [SSOBusinessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Check if a member is active based on the provided card number.",
        responses={200: CheckMemberActiveSerializer()}
    )
    def get(self, request):
        if not hasattr(request.user, "business_id"):
            return Response(
                {"success": False, "error": "User is not a Business."},
                status=status.HTTP_403_FORBIDDEN
            )

        card_number = request.query_params.get("card_number")
        if not card_number:
            return Response(
                {"success": False, "error": "Card number is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        business_id = request.user.business_id

        # Step 1: Resolve primary card (external Auth Server)
        resolved = get_primary_card_from_remote(card_number, business_id)
        primary_card_number = resolved.get("primary_card_number")

        # Step 1a: Fallback if resolution failed
        if not resolved.get("success") or not primary_card_number:
            # Check if card exists in current business anyway
            fallback_member = BusinessMember.objects.filter(
                BizMbrCardNo=card_number,
                BizMbrBizId=business_id
            ).first()

            if fallback_member:
                if not fallback_member.BizMbrIsActive:
                    return Response(
                        {"success": False, "message": "Member is not active."},
                        status=status.HTTP_200_OK
                    )
                serializer = CheckMemberActiveSerializer(fallback_member)
                return Response(
                    {"success": True, "message": "Active member found (primary fallback).", "data": serializer.data},
                    status=status.HTTP_200_OK
                )

            # Check if card exists in other business
            other_business_member = BusinessMember.objects.filter(
                BizMbrCardNo=card_number
            ).first()
            if other_business_member:
                return Response(
                    {
                        "success": False,
                        "message": "This card belongs to another business.",
                        "other_business_id": other_business_member.BizMbrBizId
                    },
                    status=status.HTTP_200_OK
                )

            return Response(
                {"success": False, "message": resolved.get("message", "This card is not registered.")},
                status=status.HTTP_200_OK
            )

        # Step 2: Confirm member exists via Auth Server
        member_data = get_member_details_by_card(primary_card_number)
        if not member_data:
            return Response(
                {"success": False, "message": "Card is not associated with your business."},
                status=status.HTTP_200_OK
            )

        # Step 3: Find BusinessMember in current business
        business_member = BusinessMember.objects.filter(
            BizMbrCardNo=primary_card_number,
            BizMbrBizId=business_id
        ).first()

        if not business_member:
            # Card exists, but belongs to other business?
            other_business_member = BusinessMember.objects.filter(
                BizMbrCardNo=primary_card_number
            ).first()
            if other_business_member:
                return Response(
                    {
                        "success": False,
                        "message": "This card belongs to another business.",
                        "other_business_id": other_business_member.BizMbrBizId
                    },
                    status=status.HTTP_200_OK
                )

            return Response(
                {"success": False, "error": "No active member found for this card number."},
                status=status.HTTP_200_OK
            )

        # Step 4: Check active status
        if not business_member.BizMbrIsActive:
            return Response(
                {"success": False, "message": "Member is not active.", "BizMbrIsActive": False},
                status=status.HTTP_200_OK
            )

        # Step 5: Return success
        serializer = CheckMemberActiveSerializer(business_member)
        return Response(
            {"success": True, "message": "Active member found.", "data": serializer.data},
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

        
        # Fetch member data from external AUTH service
        member_data = get_member_details_by_mobile(mobile_number)
        mbrcardno = member_data.get("mbrcardno")
        if not mbrcardno:
            return Response(
                {"success": False, "message": "No member found with this mobile number.", "BizMbrIsActive": False, "is_present":False},
                status=status.HTTP_200_OK
            )
        full_name = member_data.get("full_name")
        business_id = request.user.business_id

        # Get the first active business member linked to this member and business
        business_member = BusinessMember.objects.filter(
            BizMbrCardNo=mbrcardno,
            BizMbrBizId=business_id,
            BizMbrIsActive=True
        ).first()

        if not business_member:
            return Response(
                {"success": False, "message": "No active member found for this business.", "BizMbrIsActive": False, "card_number":mbrcardno,"is_present":True,"full_name":full_name,"mobile_number":mobile_number},
                status=status.HTTP_200_OK
            )

        # Serialize the active business member
        serializer = CheckMemberActiveSerializer(business_member)
        return Response(
            {"success": True, "message": "Active member found.", "data": serializer.data, "BizMbrIsActive": True, "card_number":mbrcardno,"is_present":True},
            status=status.HTTP_200_OK
        )





# ---------------  Business Member get and List  ------------------       
class BusinessMemberListCreateApi(APIView):
    """
    API to list and create Business Members.
    """
    authentication_classes = [SSOBusinessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve a list of all Business Members.",
        responses={200: BusinessMemberSerializer(many=True)}
    )
    def get(self, request):
        """
        List all Business Members.
        """
        business_members = BusinessMember.objects.filter(BizMbrBizId=request.user.business_id)
        
        data = []
        for member in business_members:
            print(member.BizMbrRuleId.id, "-----")
            member_data = get_member_details_by_card(card_number=member.BizMbrCardNo)
            full_name = member_data.get("full_name")
            mobile_number = member_data.get("mobile_number")
            data.append({
                "BizMbrBizId": member.BizMbrBizId,  
                "BizMbrCardNo": member.BizMbrCardNo, 
                "BizMbrRuleId": member.BizMbrRuleId.id,  
                "BizMbrIssueDate": member.BizMbrIssueDate,  
                "BizMbrValidityEnd": member.BizMbrValidityEnd,
                "BizMbrIsActive": member.BizMbrIsActive,
                "full_name": full_name,  
                "mobile_number": mobile_number  # Fetch member's mobile number
            })
        serializer = BusinessMemberSerializer(business_members, many=True)
        return Response(data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
    request_body=BusinessMemberSerializer,
    operation_description="Create a Business Member from a scanned QR code (card number)."
    )
    def post(self, request):
        """
        Handle the card_number from the QR code and create a Business Member.
        """
        card_number = request.data.get("BizMbrCardNo")  # Get card number from the scanned QR code
        reward_rule_id = request.data.get("BizMbrRuleId")  

        if not card_number or not reward_rule_id:
            return Response({"success": False, "error": "card_number and reward_rule_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            business_instance = request.user.business_id
            business_name = request.user.business_name
            # ✅ Fetch Reward Rule associated with the authenticated business user
            reward_rule = BusinessRewardRule.objects.get(
                pk=reward_rule_id, 
                RewardRuleBizId=business_instance
            )

            # ✅ Convert validity period to years
            validity_period_years = int(reward_rule.RewardRuleValidityPeriodYears)  
            current_date = datetime.now()
            validity_end_date = current_date + timedelta(days=validity_period_years * 365)  # Convert years to days

            # ✅ Fetch the Member from the card number
            
            member_data = get_member_details_by_card(card_number)
            
            member = member_data.get("mbrcardno")
            email = member_data.get("email")
            full_name = member_data.get("full_name")

            # ✅ Check if an active membership already exists for this business and card
            existing_membership = BusinessMember.objects.filter(
                BizMbrBizId=business_instance,
                BizMbrCardNo=member,
                BizMbrIsActive=True
            ).exists()

            if existing_membership:
                return Response({"success": False, "BizMbrIsActive":False, "error": "This card number is already activated for this business."}, status=status.HTTP_400_BAD_REQUEST)

            # Prepare the data for serializer
            data = {
                "BizMbrBizId": request.user.business_id,  
                "BizMbrCardNo": member,  
                "BizMbrRuleId": reward_rule.id,  
                "BizMbrIssueDate": current_date,  
                "BizMbrValidityEnd": validity_end_date,
                "BizMbrIsActive": True  # Set new entry as active
            }

            # Use the serializer to validate and save the data
            serializer = BusinessMemberSerializer(data=data)
            if serializer.is_valid():
                # Save the BusinessMember
                serializer.save()
                
                 # ✅ Add business_name to email context
                context = {
                    "business_name": business_name,
                    "member_name": full_name,
                    "card_number": member,
                    "validity_end": validity_end_date.strftime('%Y-%m-%d'),
                }

                send_template_email(
                    subject="Membership Enrolled Successfully",
                    template_name="email_template/enroll_member.html",
                    context=context,
                    recipient_list=[email]
                )
                return Response({
                    "success": True,
                    "BizMbrIsActive":True,
                    "message": "Business Member created successfully.",
                    "data": serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({"success": False, "error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except BusinessRewardRule.DoesNotExist:
            return Response({"success": False, "error": "Invalid Reward Rule ID or not associated with this business."}, status=status.HTTP_400_BAD_REQUEST)

       
        except IntegrityError:
            return Response({"success": False, "error": "Failed to insert the record into BusinessMember table."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
    
class BusinessMembercheckActiveAPI(APIView):
    # authentication_classes = [SSOBusinessTokenAuthentication]
    # permission_classes = [IsAuthenticated]
    
    def get(self, request):
        card_number = request.GET.get("card_number")
        business_id = request.GET.get("business_id")
        if not card_number:
            return Response({"message": "card number is required."}, status=status.HTTP_200_OK)
         
        member = BusinessMember.objects.filter(BizMbrCardNo=card_number, BizMbrBizId=business_id).first()
        
        if not member:
            return Response({"message": "Member not active."}, status=status.HTTP_200_OK)

        serializer = BusinessMemberSerializer(member)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    

class BusinessMemberDetailApi(APIView):
    """
    API to retrieve, update, or delete a specific Business Member.
    """
    authentication_classes = [SSOBusinessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve details of a specific Business Member.",
        responses={200: BusinessMemberSerializer()}
    )
    def get(self, request, pk):
        """
        Retrieve a specific Business Member.
        """
        try:
            business_member = BusinessMember.objects.get(pk=pk, BizMbrBizId=request.user.business_id)
            serializer = BusinessMemberSerializer(business_member)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except BusinessMember.DoesNotExist:
            return Response({"error": "Business Member not found."}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        request_body=BusinessMemberSerializer,
        operation_description="Update an existing Business Member."
    )
    def put(self, request, pk):
        """
        Update an existing Business Member.
        """
        try:
            business_member = BusinessMember.objects.get(pk=pk, BizMbrBizId=request.user.business_id)
            serializer = BusinessMemberSerializer(business_member, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"message": "Business Member updated successfully.", "data": serializer.data}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except BusinessMember.DoesNotExist:
            return Response({"error": "Business Member not found."}, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="Delete a specific Business Member.",
        responses={204: "Deleted successfully"}
    )
    def delete(self, request, pk):
        """
        Delete a Business Member.
        """
        try:
            business_member = BusinessMember.objects.get(pk=pk, BizMbrBizId=request.user.business_id)
            business_member.delete()
            return Response({"message": "Business Member deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except BusinessMember.DoesNotExist:
            return Response({"error": "Business Member not found."}, status=status.HTTP_404_NOT_FOUND)
        
        
        
### ------------- ✅ Card Transaction API --------------- ###
class CardTransactionApi(APIView):
    authentication_classes = [SSOBusinessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: CardTransactionSerializer(many=True)})
    def get(self, request):
        transactions = CardTransaction.objects.filter(CrdTrnsBizId=request.user.business_id)
        serializer = CardTransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=CardTransactionSerializer)
    def post(self, request):
        data = request.data.copy()
        data["CrdTrnsBizId"] = request.user.business_id

        serializer = CardTransactionSerializer(data=data)
        if serializer.is_valid():
            try:
                # Extract validated data
                validated_data = serializer.validated_data

                # Create transaction object manually
                transaction = CardTransaction(
                    CrdTrnsBizId=request.user.business_id,
                    CrdTrnsCardNumber=validated_data["CrdTrnsCardNumber"],
                    CrdTrnsPurchaseAmount=validated_data["CrdTrnsPurchaseAmount"],
                    CrdTrnsTransactionType=validated_data["CrdTrnsTransactionType"],
                )

                # Default points
                transaction.CrdTrnsPoint = 0

                # 🔢 Point Calculation Logic
                business_member = BusinessMember.objects.filter(
                    BizMbrCardNo=transaction.CrdTrnsCardNumber,
                    BizMbrBizId=transaction.CrdTrnsBizId,
                    BizMbrIsActive=True
                ).select_related("BizMbrRuleId").first()

                reward_rule = None
                if business_member and business_member.BizMbrRuleId:
                    reward_rule = business_member.BizMbrRuleId
                    reward_notional_value = float(reward_rule.RewardRuleNotionalValue or 1)
                    reward_value = float(reward_rule.RewardRuleValue or 1)

                    if reward_rule.RewardRuleType == "percentage":
                        transaction.CrdTrnsPoint = int((transaction.CrdTrnsPurchaseAmount * reward_value) / 100)
                    elif reward_rule.RewardRuleType == "purchase_value_to_points":
                        transaction.CrdTrnsPoint = int((transaction.CrdTrnsPurchaseAmount * reward_value) / 100)
                    elif reward_rule.RewardRuleType == "flat":
                        transaction.CrdTrnsPoint = int(reward_value)

                # Save the transaction
                transaction.save()
                member_data = get_member_details_by_card(transaction.CrdTrnsCardNumber)
                full_name = member_data.get("full_name")
                email = member_data.get("email")
                # 💡 Update Cumulative Points
                cumulative_points, created = CumulativePoints.objects.get_or_create(
                    CmltvPntsMbrCardNo=transaction.CrdTrnsCardNumber,
                    CmltvPntsBizId=transaction.CrdTrnsBizId,
                    defaults={
                        "LifetimeEarnedPoints": 0,
                        "CurrentBalance": 0,
                        "TotalPurchaseAmount": 0,
                        "LifetimeRedeemedPoints": 0,
                    }
                )

                if transaction.CrdTrnsTransactionType == "Points_Earned":
                    cumulative_points.LifetimeEarnedPoints += transaction.CrdTrnsPoint
                    cumulative_points.CurrentBalance += transaction.CrdTrnsPoint
                    cumulative_points.TotalPurchaseAmount += transaction.CrdTrnsPurchaseAmount

                elif transaction.CrdTrnsTransactionType == "Points_Redeemed":
                    milestone = reward_rule.RewardRuleMilestone if reward_rule and reward_rule.RewardRuleMilestone else 0
                    required_points = milestone if milestone > 0 else transaction.CrdTrnsPoint

                    if cumulative_points.CurrentBalance >= required_points:
                        cumulative_points.LifetimeRedeemedPoints += required_points
                        cumulative_points.CurrentBalance -= required_points
                    else:
                        return Response({
                            "success": False,
                            "message": "Insufficient points for redemption."
                        }, status=status.HTTP_400_BAD_REQUEST)

                cumulative_points.save()
                # Prepare context for email
                email_context = {
                    "full_name": full_name,
                    "transaction_type": transaction.CrdTrnsTransactionType.replace("_", " "),
                    "points": transaction.CrdTrnsPoint,
                    "purchase_amount": transaction.CrdTrnsPurchaseAmount,
                    "card_number": transaction.CrdTrnsCardNumber,
                    "business_name": request.user.business_name,
                }
                # Send email notification
                send_template_email(
                    subject="Your JSJ Card Transaction Summary",
                    template_name="email_template/transaction_notification.html",
                    context=email_context,
                    recipient_list=[email]
                )
                return Response({
                    "success": True,
                    "message": "Transaction recorded successfully.",
                    "transaction_id": transaction.id,
                    "business_id": request.user.business_id,
                    "business_name": request.user.business_name,
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                import traceback
                traceback.print_exc()
                return Response({
                    "success": False,
                    "message": "An error occurred while processing the transaction.",
                    "error": str(e),
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



    
    
    
# ---------------- transaction details ----------------
class CardTransactionDetailApi(APIView):
    authentication_classes = [SSOBusinessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(responses={200: CardTransactionSerializer()})
    def get(self, request, transaction_id):
        """Retrieve details of a specific Card Transaction by ID."""
        try:
            transaction = CardTransaction.objects.get(id=transaction_id, CrdTrnsBizId=request.user.business_id)
        except CardTransaction.DoesNotExist:
            return Response({"error": "Transaction not found or access denied."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CardTransactionSerializer(transaction)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
    
class SpecificCardTransactionApi(APIView):
    """Retrieve transaction history for a specific card, filter by debit and credit, and return cumulative points."""

    authentication_classes = [SSOBusinessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        query_serializer=SpecificCardTransactionSerializer,
        responses={
            200: openapi.Response(description="Transaction history retrieved successfully"),
            400: openapi.Response(description="Bad request"),
            404: openapi.Response(description="No transactions found for this card"),
        }
    )
    def get(self, request, card_number):
        serializer = SpecificCardTransactionSerializer(data=request.query_params)

        if not serializer.is_valid():
            return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        transaction_type = serializer.validated_data.get("transaction_type")

        # Fetch transactions for the given card number
        transactions = CardTransaction.objects.filter(
            CrdTrnsBizId=request.user.business_id,
            CrdTrnsCardNumber=card_number
        )

        if transaction_type:
            transactions = transactions.filter(CrdTrnsTransactionType=transaction_type.lower())

        # Fetch cumulative points
        try:
            cumulative_points = CumulativePoints.objects.get(
                CmltvPntsMbrCardNo=card_number,
                CmltvPntsBizId=request.user.business_id
            )
            cumulative_data = {
                "LifetimeEarnedPoints": cumulative_points.LifetimeEarnedPoints,
                "LifetimeRedeemedPoints": cumulative_points.LifetimeRedeemedPoints,
                "CurrentBalance": cumulative_points.CurrentBalance,
                "TotalPurchaseAmount": cumulative_points.TotalPurchaseAmount,
                "LastUpdated": cumulative_points.LastUpdated
            }
        except CumulativePoints.DoesNotExist:
            cumulative_data = {"message": "No cumulative points data found for this card."}

        # Get reward rule info
        try:
            business_member = BusinessMember.objects.select_related("BizMbrRuleId").get(
                BizMbrBizId=request.user.business_id,
                BizMbrCardNo=card_number,
                BizMbrIsActive=True
            )
            reward_rule = business_member.BizMbrRuleId
            reward_info = {
                "RewardRuleId": reward_rule.id,
                "RewardRuleType": reward_rule.RewardRuleType,
                "RewardRuleNotionalValue": reward_rule.RewardRuleNotionalValue,
                "RewardRuleValue": reward_rule.RewardRuleValue
            }
        except BusinessMember.DoesNotExist:
            reward_info = {"message": "No active reward rule assigned for this card."}

        if not transactions.exists():
            return Response(
                {
                    "success": False,
                    "message": "No transactions found for this card.",
                    "cumulative_points": cumulative_data,
                    "reward_info": reward_info
                },
                status=status.HTTP_200_OK
            )

        transaction_serializer = CardTransactionSerializer(transactions, many=True)
        
        return Response(
            {
                "success": True,
                "transactions": transaction_serializer.data,
                "cumulative_points": cumulative_data,
                "reward_info": reward_info
            },
            status=status.HTTP_200_OK
        )



# -------------- create a redeem transaction -------------- #
class RedeemPointsAPIView(APIView):
    """API endpoint for redeeming fixed milestone points."""

    @swagger_auto_schema(
        request_body=RedeemPointsSerializer,
        responses={
            200: openapi.Response(
                description="Points redemption status",
                examples={
                    "application/json": {
                        "success": False,
                        "error": "Insufficient points for redemption."
                    }
                }
            ),
            201: openapi.Response(
                description="Points redeemed successfully",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Points redeemed successfully!",
                        "transaction_id": 5
                    }
                }
            ),
        }
    )
    def post(self, request):
        serializer = RedeemPointsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        card_number = serializer.validated_data["card_number"]
        business_id = serializer.validated_data["business_id"]
        member_data = get_member_details_by_card(card_number)
        full_name = member_data.get("full_name")
        email = member_data.get("email")
        # 🔍 Fetch cumulative points
        try:
            cumulative_points = CumulativePoints.objects.get(
                CmltvPntsMbrCardNo=card_number,
                CmltvPntsBizId=business_id
            )
        except CumulativePoints.DoesNotExist:
            return Response(
                {"success": False, "message": "No cumulative points found for this card and business."},
                status=status.HTTP_200_OK
            )

        # 🔍 Fetch active business member and reward rule
        business_member = BusinessMember.objects.filter(
            BizMbrCardNo=card_number,
            BizMbrBizId=business_id,
            BizMbrIsActive=True
        ).select_related("BizMbrRuleId").first()

        if not business_member or not business_member.BizMbrRuleId:
            return Response(
                {"success": False, "message": "No active reward rule found for this member."},
                status=status.HTTP_200_OK
            )

        reward_rule = business_member.BizMbrRuleId
        milestone = reward_rule.RewardRuleMilestone

        if cumulative_points.CurrentBalance < milestone:
            return Response(
                {"success": False, "message": "Insufficient points for redemption."},
                status=status.HTTP_200_OK
            )

        # 💾 Create transaction
        transaction = CardTransaction.objects.create(
            CrdTrnsCardNumber=card_number,
            CrdTrnsBizId=business_id,
            CrdTrnsPurchaseAmount=0,
            CrdTrnsPoint=milestone,
            CrdTrnsTransactionType="Points_Redeemed"
        )

        # 🔄 Update points
        cumulative_points.LifetimeRedeemedPoints += milestone
        cumulative_points.CurrentBalance -= milestone
        cumulative_points.save()
        # Prepare email context
        email_context = {
            "full_name": full_name,
            "card_number": card_number,
            "points": milestone,
            "transaction_id": transaction.id
        }

        # Send email
        send_template_email(
            subject="Points Redemption Notification",
            template_name="email_template/redeem_notification.html",
            context=email_context,
            recipient_list=[email]
        )
        return Response(
            {
                "success": True,
                "message": "Points redeemed successfully!",
                "transaction_id": transaction.id
            },
            status=status.HTTP_201_CREATED
        )

    

class BusinessReportsAPIView(APIView):
    """API endpoint for business reports."""
    
    authentication_classes = [SSOBusinessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Business Reports",
                examples={
                    "application/json": {
                        "success": True,
                        "total_cards_registered": 100,
                        "total_transaction_amount": 50000.00,
                        "average_transaction_amount": 500.00
                    }
                }
            ),
            403: openapi.Response(
                description="Unauthorized access",
                examples={"application/json": {"success": False, "error": "Permission denied"}}
            ),
        }
    )
    def get(self, request):
        """Retrieve business report including total cards, transaction amount, and average transaction amount."""
        business_id = request.user.business_id

        # Count total cards registered for the business
        total_cards_registered = BusinessMember.objects.filter(BizMbrBizId=business_id).count()

        # Get total and average transaction amounts
        transactions = CardTransaction.objects.filter(CrdTrnsBizId=business_id)
        # Total transaction amount (all types)
        total_transaction_amount = transactions.aggregate(
            Sum("CrdTrnsPurchaseAmount")
        )["CrdTrnsPurchaseAmount__sum"] or 0

        # Average amount of credit transactions only
        credit_avg_transaction_amount = transactions.filter(
            CrdTrnsTransactionType='Points_Earned'
        ).aggregate(
            Avg("CrdTrnsPurchaseAmount")
        )["CrdTrnsPurchaseAmount__avg"] or 0
        return Response({
            "success": True,
            "total_cards_registered": total_cards_registered,
            "total_transaction_amount": total_transaction_amount,
            "average_transaction_amount": credit_avg_transaction_amount
        }, status=status.HTTP_200_OK)
        
        
class MemberRequestListApi(APIView):
    authentication_classes = [SSOBusinessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List all pending member join requests for the authenticated business.",
        responses={200: MemberJoinRequestSerializer(many=True)}
    )
    def get(self, request):
        business_id = request.user.business_id
        pending_requests = MemberJoinRequest.objects.filter(business=business_id , is_approved=False)
        serializer = MemberJoinRequestSerializer(pending_requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
    
    
class ApproveJoinRequestView(APIView):
    authentication_classes = [SSOBusinessTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Approve a specific join request by request_id.",
        manual_parameters=[
            openapi.Parameter(
                'request_id',
                openapi.IN_PATH,
                description="ID of the join request",
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={
            200: openapi.Response(description="Member approved and added."),
            404: openapi.Response(description="Join request not found.")
        }
    )
    def post(self, request, request_id):
        try:
            join_request = MemberJoinRequest.objects.get(id=request_id)

            # Approve and save the join request
            join_request.is_approved = True
            join_request.responded_at = timezone.now()
            join_request.save()

            return Response({"success": True, "message": "Member approved ", "card_number":join_request.card_number,"BizMbrIsActive": False,}, status=200)

        except MemberJoinRequest.DoesNotExist:
            return Response({"success": False, "error": "Join request not found."}, status=404)