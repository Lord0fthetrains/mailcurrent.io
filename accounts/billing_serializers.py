from rest_framework import serializers
from .models import Plan, Subscription, BillingHistory
from .stripe_service import StripeService


class PlanSerializer(serializers.ModelSerializer):
    """Serializer for pricing plans"""
    
    class Meta:
        model = Plan
        fields = [
            'id', 'name', 'description', 'price_monthly', 'price_yearly',
            'emails_per_month', 'api_keys_limit', 'custom_templates',
            'attachments', 'webhooks', 'analytics', 'priority_support',
            'stripe_price_id_monthly', 'stripe_price_id_yearly'
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for user subscriptions"""
    plan = PlanSerializer(read_only=True)
    plan_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'plan', 'plan_id', 'status', 'billing_cycle',
            'current_period_start', 'current_period_end', 'trial_end',
            'emails_sent_this_period', 'stripe_customer_id',
            'stripe_subscription_id', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'current_period_start', 'current_period_end',
            'trial_end', 'emails_sent_this_period', 'stripe_customer_id',
            'stripe_subscription_id', 'created_at', 'updated_at'
        ]


class BillingHistorySerializer(serializers.ModelSerializer):
    """Serializer for billing history"""
    
    class Meta:
        model = BillingHistory
        fields = [
            'id', 'invoice_id', 'amount', 'currency', 'status',
            'billed_at', 'period_start', 'period_end'
        ]


class CreateSubscriptionSerializer(serializers.Serializer):
    """Serializer for creating a new subscription"""
    plan_id = serializers.IntegerField()
    billing_cycle = serializers.ChoiceField(choices=['monthly', 'yearly'])
    
    def validate_plan_id(self, value):
        try:
            plan = Plan.objects.get(id=value, is_active=True)
            return value
        except Plan.DoesNotExist:
            raise serializers.ValidationError("Invalid plan ID")
    
    def create(self, validated_data):
        user = self.context['request'].user
        plan = Plan.objects.get(id=validated_data['plan_id'])
        billing_cycle = validated_data['billing_cycle']
        
        # Create Stripe subscription
        subscription = StripeService.create_subscription(user, plan, billing_cycle)
        
        return user.subscription


class UpdateSubscriptionSerializer(serializers.Serializer):
    """Serializer for updating a subscription"""
    plan_id = serializers.IntegerField()
    billing_cycle = serializers.ChoiceField(choices=['monthly', 'yearly'])
    
    def validate_plan_id(self, value):
        try:
            plan = Plan.objects.get(id=value, is_active=True)
            return value
        except Plan.DoesNotExist:
            raise serializers.ValidationError("Invalid plan ID")
    
    def update(self, instance, validated_data):
        plan = Plan.objects.get(id=validated_data['plan_id'])
        billing_cycle = validated_data['billing_cycle']
        
        # Update Stripe subscription
        StripeService.update_subscription(
            instance.stripe_subscription_id, plan, billing_cycle
        )
        
        return instance


class CancelSubscriptionSerializer(serializers.Serializer):
    """Serializer for canceling a subscription"""
    reason = serializers.CharField(required=False, allow_blank=True)
    
    def update(self, instance, validated_data):
        # Cancel Stripe subscription
        StripeService.cancel_subscription(instance.stripe_subscription_id)
        
        return instance


class PaymentMethodSerializer(serializers.Serializer):
    """Serializer for payment methods"""
    id = serializers.CharField()
    type = serializers.CharField()
    card = serializers.DictField()
    created = serializers.IntegerField()


class CreatePaymentIntentSerializer(serializers.Serializer):
    """Serializer for creating payment intents"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(default='usd')
    
    def create(self, validated_data):
        user = self.context['request'].user
        amount = validated_data['amount']
        currency = validated_data['currency']
        
        # Create payment intent
        intent = StripeService.create_payment_intent(
            amount, currency, user.subscription.stripe_customer_id
        )
        
        return {
            'client_secret': intent.client_secret,
            'id': intent.id
        }
