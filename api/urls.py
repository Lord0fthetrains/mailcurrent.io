from django.urls import path
from . import views
from . import webhook_views
from . import analytics_views

app_name = 'api'

urlpatterns = [
    # Email sending endpoints
    path('send-template/', views.SendTemplateEmailView.as_view(), name='send-template'),
    path('send/', views.SendCustomEmailView.as_view(), name='send'),
    
    # Template management
    path('templates/', views.TemplatesListView.as_view(), name='templates'),
    
    # Email logs and stats
    path('logs/', views.EmailLogsView.as_view(), name='logs'),
    path('stats/', views.EmailStatsView.as_view(), name='stats'),
    
    # API key management
    path('validate/', views.ValidateAPIKeyView.as_view(), name='validate'),
    path('api-keys/', views.APIKeysListView.as_view(), name='api-keys'),
    path('api-keys/<int:pk>/', views.APIKeyDetailView.as_view(), name='api-key-detail'),
    
    # Webhook management
    path('webhooks/', webhook_views.WebhookEndpointListCreateView.as_view(), name='webhook-list'),
    path('webhooks/<int:pk>/', webhook_views.WebhookEndpointDetailView.as_view(), name='webhook-detail'),
    path('webhooks/<int:pk>/test/', webhook_views.test_webhook, name='webhook-test'),
    path('webhook-deliveries/', webhook_views.WebhookDeliveryListView.as_view(), name='webhook-deliveries'),
    path('email-events/', webhook_views.EmailEventListView.as_view(), name='email-events'),
    
    # Unsubscribe management
    path('unsubscribe/<int:email_log_id>/<str:token>/', webhook_views.unsubscribe_view, name='unsubscribe'),
    path('unsubscribe/', webhook_views.unsubscribe_email, name='unsubscribe-email'),
    path('unsubscribe-list/', webhook_views.unsubscribe_list, name='unsubscribe-list'),
    path('resubscribe/', webhook_views.resubscribe_email, name='resubscribe-email'),
    
    # Email tracking
    path('track/open/<int:email_log_id>/<str:pixel_id>/', webhook_views.email_tracking_pixel, name='track-open'),
    path('track/click/<int:email_log_id>/<str:link_id>/', webhook_views.link_click_tracking, name='track-click'),
    
    # Analytics
    path('analytics/stats/', analytics_views.email_stats, name='analytics-stats'),
    path('analytics/events/', analytics_views.recent_events, name='analytics-events'),
    path('analytics/recipients/', analytics_views.top_recipients, name='analytics-recipients'),
    path('analytics/hourly/', analytics_views.hourly_stats, name='analytics-hourly'),
    path('analytics/performance/<int:email_log_id>/', analytics_views.email_performance, name='analytics-performance'),
    path('analytics/dashboard/', analytics_views.dashboard_summary, name='analytics-dashboard'),
    path('analytics/delivery-status/', analytics_views.delivery_status, name='analytics-delivery-status'),
    path('analytics/engagement/', analytics_views.engagement_metrics, name='analytics-engagement'),
    path('analytics/export/', analytics_views.export_analytics, name='analytics-export'),
    
    # Health check
    path('health/', views.health_check, name='health'),
]
