from rest_framework import serializers
from business.models import BusinessRewardRule, BusinessMember, CardTransaction, BusinessCardDesign,CumulativePoints
from django.core.validators import MinValueValidator, MaxValueValidator
import re
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import requests
from django.conf import settings
from .authentication import SSOBusinessTokenAuthentication


class BusinessMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessMember
        fields = [
            "BizMbrCardNo",
            "BizMbrRuleId",
            "BizMbrIsActive",
            "BizMbrIssueDate",
            "BizMbrValidityEnd",
            
        ]



class NewMemberSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    mobile_number = serializers.CharField(max_length=15)
   
    def validate_mobile_number(self, value):
        # Only digits, length exactly 10
        if not re.fullmatch(r"\d{10}", value):
            raise serializers.ValidationError("Mobile number must be exactly 10 digits.")
        return value


    
    
class BusinessRewardRuleSerializer(serializers.ModelSerializer):
    RewardRuleValidityPeriodYears = serializers.IntegerField(
        write_only=False,
        required=True,
        help_text="Validity Period in Years (Min: 1, Max: 100)",
        validators=[MinValueValidator(1), MaxValueValidator(100)]  # ✅ Enforce min 1 year, max 100 years
    )

    class Meta:
        model = BusinessRewardRule
        fields = "__all__"
        read_only_fields = ["RewardRuleBizId"]

    def create(self, validated_data):
        """Authenticate the user and assign `RewardRuleBizId` without needing business-specific data."""
        request = self.context.get("request")

        # Step 1: Authenticate the user using SSOBusinessTokenAuthentication
        user = self.authenticate_user(request)

        if not user:
            raise serializers.ValidationError({"success": False, "error": "Authentication failed."})

        # Step 2: Create Reward Rule (simplified, no business validation)
        return self.create_reward_rule(validated_data, user)

    def authenticate_user(self, request):
        """Authenticate the user based on token."""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Token "):
            raise AuthenticationFailed("Authorization token is missing or incorrect.")
        
        token_key = auth_header.split("Token ")[1]
        
        try:
            user, _ = SSOBusinessTokenAuthentication().authenticate(request)  # Unpack the tuple to get the user
            return user  # Return only the user object, not the entire tuple
        except AuthenticationFailed as e:
            raise serializers.ValidationError({"success": False, "error": str(e)})

    def create_reward_rule(self, validated_data, user):
        """Create a new reward rule for the authenticated user."""
        # Store validity period directly in years (no conversion to days)
        validity_years = validated_data.pop("RewardRuleValidityPeriodYears")
        validated_data["RewardRuleValidityPeriodYears"] = validity_years  # ✅ Store as years, not days

        # Check if the reward type already exists for the business (filter using RewardRuleBizId)
        reward_type = validated_data.get("RewardRuleType")
        if BusinessRewardRule.objects.filter(RewardRuleBizId=user.business_id, RewardRuleType=reward_type).exists():
            raise serializers.ValidationError({
                "success": False, 
                "error": f"A reward rule with type '{reward_type}' already exists. Please select another type."
            })
        
        # Assign count specific to the business
        existing_rules = BusinessRewardRule.objects.filter(RewardRuleBizId=user.business_id)
        validated_data["count"] = existing_rules.count() + 1

        validated_data["RewardRuleIsDefault"] = existing_rules.count() == 0
        # Assign `RewardRuleBizId` as the authenticated user's business ID
        validated_data["RewardRuleBizId"] = user.business_id

        return super().create(validated_data)

   


class CheckMemberActiveSerializer(serializers.ModelSerializer):
    # BizMbrCardNo = serializers.CharField(source="BizMbrCardNo.mbrcardno")  # Get card number from related Member model

    class Meta:
        model = BusinessMember
        fields = ["BizMbrCardNo",'BizMbrBizId', "BizMbrIsActive"]



    
class BusinessMemberSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="BizMbrCardNo.mbrfullname", read_only=True)
    mobile_number = serializers.CharField(source="BizMbrCardNo.mbrmobile", read_only=True)

    class Meta:
        model = BusinessMember
        extra_kwargs = {
            "BizMbrBizId": {"required": False, "allow_null": True}
        }
        fields = [ 
                 
            "BizMbrBizId",
            "BizMbrCardNo",
            "BizMbrRuleId",
            "BizMbrIssueDate",
            "BizMbrValidityEnd",
            "BizMbrIsActive",
            "full_name",
            "mobile_number"
        ]
        

    # def validate_BizMbrValidityEnd(self, value):
    #     """Ensure the validity end date is in the future."""
    #     from datetime import datetime
    #     if value and value < datetime.now():
    #         raise serializers.ValidationError("Validity end date must be in the future.")
    #     return value
    



class SpecificCardTransactionSerializer(serializers.Serializer):
    card_number = serializers.CharField(required=True)
    # transaction_type = serializers.ChoiceField(choices=["debit", "credit"], required=False)


class FetchMemberDetailsSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15, required=False)  # Now optional
    mbrcardno = serializers.CharField(max_length=20, required=False)  # Assuming max length is 20

    def validate(self, data):
        if not data.get("mobile_number") and not data.get("mbrcardno"):
            raise serializers.ValidationError("Either mobile_number or mbrcardno is required.")
        return data

class CardTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardTransaction
        fields = "__all__"

    def create(self, validated_data):
        request = self.context.get("request")  # Get request from context
        
    
        business_instance = request.user.business_id
        

        validated_data["CrdTrnsBizId"] = business_instance  # Assign business instance

        transaction = CardTransaction(**validated_data)
        transaction.calculate_points()  # Auto-calculate points
        transaction.save()
        return transaction


 

class RedeemPointsSerializer(serializers.Serializer):
    card_number = serializers.CharField(write_only=True)
    business_id = serializers.IntegerField(write_only=True)

    def validate(self, data):
        """Check if the user has enough points to redeem a fixed milestone value."""
        card_number = data["card_number"]
        business_id = data["business_id"]
      
        return data


   





class BusinessCardDesignSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessCardDesign
        fields = '__all__' 
        
        
class MemberByCardSerializer(serializers.Serializer):
    mbrcardno = serializers.CharField()
   
        

