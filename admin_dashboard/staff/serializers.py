from rest_framework import serializers
from business.models import  BusinessMember
from helpers.utils import get_member_details_by_card



class BusinessMemberClubSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    mobile_number = serializers.SerializerMethodField()

    class Meta:
        model = BusinessMember
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

    def get_full_name(self, obj):
        try:
            member_details = get_member_details_by_card(obj.BizMbrCardNo)
            return member_details.get("full_name")
        except Exception:
            return None

    def get_mobile_number(self, obj):
        try:
            member_details = get_member_details_by_card(obj.BizMbrCardNo)
            return member_details.get("mobile_number")
        except Exception:
            return None
