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
            data.append({
                "BizMbrBizId": member.BizMbrBizId.business_id,  
                "BizMbrCardNo": member.BizMbrCardNo.mbrcardno,  
                "BizMbrRuleId": member.BizMbrRuleId.id,  
                "BizMbrIssueDate": member.BizMbrIssueDate,  
                "BizMbrValidityEnd": member.BizMbrValidityEnd,
                "BizMbrIsActive": member.BizMbrIsActive,
                "full_name": member.BizMbrCardNo.full_name,  # Fetch member's full name
                "mobile_number": member.BizMbrCardNo.mobile_number  # Fetch member's mobile number
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
        """Retrieve all Card Transactions for the logged-in business."""
        transactions = CardTransaction.objects.filter(CrdTrnsBizId=request.user.business_id)
        serializer = CardTransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=CardTransactionSerializer)
    def post(self, request):
        """Create a new Card Transaction and auto-assign the Business ID."""
        serializer = CardTransactionSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            transaction = serializer.save()
            return Response(
                {
                    "success": True,
                    "message": "Transaction recorded successfully.",
                    "transaction_id": transaction.id,
                    "business_id": request.user.business_id,
                    "business_name": request.user.business_name,
                },
                status=status.HTTP_201_CREATED
            )

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
                status=status.HTTP_404_NOT_FOUND
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
        try:
            serializer.is_valid(raise_exception=True)
            transaction = serializer.save()
            return Response(
                {
                    "success": True,
                    "message": "Points redeemed successfully!",
                    "transaction_id": transaction.id
                },
                status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return Response(
                {
                    "success": False,
                    "message": e.detail.get("non_field_errors", ["Validation error"])[0]
                },
                status=status.HTTP_200_OK  # ⬅️ Custom 200 for validation error
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
        transactions = CardTransaction.objects.filter(CrdTrnsBizId__business_id=business_id)
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