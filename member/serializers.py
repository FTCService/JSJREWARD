from rest_framework import serializers
from business.models import  BusinessMember, CumulativePoints
from member import models



class MemberBusinessSotreSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessMember
        fields = "__all__"
        extra_kwargs = {
            "BizMbrBizId": {"required": False, "allow_null": True}
        }
        
        
 
class CumulativePointsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CumulativePoints
        fields = [
            "LifetimeEarnedPoints",
            "LifetimeRedeemedPoints",
            "CurrentBalance",
            "TotalPurchaseAmount",
            "LastUpdated"
        ]


