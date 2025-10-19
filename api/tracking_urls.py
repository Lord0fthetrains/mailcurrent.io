"""
Public tracking URLs - no authentication required
These endpoints are used for email tracking and should be publicly accessible
"""
from django.urls import path
from . import webhook_views

urlpatterns = [
    # Email tracking endpoints (public)
    path('open/<int:email_log_id>/<str:pixel_id>/', webhook_views.email_tracking_pixel, name='track-open'),
    path('click/<int:email_log_id>/<str:link_id>/', webhook_views.link_click_tracking, name='track-click'),
]
