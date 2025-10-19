from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.HomeView.as_view(), name='home'),
    path('pricing/', views.PricingView.as_view(), name='pricing'),
    path('api-docs/', views.APIDocsView.as_view(), name='api_docs'),
    
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    
    # Dashboard (requires login)
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/api/', views.dashboard_api_view, name='dashboard_api'),
    path('dashboard/analytics/', views.dashboard_analytics_view, name='dashboard_analytics'),
    path('profile/', views.profile_view, name='profile'),
    path('billing/', views.billing_view, name='billing'),
    
    # API Key management (AJAX)
    path('api-keys/create/', views.create_api_key, name='create_api_key'),
    path('api-keys/<int:key_id>/delete/', views.delete_api_key, name='delete_api_key'),
    
    # Debug
    path('debug-session/', views.debug_session, name='debug_session'),
    
    # Legal Pages
    path('privacy/', views.PrivacyPolicyView.as_view(), name='privacy'),
    path('terms/', views.TermsOfServiceView.as_view(), name='terms'),
    path('cookies/', views.CookiePolicyView.as_view(), name='cookies'),
    
    # Company Pages
    path('about/', views.AboutUsView.as_view(), name='about'),
    path('security/', views.SecurityView.as_view(), name='security'),
    path('compliance/', views.ComplianceView.as_view(), name='compliance'),
    
    # Service Pages
    path('status/', views.StatusView.as_view(), name='status'),
    path('blog/', views.BlogView.as_view(), name='blog'),
    path('community/', views.CommunityView.as_view(), name='community'),
]
