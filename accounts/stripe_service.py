import stripe
from django.conf import settings
from django.utils import timezone
from .models import User, Plan, Subscription
import logging

logger = logging.getLogger('api')

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service class for handling Stripe operations"""
    
    @staticmethod
    def create_customer(user):
        """Create a Stripe customer for a user"""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}".strip(),
                metadata={
                    'user_id': user.id,
                    'company_name': user.company_name or '',
                }
            )
            
            # Update user's subscription with Stripe customer ID
            if hasattr(user, 'subscription'):
                user.subscription.stripe_customer_id = customer.id
                user.subscription.save(update_fields=['stripe_customer_id'])
            
            logger.info(f"Created Stripe customer {customer.id} for user {user.email}")
            return customer
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer for user {user.email}: {e}")
            raise
    
    @staticmethod
    def create_subscription(user, plan, billing_cycle='monthly'):
        """Create a Stripe subscription for a user"""
        try:
            # Get or create Stripe customer
            if not user.subscription.stripe_customer_id:
                StripeService.create_customer(user)
                user.subscription.refresh_from_db()
            
            # Get the appropriate price ID
            if billing_cycle == 'yearly':
                price_id = plan.stripe_price_id_yearly
            else:
                price_id = plan.stripe_price_id_monthly
            
            if not price_id:
                raise ValueError(f"No Stripe price ID found for plan {plan.name} ({billing_cycle})")
            
            # Create subscription
            subscription = stripe.Subscription.create(
                customer=user.subscription.stripe_customer_id,
                items=[{
                    'price': price_id,
                }],
                payment_behavior='default_incomplete',
                payment_settings={'save_default_payment_method': 'on_subscription'},
                expand=['latest_invoice.payment_intent'],
                metadata={
                    'user_id': user.id,
                    'plan_id': plan.id,
                    'billing_cycle': billing_cycle,
                }
            )
            
            # Update local subscription
            user.subscription.stripe_subscription_id = subscription.id
            user.subscription.stripe_price_id = price_id
            user.subscription.plan = plan
            user.subscription.billing_cycle = billing_cycle
            user.subscription.status = subscription.status
            user.subscription.current_period_start = timezone.datetime.fromtimestamp(
                subscription.current_period_start, tz=timezone.utc
            )
            user.subscription.current_period_end = timezone.datetime.fromtimestamp(
                subscription.current_period_end, tz=timezone.utc
            )
            user.subscription.save()
            
            logger.info(f"Created Stripe subscription {subscription.id} for user {user.email}")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe subscription for user {user.email}: {e}")
            raise
    
    @staticmethod
    def cancel_subscription(subscription_id):
        """Cancel a Stripe subscription"""
        try:
            subscription = stripe.Subscription.delete(subscription_id)
            
            # Update local subscription
            local_subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
            local_subscription.status = 'canceled'
            local_subscription.save(update_fields=['status'])
            
            logger.info(f"Cancelled Stripe subscription {subscription_id}")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel Stripe subscription {subscription_id}: {e}")
            raise
    
    @staticmethod
    def update_subscription(subscription_id, new_plan, billing_cycle='monthly'):
        """Update a Stripe subscription to a new plan"""
        try:
            # Get the appropriate price ID
            if billing_cycle == 'yearly':
                price_id = new_plan.stripe_price_id_yearly
            else:
                price_id = new_plan.stripe_price_id_monthly
            
            if not price_id:
                raise ValueError(f"No Stripe price ID found for plan {new_plan.name} ({billing_cycle})")
            
            # Update subscription
            subscription = stripe.Subscription.modify(
                subscription_id,
                items=[{
                    'id': subscription_id,
                    'price': price_id,
                }],
                proration_behavior='create_prorations',
                metadata={
                    'plan_id': new_plan.id,
                    'billing_cycle': billing_cycle,
                }
            )
            
            # Update local subscription
            local_subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
            local_subscription.plan = new_plan
            local_subscription.billing_cycle = billing_cycle
            local_subscription.stripe_price_id = price_id
            local_subscription.save()
            
            logger.info(f"Updated Stripe subscription {subscription_id} to plan {new_plan.name}")
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update Stripe subscription {subscription_id}: {e}")
            raise
    
    @staticmethod
    def create_payment_intent(amount, currency='usd', customer_id=None):
        """Create a payment intent for one-time payments"""
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency,
                customer=customer_id,
                automatic_payment_methods={
                    'enabled': True,
                },
            )
            
            logger.info(f"Created payment intent {intent.id} for amount {amount}")
            return intent
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create payment intent: {e}")
            raise
    
    @staticmethod
    def get_customer_payment_methods(customer_id):
        """Get payment methods for a customer"""
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type='card',
            )
            
            return payment_methods.data
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get payment methods for customer {customer_id}: {e}")
            raise
    
    @staticmethod
    def create_setup_intent(customer_id):
        """Create a setup intent for saving payment methods"""
        try:
            intent = stripe.SetupIntent.create(
                customer=customer_id,
                payment_method_types=['card'],
            )
            
            logger.info(f"Created setup intent {intent.id} for customer {customer_id}")
            return intent
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create setup intent for customer {customer_id}: {e}")
            raise
