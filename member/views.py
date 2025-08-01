from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .authentication import SSOMemberTokenAuthentication
from business.serializers import CardTransactionSerializer
from business.models import BusinessMember, BusinessCardDesign, CumulativePoints,CardTransaction, MemberJoinRequest
from .serializers import MemberBusinessSotreSerializer, CumulativePointsSerializer, SelfMemberActiveSerializer
from helpers.utils import get_business_details_by_id, get_member_details_by_card
from django.utils import timezone
from django.db.models import Q
from helpers.emails import send_template_email


class BusinessStoreListApi(APIView):
    """
    List all Business stores for the logged-in member along with card design details.
    """
    authentication_classes = [SSOMemberTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve a list of all Businesses associated with the logged-in member along with their card designs.",
        responses={
            200: "Success - Returns a list of businesses (empty if none found)",
            404: "Error - Member not found",
            500: "Error - Internal server error"
        }
    )
    def get(self, request):
        try:
            # Fetch the logged-in user's member record
            
            member = request.user.mbrcardno
            print(member,"member")
            if not member:
                return Response(
                    {"error": "Member not found for this user"}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            # Fetch all BusinessMember records where BizMbrCardNo matches the member
            business_memberships = BusinessMember.objects.filter(BizMbrCardNo=member)

            business_data = []

            for membership in business_memberships:
                business = membership.BizMbrBizId  # Business instance
                business_details =get_business_details_by_id(business)
                
                business_name=business_details.get("business_name")
               
                # Fetch card design for the business
                card_design = BusinessCardDesign.objects.filter(CardDsgBizId=business).first()
                
                cumulative_points = CumulativePoints.objects.filter(
                    CmltvPntsMbrCardNo=member, 
                    CmltvPntsBizId=business
                ).first()
                
                # Append business & card design details
                business_data.append({
                    "business_id": business,
                    "business_name": business_name,
                    "CardDsgDesignTemplateId": card_design.CardDsgDesignTemplateId if card_design else None,
                    "CardDsgAddLogo": card_design.CardDsgAddLogo if card_design else None,
                    "CardDsgBackgroundColor": card_design.CardDsgBackgroundColor if card_design else None,
                    "CardDsgTextColor": card_design.CardDsgTextColor if card_design else None,
                    "CardDsgCreationDate": card_design.CardDsgCreationDate if card_design else None,
                    "CurrentBalance": cumulative_points.CurrentBalance if cumulative_points else 0.00,
                    "fullname": request.user.full_name,  # Full name of the member
                    "cardno": request.user.mbrcardno  # Card number of the member
                })

            return Response(
                {
                    "success": True,
                    "message": "Business store list retrieved successfully.",
                    "businesses": business_data
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
            

class BusinessStoreDetailsApi(APIView):
    """
    List all Business stores for the logged-in member along with their card design,
    cumulative points, milestone progress, and real-time eligibility status.
    """
    authentication_classes = [SSOMemberTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve Business store details, card design, cumulative points, and milestone progress.",
        manual_parameters=[
            openapi.Parameter(
                'biz_id',
                openapi.IN_PATH,
                description="Business ID to fetch details",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Business store details with milestone progress",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "BizMbrBizId": openapi.Schema(type=openapi.TYPE_INTEGER, description="Business ID"),
                        "business_name": openapi.Schema(type=openapi.TYPE_STRING, description="Business Name"),
                        "CardDsgDesignTemplateId": openapi.Schema(type=openapi.TYPE_STRING, description="Card Design Template ID"),
                        "CardDsgAddLogo": openapi.Schema(type=openapi.TYPE_STRING, description="Business Logo URL"),
                        "CardDsgBackgroundColor": openapi.Schema(type=openapi.TYPE_STRING, description="Card Background Color"),
                        "CardDsgTextColor": openapi.Schema(type=openapi.TYPE_STRING, description="Card Text Color"),
                        "CardDsgCreationDate": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description="Card Creation Date"),
                        "LifetimeEarnedPoints": openapi.Schema(type=openapi.TYPE_NUMBER, description="Lifetime Earned Points"),
                        "LifetimeRedeemedPoints": openapi.Schema(type=openapi.TYPE_NUMBER, description="Lifetime Redeemed Points"),
                        "CurrentBalance": openapi.Schema(type=openapi.TYPE_NUMBER, description="Current Balance Points"),
                        "TotalPurchaseAmount": openapi.Schema(type=openapi.TYPE_NUMBER, description="Total Purchase Amount"),
                        "MbrCardNo": openapi.Schema(type=openapi.TYPE_STRING, description="Member Card Number"),
                        "FullName": openapi.Schema(type=openapi.TYPE_STRING, description="Full Name"),
                        "MilestoneValue": openapi.Schema(type=openapi.TYPE_NUMBER, description="Milestone Point Value"),
                        "AchievedMilestones": openapi.Schema(type=openapi.TYPE_INTEGER, description="How many times milestone achieved"),
                        "PointsToNextMilestone": openapi.Schema(type=openapi.TYPE_NUMBER, description="Points needed for next milestone"),
                        "IsEligible": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Is member eligible for redemption"),
                        "RewardInfo": openapi.Schema(type=openapi.TYPE_OBJECT, description="Reward Info", additional_properties=True),
                    }
                )
            ),
            400: "BizMbrBizId parameter is required",
            404: "Business not found or no cumulative points available"
        }
    )
    def get(self, request, biz_id):
        if not biz_id:
            return Response({"error": "BizMbrBizId parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        business = get_business_details_by_id(biz_id)
        if not business:
            return Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)

        business_name = business.get("business_name")

        # Card design
        card_design = BusinessCardDesign.objects.filter(CardDsgBizId=biz_id).first()

        # Points and member info
        cumulative_points = CumulativePoints.objects.filter(
            CmltvPntsMbrCardNo=request.user.mbrcardno,
            CmltvPntsBizId=biz_id
        ).first()

        mbr_card_no = request.user.mbrcardno
        full_name = request.user.full_name

        if cumulative_points:
            earned = cumulative_points.LifetimeEarnedPoints or 0
            current_balance = cumulative_points.CurrentBalance or 0
            redeemed = cumulative_points.LifetimeRedeemedPoints or 0
            total_purchase = cumulative_points.TotalPurchaseAmount or 0
        else:
            earned = current_balance = redeemed = total_purchase = 0

        # Milestone logic
        milestone_value = 0
        achieved_milestones = 0
        points_to_next_milestone = 0
        is_eligible = False
        reward_info = None

        biz_member = BusinessMember.objects.filter(
            BizMbrBizId=biz_id,
            BizMbrCardNo=request.user.mbrcardno,
            BizMbrIsActive=True
        ).select_related("BizMbrRuleId").first()

        if biz_member and biz_member.BizMbrRuleId:
            reward_rule = biz_member.BizMbrRuleId
            milestone_value = reward_rule.RewardRuleMilestone or 0

            if milestone_value > 0:
                achieved_milestones = earned // milestone_value
                points_to_next_milestone = milestone_value - (earned % milestone_value)
                is_eligible = current_balance >= milestone_value

            reward_info = {
                "RewardRuleId": reward_rule.id,
                "RewardRuleType": reward_rule.RewardRuleType,
                "RewardRuleNotionalValue": reward_rule.RewardRuleNotionalValue,
                "RewardRuleValue": reward_rule.RewardRuleValue
            }

        response_data = {
            "BizMbrBizId": biz_id,
            "business_name": business_name,
            "CardDsgDesignTemplateId": card_design.CardDsgDesignTemplateId if card_design else None,
            "CardDsgAddLogo": card_design.CardDsgAddLogo if card_design else None,
            "CardDsgBackgroundColor": card_design.CardDsgBackgroundColor if card_design else None,
            "CardDsgTextColor": card_design.CardDsgTextColor if card_design else None,
            "CardDsgCreationDate": card_design.CardDsgCreationDate if card_design else None,
            "LifetimeEarnedPoints": earned,
            "LifetimeRedeemedPoints": redeemed,
            "CurrentBalance": current_balance,
            "TotalPurchaseAmount": total_purchase,
            "MbrCardNo": mbr_card_no,
            "FullName": full_name,
            "MilestoneValue": milestone_value,
            "AchievedMilestones": achieved_milestones,
            "PointsToNextMilestone": points_to_next_milestone if current_balance < milestone_value else 0,
            "IsEligible": is_eligible,
            "RewardInfo": reward_info
        }

        return Response(response_data, status=status.HTTP_200_OK)
    
    
    


class MemberTransactionHistoryApi(APIView):
    """
    Retrieve all transactions of a member for a specific business (BizMbrBizId),
    including cumulative points summary.
    """
    authentication_classes = [SSOMemberTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve all transactions for a member related to a specific business, along with cumulative points summary.",
        manual_parameters=[
            openapi.Parameter(
                'biz_id',
                openapi.IN_PATH,
                description="Business ID to fetch transactions and cumulative points",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                'transaction_type',
                openapi.IN_QUERY,
                description="Filter transactions by type (debit or credit)",
                type=openapi.TYPE_STRING,
                enum=['debit', 'credit'],
                required=False
            )
        ],
        responses={
            200: openapi.Response(
                description="Transactions and cumulative points retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Request success status"),
                        "transactions": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(type=openapi.TYPE_OBJECT),
                            description="List of transactions with type (debit or credit)"
                        ),
                        "cumulative_points": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "LifetimeEarnedPoints": openapi.Schema(type=openapi.TYPE_NUMBER, description="Total earned points"),
                                "LifetimeRedeemedPoints": openapi.Schema(type=openapi.TYPE_NUMBER, description="Total redeemed points"),
                                "CurrentBalance": openapi.Schema(type=openapi.TYPE_NUMBER, description="Current point balance"),
                                "TotalPurchaseAmount": openapi.Schema(type=openapi.TYPE_NUMBER, description="Total purchase amount"),
                                "LastUpdated": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, description="Last updated timestamp"),
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Bad request",
                examples={"application/json": {"success": False, "error": "BizMbrBizId parameter is required."}}
            ),
            404: openapi.Response(
                description="No transactions or cumulative points found",
                examples={"application/json": {"success": False, "message": "No transactions or cumulative points found for this business."}}
            ),
        }
    )
    def get(self, request, biz_id):
        """
        Retrieve all transactions of a member for a specific business,
        including cumulative points summary.
        """
        if not biz_id:
            return Response(
                {"success": False, "error": "BizMbrBizId parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure the business exists
        business = get_business_details_by_id(biz_id)
        business_id=business.get("business_id")
        if not business_id:
            return Response({"error": "Business not found"}, status=status.HTTP_404_NOT_FOUND)
            
        transaction_type = request.query_params.get('transaction_type', None)
        # print(transaction_type,"================================")

        # Retrieve all transactions related to the business for the logged-in member
        transactions = CardTransaction.objects.filter(
            CrdTrnsBizId=business_id,
            CrdTrnsCardNumber=request.user.mbrcardno  # Filtering transactions for the logged-in member
        )

        # Apply filter for transaction type if provided
        if transaction_type in ['Points_Redeemed', 'Points_Earned']:
            transactions = transactions.filter(CrdTrnsTransactionType=transaction_type)

        # Retrieve cumulative points for the logged-in member and business
        cumulative_points = CumulativePoints.objects.filter(
            CmltvPntsMbrCardNo=request.user.mbrcardno,
            CmltvPntsBizId=business_id
        ).first()

        transaction_data = CardTransactionSerializer(transactions, many=True).data if transactions.exists() else []
        cumulative_points_data = CumulativePointsSerializer(cumulative_points).data if cumulative_points else {}

        if not transactions.exists() and not cumulative_points:
            return Response(
                {"success": False, "message": "No transactions or cumulative points found for this business."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "success": True,
                "transactions": transaction_data,
                "cumulative_points": cumulative_points_data
            },
            status=status.HTTP_200_OK
        )
        
        
        


class TransactionDetailApi(APIView):
    """
    Retrieve details of a specific transaction for a given business.
    """
    authentication_classes = [SSOMemberTokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retrieve details of a specific transaction for a business.",
        responses={
            200: openapi.Response(
                description="Transaction details retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "transaction_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "biz_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "card_number": openapi.Schema(type=openapi.TYPE_STRING),
                        "amount": openapi.Schema(type=openapi.TYPE_NUMBER),
                        "transaction_type": openapi.Schema(type=openapi.TYPE_STRING),
                        "date": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                    }
                )
            ),
            404: openapi.Response(
                description="Transaction not found",
                examples={"application/json": {"error": "Transaction not found."}}
            )
        }
    )
    def get(self, request, biz_id, transaction_id):
        """
        Retrieve a specific transaction by ID for a business.
        """
        try:
            transaction = CardTransaction.objects.get(CrdTrnsBizId=biz_id, id=transaction_id)
        except CardTransaction.DoesNotExist:
            return Response({"error": "Transaction not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CardTransactionSerializer(transaction)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
class MemberQRScanAPIView(APIView):
    """
    API for member scanning a business QR code.
    - GET: Check if the member is active in the business.
    - POST: If not active, send a join request to the business.
    """
    authentication_classes = [SSOMemberTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Check if a member is already active in a business.
        """
        Biz_Id = request.query_params.get("Biz_Id")
        card_number = request.user.mbrcardno

        if not Biz_Id:
            return Response(
                {"success": False, "error": "Biz_Id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            Biz_Id = int(Biz_Id)
        except ValueError:
            return Response(
                {"success": False, "error": "Invalid Biz_Id format."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if member is already active
        business_member = BusinessMember.objects.filter(
            BizMbrCardNo=card_number,
            BizMbrBizId=Biz_Id
        ).first()

        if business_member:
            serializer = SelfMemberActiveSerializer(business_member)
            return Response({
                "success": True,
                "message": "Member is active in the business.",
                "BizMbrIsActive": True,
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "success": False,
                "message": "You're just a join request away from exclusive discounts and becoming a loyal customer.",
                "BizMbrIsActive": False
            }, status=status.HTTP_200_OK)

    def post(self, request):
        """
        If member is not active, create a join request to the business.
        """
        business_id = request.query_params.get("Biz_Id")
        card_number = request.user.mbrcardno

        if not business_id:
            return Response({"success": False, "error": "Biz_Id is required."}, status=400)
        
        try:
            business_id = int(business_id)
        except ValueError:
            return Response({"success": False, "error": "Invalid Biz_Id format."}, status=400)
        business = get_business_details_by_id(business_id)
        business_id=business.get("business_id")
        email=business.get("email")
        # Check if already active
        if BusinessMember.objects.filter(BizMbrCardNo=card_number, BizMbrBizId=business_id).exists():
            return Response({
                "success": True,
                "message": "Member is already active in this business.",
                "BizMbrIsActive": True
            }, status=status.HTTP_200_OK)

        # Optional: prevent duplicate join requests
        if MemberJoinRequest.objects.filter(card_number=card_number, business=business_id, is_approved=False).exists():
            return Response({
                "success": False,
                "message": "Join request already sent to this business.",
            }, status=status.HTTP_200_OK)

        # Get member details
        member_data = get_member_details_by_card(card_number)
        if not member_data:
            return Response({"success": False, "error": "Member not found."}, status=404)
        
        # Create join request
        MemberJoinRequest.objects.create(
            business=business_id,
            card_number=card_number,
            full_name=member_data.get("full_name"),
            mobile_number=member_data.get("mobile_number"),
            is_approved=False
        )
        
        context = {
            "full_name": member_data.get("full_name"),
            "mbrcardno": card_number,
            "Mobile_number": member_data.get("mobile_number"),
        }
        send_template_email(
            subject="New Join Request Received",
            template_name="email_template/send_request.html",
            context=context,
            recipient_list=[email] 
            )

        return Response({
            "success": True,
            "message": "Join request sent to business.",
            # "BizMbrIsActive": False,
            "card_number": card_number,
            "business_id": business_id
            
        }, status=201)



# class MemberActiveInnBusiness(APIView):
#     """
#     API to check if a member is active based on the provided business Id.
#     """
#     authentication_classes = [SSOMemberTokenAuthentication]
#     permission_classes = [IsAuthenticated]

#     @swagger_auto_schema(
#         operation_description="Check if a member is active based on the provided business Id.",
#         responses={200: SelfMemberActiveSerializer()}
#     )
#     def get(self, request):
#         """
#         Check if a member is active in a business using their card number.
#         """
#         Biz_Id = request.query_params.get("Biz_Id")
#         if not Biz_Id:
#             return Response(
#                 {"success": False, "error": "Business ID is required."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         try:
#             Biz_Id = int(Biz_Id)
#         except ValueError:
#             return Response(
#                 {"success": False, "error": "Invalid Business ID format."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         card_number = request.user.mbrcardno
#         print(f"Checking for card_number: {card_number} in Biz_Id: {Biz_Id}")

#         business_member = BusinessMember.objects.filter(
#             BizMbrCardNo=card_number,
#             BizMbrBizId=Biz_Id
#         ).first()

#         if not business_member:
#             return Response(
#                 {
#                     "success": False,
#                     "message": "Member is not active in this business. Please scan a valid business QR ",
#                     "BizMbrIsActive": False
#                 },
#                 status=status.HTTP_200_OK
#             )

#         serializer = SelfMemberActiveSerializer(business_member)
#         return Response(
#             {
#                 "success": True,
#                 "message": "Member is active in the business.",
#                 "data": serializer.data
#             },
#             status=status.HTTP_200_OK
#         )
