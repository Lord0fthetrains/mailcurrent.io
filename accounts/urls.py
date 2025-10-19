from django.urls import path
from . import views
from .billing_views import (
    CreateSubscriptionView, UpdateSubscriptionView, CancelSubscriptionView,
    payment_methods, create_payment_intent, create_setup_intent, billing_portal
)
from .webhooks import stripe_webhook
from .verification_views import (
    send_verification_email, verify_email, verify_email_page,
    request_password_reset, reset_password, reset_password_page
)

urlpatterns = [
    # Authentication
    path('register/', views.UserRegistrationView.as_view(), name='user-register'),
    path('login/', views.UserLoginView.as_view(), name='user-login'),
    path('logout/', views.UserLogoutView.as_view(), name='user-logout'),
    
    # User Profile
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    
    # Plans and Subscriptions
    path('plans/', views.PlanListView.as_view(), name='plan-list'),
    path('subscription/', views.SubscriptionView.as_view(), name='subscription'),
    
    # Usage and Billing
    path('usage/', views.UsageLogView.as_view(), name='usage-logs'),
    path('billing/', views.BillingHistoryView.as_view(), name='billing-history'),
    
    # Dashboard
    path('dashboard/', views.user_dashboard, name='user-dashboard'),
    
    # API Key Management
    path('api-keys/', views.api_keys, name='api-keys'),
    path('api-keys/<int:key_id>/update/', views.update_api_key, name='update-api-key'),
    path('api-keys/<int:key_id>/delete/', views.delete_api_key, name='delete-api-key'),
    
    # Billing and Payments
    path('subscription/create/', CreateSubscriptionView.as_view(), name='create-subscription'),
    path('subscription/update/', UpdateSubscriptionView.as_view(), name='update-subscription'),
    path('subscription/cancel/', CancelSubscriptionView.as_view(), name='cancel-subscription'),
    path('payment-methods/', payment_methods, name='payment-methods'),
    path('payment-intent/', create_payment_intent, name='create-payment-intent'),
    path('setup-intent/', create_setup_intent, name='create-setup-intent'),
    path('billing-portal/', billing_portal, name='billing-portal'),
    
    # Webhooks
    path('webhooks/stripe/', stripe_webhook, name='stripe-webhook'),
    
    # Email Verification
    path('send-verification/', send_verification_email, name='send-verification'),
    path('verify-email/<str:token>/', verify_email, name='verify-email'),
    path('verify-email-page/<str:token>/', verify_email_page, name='verify-email-page'),
    
    # Password Reset
    path('request-password-reset/', request_password_reset, name='request-password-reset'),
    path('reset-password/<str:token>/', reset_password, name='reset-password'),
    path('reset-password-page/<str:token>/', reset_password_page, name='reset-password-page'),
]
