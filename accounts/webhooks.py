import stripe
import json
import logging
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import User, Subscription, BillingHistory
from .stripe_service import StripeService

logger = logging.getLogger('api')


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return HttpResponse(status=400)
    
    # Handle the event
    try:
        if event['type'] == 'customer.subscription.created':
            handle_subscription_created(event['data']['object'])
        elif event['type'] == 'customer.subscription.updated':
            handle_subscription_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            handle_subscription_deleted(event['data']['object'])
        elif event['type'] == 'invoice.payment_succeeded':
            handle_invoice_payment_succeeded(event['data']['object'])
        elif event['type'] == 'invoice.payment_failed':
            handle_invoice_payment_failed(event['data']['object'])
        elif event['type'] == 'customer.subscription.trial_will_end':
            handle_trial_will_end(event['data']['object'])
        else:
            logger.info(f"Unhandled event type: {event['type']}")
    
    except Exception as e:
        logger.error(f"Error handling webhook event {event['type']}: {e}")
        return HttpResponse(status=500)
    
    return HttpResponse(status=200)


def handle_subscription_created(subscription_data):
    """Handle subscription created event"""
    try:
        customer_id = subscription_data['customer']
        subscription_id = subscription_data['id']
        
        # Find user by Stripe customer ID
        user = User.objects.get(subscription__stripe_customer_id=customer_id)
        
        # Update subscription
        user.subscription.stripe_subscription_id = subscription_id
        user.subscription.status = subscription_data['status']
        user.subscription.current_period_start = timezone.datetime.fromtimestamp(
            subscription_data['current_period_start'], tz=timezone.utc
        )
        user.subscription.current_period_end = timezone.datetime.fromtimestamp(
            subscription_data['current_period_end'], tz=timezone.utc
        )
        user.subscription.save()
        
        logger.info(f"Updated subscription for user {user.email}: {subscription_id}")
        
    except User.DoesNotExist:
        logger.error(f"User not found for customer {customer_id}")
    except Exception as e:
        logger.error(f"Error handling subscription created: {e}")


def handle_subscription_updated(subscription_data):
    """Handle subscription updated event"""
    try:
        subscription_id = subscription_data['id']
        
        # Find subscription
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        
        # Update subscription
        subscription.status = subscription_data['status']
        subscription.current_period_start = timezone.datetime.fromtimestamp(
            subscription_data['current_period_start'], tz=timezone.utc
        )
        subscription.current_period_end = timezone.datetime.fromtimestamp(
            subscription_data['current_period_end'], tz=timezone.utc
        )
        subscription.save()
        
        logger.info(f"Updated subscription {subscription_id} status to {subscription_data['status']}")
        
    except Subscription.DoesNotExist:
        logger.error(f"Subscription not found: {subscription_id}")
    except Exception as e:
        logger.error(f"Error handling subscription updated: {e}")


def handle_subscription_deleted(subscription_data):
    """Handle subscription deleted event"""
    try:
        subscription_id = subscription_data['id']
        
        # Find subscription
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        
        # Update subscription
        subscription.status = 'canceled'
        subscription.save()
        
        logger.info(f"Cancelled subscription {subscription_id}")
        
    except Subscription.DoesNotExist:
        logger.error(f"Subscription not found: {subscription_id}")
    except Exception as e:
        logger.error(f"Error handling subscription deleted: {e}")


def handle_invoice_payment_succeeded(invoice_data):
    """Handle successful invoice payment"""
    try:
        customer_id = invoice_data['customer']
        subscription_id = invoice_data.get('subscription')
        
        # Find user
        user = User.objects.get(subscription__stripe_customer_id=customer_id)
        
        # Create billing history record
        BillingHistory.objects.create(
            user=user,
            subscription=user.subscription,
            invoice_id=invoice_data['id'],
            amount=invoice_data['amount_paid'] / 100,  # Convert from cents
            currency=invoice_data['currency'],
            status='paid',
            period_start=timezone.datetime.fromtimestamp(
                invoice_data['period_start'], tz=timezone.utc
            ),
            period_end=timezone.datetime.fromtimestamp(
                invoice_data['period_end'], tz=timezone.utc
            ),
        )
        
        # Reset usage counter
        user.subscription.emails_sent_this_period = 0
        user.subscription.save(update_fields=['emails_sent_this_period'])
        
        logger.info(f"Payment succeeded for user {user.email}: ${invoice_data['amount_paid']/100}")
        
    except User.DoesNotExist:
        logger.error(f"User not found for customer {customer_id}")
    except Exception as e:
        logger.error(f"Error handling invoice payment succeeded: {e}")


def handle_invoice_payment_failed(invoice_data):
    """Handle failed invoice payment"""
    try:
        customer_id = invoice_data['customer']
        
        # Find user
        user = User.objects.get(subscription__stripe_customer_id=customer_id)
        
        # Update subscription status
        user.subscription.status = 'past_due'
        user.subscription.save(update_fields=['status'])
        
        # Create billing history record
        BillingHistory.objects.create(
            user=user,
            subscription=user.subscription,
            invoice_id=invoice_data['id'],
            amount=invoice_data['amount_due'] / 100,  # Convert from cents
            currency=invoice_data['currency'],
            status='failed',
            period_start=timezone.datetime.fromtimestamp(
                invoice_data['period_start'], tz=timezone.utc
            ),
            period_end=timezone.datetime.fromtimestamp(
                invoice_data['period_end'], tz=timezone.utc
            ),
        )
        
        logger.warning(f"Payment failed for user {user.email}: ${invoice_data['amount_due']/100}")
        
    except User.DoesNotExist:
        logger.error(f"User not found for customer {customer_id}")
    except Exception as e:
        logger.error(f"Error handling invoice payment failed: {e}")


def handle_trial_will_end(subscription_data):
    """Handle trial will end event"""
    try:
        subscription_id = subscription_data['id']
        
        # Find subscription
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        
        # Send notification email (implement as needed)
        logger.info(f"Trial will end for user {subscription.user.email}")
        
    except Subscription.DoesNotExist:
        logger.error(f"Subscription not found: {subscription_id}")
    except Exception as e:
        logger.error(f"Error handling trial will end: {e}")
