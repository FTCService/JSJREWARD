from django.db import models

# Create your models here.

class BusinessRewardRule(models.Model):
    REWARD_TYPE_CHOICES = [
    ('percentage', 'Percentage'),
    ('purchase_value_to_points', 'Purchase Value to Points'),
    ('flat', 'Flat')
    ]

    RewardRuleBizId = models.IntegerField(verbose_name="Business ID")
    
    RewardRuleType = models.CharField(
        max_length=30, choices=REWARD_TYPE_CHOICES, verbose_name="Reward Rule Type"
    )
    RewardRuleNotionalValue = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Notional Value"
    )
    
    RewardRuleValue = models.FloatField(verbose_name="Reward Rule Value", null=True, blank=True, default=1.0)  
    
    RewardRuleValidityPeriodYears = models.IntegerField(
        verbose_name="Validity Period (years)", null=True, blank=True
    )
    RewardRuleMilestone = models.IntegerField(
        verbose_name="Milestone (Points)", null=True, blank=True
    )

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
    
    def calculate_points(self):
        """Auto-calculate transaction points based on business reward rules."""
        try:
            # Fetch the assigned reward rule for the card number
            business_member = BusinessMember.objects.filter(
                BizMbrCardNo=self.CrdTrnsCardNumber,
                BizMbrBizId=self.CrdTrnsBizId,
                BizMbrIsActive=True
            ).select_related("BizMbrRuleId").first()

            if not business_member:
                self.CrdTrnsPoint = 0
                return

            reward_rule = business_member.BizMbrRuleId  # Assigned reward rule
            
            if not reward_rule:
                self.CrdTrnsPoint = 0
                return
            
            # Extract rule values
            reward_notional_value = float(reward_rule.RewardRuleNotionalValue) if reward_rule.RewardRuleNotionalValue else 1.0  
            reward_value = float(reward_rule.RewardRuleValue) if reward_rule.RewardRuleValue is not None else 1.0  

            # Calculate points based on reward type
            if reward_rule.RewardRuleType == "percentage":
                self.CrdTrnsPoint = int((self.CrdTrnsPurchaseAmount * reward_value) / 100)
            elif reward_rule.RewardRuleType == "purchase_value_to_points":
                if reward_notional_value > 0:
                    self.CrdTrnsPoint = int((self.CrdTrnsPurchaseAmount * reward_value)/100 )
                else:
                    self.CrdTrnsPoint = 0
            elif reward_rule.RewardRuleType == "flat":
                self.CrdTrnsPoint = int(reward_value)  # Direct flat reward value
            else:
                self.CrdTrnsPoint = 0  # Default to 0 if no valid rule is found

        except Exception as e:
            print(f"Error calculating points: {e}")
            self.CrdTrnsPoint = 0


    def update_cumulative_points(self):
        cumulative_points, _ = CumulativePoints.objects.get_or_create(
            CmltvPntsMbrCardNo=self.CrdTrnsCardNumber,
            CmltvPntsBizId=self.CrdTrnsBizId
        )

        business_member = BusinessMember.objects.filter(
            BizMbrCardNo=self.CrdTrnsCardNumber,
            BizMbrBizId=self.CrdTrnsBizId,
            BizMbrIsActive=True
        ).select_related("BizMbrRuleId").first()

        if not business_member:
            raise ValueError("No active reward rule found for this member.")

        reward_rule = business_member.BizMbrRuleId

        if self.CrdTrnsTransactionType == "Points_Earned":
            cumulative_points.LifetimeEarnedPoints += self.CrdTrnsPoint
            cumulative_points.CurrentBalance += self.CrdTrnsPoint
            cumulative_points.TotalPurchaseAmount += self.CrdTrnsPurchaseAmount

        elif self.CrdTrnsTransactionType == "Points_Redeemed":
            milestone = reward_rule.RewardRuleMilestone if reward_rule and reward_rule.RewardRuleMilestone else 0
            required_points = milestone if milestone > 0 else self.CrdTrnsPoint

            if cumulative_points.CurrentBalance >= required_points:
                cumulative_points.LifetimeRedeemedPoints += required_points
                cumulative_points.CurrentBalance -= required_points
            else:
                raise ValueError("Insufficient points for redemption.")

        cumulative_points.save()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_cumulative_points()

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
    LifetimeEarnedPoints = models.FloatField(default=0.00)
    LifetimeRedeemedPoints = models.FloatField(default=0.00)
    CurrentBalance = models.FloatField(default=0.00)
    TotalPurchaseAmount = models.FloatField(default=0.00)
    LastUpdated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.CmltvPntsMbrCardNo} - {self.CmltvPntsBizId} - Balance: {self.CurrentBalance}"