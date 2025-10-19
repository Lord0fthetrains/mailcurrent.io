from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Plan, Subscription, BillingHistory
from .billing_serializers import (
    PlanSerializer, SubscriptionSerializer, BillingHistorySerializer,
    CreateSubscriptionSerializer, UpdateSubscriptionSerializer,
    CancelSubscriptionSerializer, PaymentMethodSerializer,
    CreatePaymentIntentSerializer
)
from .stripe_service import StripeService
import logging

logger = logging.getLogger('api')


class PlanListView(generics.ListAPIView):
    """List all available pricing plans"""
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated]


class SubscriptionDetailView(generics.RetrieveAPIView):
    """Get current user's subscription details"""
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user.subscription


class CreateSubscriptionView(generics.CreateAPIView):
    """Create a new subscription"""
    serializer_class = CreateSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            subscription = serializer.save()
            return Response({
                'success': True,
                'message': 'Subscription created successfully',
                'subscription': SubscriptionSerializer(subscription).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Failed to create subscription: {e}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class UpdateSubscriptionView(generics.UpdateAPIView):
    """Update current subscription"""
    serializer_class = UpdateSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user.subscription
    
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            subscription = serializer.update(self.get_object(), serializer.validated_data)
            return Response({
                'success': True,
                'message': 'Subscription updated successfully',
                'subscription': SubscriptionSerializer(subscription).data
            })
        except Exception as e:
            logger.error(f"Failed to update subscription: {e}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class CancelSubscriptionView(generics.UpdateAPIView):
    """Cancel current subscription"""
    serializer_class = CancelSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user.subscription
    
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            subscription = serializer.update(self.get_object(), serializer.validated_data)
            return Response({
                'success': True,
                'message': 'Subscription cancelled successfully',
                'subscription': SubscriptionSerializer(subscription).data
            })
        except Exception as e:
            logger.error(f"Failed to cancel subscription: {e}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class BillingHistoryListView(generics.ListAPIView):
    """List user's billing history"""
    serializer_class = BillingHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return BillingHistory.objects.filter(user=self.request.user).order_by('-billed_at')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_methods(request):
    """Get user's payment methods"""
    try:
        user = request.user
        if not user.subscription.stripe_customer_id:
            return Response({
                'success': False,
                'message': 'No payment methods found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        payment_methods = StripeService.get_customer_payment_methods(
            user.subscription.stripe_customer_id
        )
        
        serializer = PaymentMethodSerializer(payment_methods, many=True)
        return Response({
            'success': True,
            'payment_methods': serializer.data
        })
        
    except Exception as e:
        logger.error(f"Failed to get payment methods: {e}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_intent(request):
    """Create a payment intent for one-time payments"""
    serializer = CreatePaymentIntentSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    
    try:
        result = serializer.save()
        return Response({
            'success': True,
            'client_secret': result['client_secret'],
            'payment_intent_id': result['id']
        })
    except Exception as e:
        logger.error(f"Failed to create payment intent: {e}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_setup_intent(request):
    """Create a setup intent for saving payment methods"""
    try:
        user = request.user
        if not user.subscription.stripe_customer_id:
            # Create customer first
            StripeService.create_customer(user)
            user.subscription.refresh_from_db()
        
        intent = StripeService.create_setup_intent(user.subscription.stripe_customer_id)
        
        return Response({
            'success': True,
            'client_secret': intent.client_secret,
            'setup_intent_id': intent.id
        })
        
    except Exception as e:
        logger.error(f"Failed to create setup intent: {e}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def billing_portal(request):
    """Create Stripe billing portal session"""
    try:
        user = request.user
        if not user.subscription.stripe_customer_id:
            return Response({
                'success': False,
                'message': 'No billing information found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Create billing portal session
        session = stripe.billing_portal.Session.create(
            customer=user.subscription.stripe_customer_id,
            return_url=request.build_absolute_uri('/billing/')
        )
        
        return Response({
            'success': True,
            'url': session.url
        })
        
    except Exception as e:
        logger.error(f"Failed to create billing portal session: {e}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
