from django.db import models

# Create your models here.

class BusinessRewardRule(models.Model):
    REWARD_TYPE_CHOICES = [
    ('percentage', 'Percentage'),
    ('purchase_value_to_points', 'Purchase Value to Points'),
    ('flat', 'Flat')
    ]
    # RewardRuleId = models.IntegerField(verbose_name="Rule ID")
    RewardRuleBizId = models.IntegerField(verbose_name="Business ID")
    
    RewardRuleType = models.CharField(
        max_length=30, choices=REWARD_TYPE_CHOICES, verbose_name="Reward Rule Type"
    )
    RewardRuleNotionalValue = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Notional Value"
    )
    
    RewardRuleValue = models.FloatField(verbose_name="Reward Rule Value", null=True, blank=True)  
    
    RewardRuleValidityPeriodYears = models.IntegerField(
        verbose_name="Validity Period (years)", null=True, blank=True
    )
    RewardRuleMilestone = models.IntegerField(
        verbose_name="Milestone (Points)", null=True, blank=True
    )

    RewardRuleIsDefault = models.BooleanField(default=False, verbose_name="Is Default Reward Rule")
    count = models.PositiveIntegerField(default=1, editable=False)
    
    CreatedAt = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    UpdatedAt = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    
        
    def __str__(self):
        return f"{self.RewardRuleBizId} - {self.RewardRuleType}"
    
    

class BusinessMember(models.Model):
    """
    Model to link Businesses with Members and Reward Rules.
    """
    BizMbrBizId = models.IntegerField(verbose_name="Business ID")
    BizMbrCardNo = models.BigIntegerField(verbose_name="Member Card Number")
    BizMbrRuleId = models.ForeignKey(BusinessRewardRule, on_delete=models.CASCADE, related_name="reward_rules", verbose_name="Reward Rule", db_column="BizMbrRuleId")
    BizMbrIsActive = models.BooleanField(default=False, verbose_name="Is Active")
    BizMbrIssueDate = models.DateTimeField(auto_now_add=True, verbose_name="Issue Date")
    BizMbrValidityEnd = models.DateTimeField(null=True, blank=True, verbose_name="Validity End Date")

    def __str__(self):
        return f"{self.BizMbrBizId} - {self.BizMbrCardNo} - {self.BizMbrRuleId.RewardRuleType}"

    class Meta:
        verbose_name = "Business Member"
        verbose_name_plural = "Business Members"
        
class MemberJoinRequest(models.Model):
    business = models.IntegerField(verbose_name="Business ID")
    card_number = models.BigIntegerField(verbose_name="Member Card Number")
    full_name = models.CharField(max_length=255, null=True, blank=True)
    mobile_number = models.CharField(max_length=15, null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    requested_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"JoinRequest: {self.card_number} to Business {self.business}"


class CardTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('Points_Earned', 'Points Earned'),
        ('Points_Redeemed', 'Points Redeemed'),
    ]

    CrdTrnsBizId = models.IntegerField(verbose_name="Business ID")
    CrdTrnsCardNumber = models.BigIntegerField(verbose_name="Card Number") 
    CrdTrnsPurchaseAmount = models.FloatField(verbose_name="Purchase Amount")
    CrdTrnsPoint = models.PositiveIntegerField(verbose_name="Transaction Points", null=True, blank=True)
    CrdTrnsTransactionType = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, verbose_name="Transaction Type")
    CrdTrnsTransactionDate = models.DateTimeField(auto_now_add=True, verbose_name="Transaction Date")
    

    def __str__(self):
        return f"Transaction {self.id}: {self.CrdTrnsTransactionType} - {self.CrdTrnsPurchaseAmount} points"

    class Meta:
        verbose_name = "Card Transaction"
        verbose_name_plural = "Card Transactions"
        


class BusinessCardDesign(models.Model):
    CardDsgBizId = models.IntegerField(verbose_name="Business ID", null=True, blank=True)
    CardDsgDesignTemplateId = models.CharField(max_length=255, null=True,blank=True)
    CardDsgAddLogo = models.TextField(null=True,blank=True)
    CardDsgBackgroundColor = models.CharField(max_length=20, default="#FFFFFF", null=True, blank=True)
    CardDsgCreationDate = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    CardDsgTextColor = models.CharField(max_length=20, default="#000000", null=True, blank=True)

    def __str__(self):
        return f"Business Card {self.id} - {self.CardDsgDesignTemplateId}"
    
    
    
class CumulativePoints(models.Model):
    CmltvPntsMbrCardNo = models.BigIntegerField(verbose_name="Member Card Number")  # Changed to BigIntegerField
    CmltvPntsBizId = models.IntegerField(verbose_name="Business ID")
    LifetimeEarnedPoints = models.FloatField()
    LifetimeRedeemedPoints = models.FloatField()
    CurrentBalance = models.FloatField()
    TotalPurchaseAmount = models.FloatField()
    LastUpdated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.CmltvPntsMbrCardNo} - {self.CmltvPntsBizId} - Balance: {self.CurrentBalance}"