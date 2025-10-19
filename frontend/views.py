from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate
from accounts.models import Plan, Subscription
from api.models import APIKey
import requests
import json


class HomeView(TemplateView):
    template_name = 'home.html'


class PricingView(TemplateView):
    template_name = 'pricing.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plans'] = Plan.objects.filter(is_active=True).order_by('price_monthly')
        return context


class APIDocsView(TemplateView):
    template_name = 'api_docs.html'


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        # Get form data
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        company_name = request.POST.get('company_name')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Validate passwords match
        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'auth/register.html')
        
        # Create user via API
        api_url = f"{request.scheme}://{request.get_host()}/api/v1/accounts/register/"
        data = {
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'company_name': company_name,
            'password': password,
            'password_confirm': password_confirm
        }
        
        try:
            response = requests.post(api_url, json=data)
            if response.status_code == 201:
                result = response.json()
                if result.get('success'):
                    # Log the user in
                    user = authenticate(request, username=email, password=password)
                    if user:
                        login(request, user)
                        messages.success(request, 'Account created successfully! Welcome to MailCurrent.io.')
                        return redirect('dashboard')
                    else:
                        messages.error(request, 'Account created but login failed. Please try logging in.')
                        return redirect('login')
                else:
                    messages.error(request, result.get('message', 'Registration failed.'))
            else:
                error_data = response.json()
                messages.error(request, f"Registration failed: {error_data}")
        except Exception as e:
            messages.error(request, f"Registration failed: {str(e)}")
    
    return render(request, 'auth/register.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Try to authenticate via API
        api_url = f"{request.scheme}://{request.get_host()}/api/v1/accounts/login/"
        data = {
            'email': email,
            'password': password
        }
        
        try:
            response = requests.post(api_url, json=data)
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    # Get the user from the API response
                    user_data = result.get('user', {})
                    user_id = user_data.get('id')
                    
                    if user_id:
                        # Get the user from database
                        from accounts.models import User
                        try:
                            user = User.objects.get(id=user_id)
                            
                            # Ensure user is active
                            if not user.is_active:
                                messages.error(request, 'Account suspended. Your account has been deactivated. Please contact support for assistance.')
                                return render(request, 'auth/login.html')
                            
                            # Set the backend attribute on the user
                            user.backend = 'django.contrib.auth.backends.ModelBackend'
                            
                            # Login the user
                            login(request, user)
                            
                            # Ensure session is saved
                            request.session.save()
                            
                            messages.success(request, 'Welcome back!')
                            return redirect('dashboard')
                        except User.DoesNotExist:
                            messages.error(request, 'User not found. Please try again.')
                    else:
                        messages.error(request, 'Invalid user data received.')
                else:
                    messages.error(request, result.get('message', 'Login failed.'))
            else:
                try:
                    error_data = response.json()
                    if 'non_field_errors' in error_data:
                        messages.error(request, error_data['non_field_errors'][0])
                    else:
                        messages.error(request, f"Login failed: {error_data}")
                except ValueError:
                    # Response is not valid JSON
                    messages.error(request, f"Login failed: {response.text}")
        except requests.exceptions.RequestException as e:
            messages.error(request, f"Login failed: Unable to connect to server")
        except Exception as e:
            messages.error(request, f"Login failed: {str(e)}")
    
    return render(request, 'auth/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


def debug_session(request):
    """Debug view to check session state"""
    # Force session creation
    if not request.session.session_key:
        request.session.create()
    
    return JsonResponse({
        'user_authenticated': request.user.is_authenticated,
        'user_id': request.user.id if request.user.is_authenticated else None,
        'session_key': request.session.session_key,
        'session_data': dict(request.session),
        'cookies': dict(request.COOKIES)
    })


def forgot_password_view(request):
    """Forgot password page"""
    return render(request, 'auth/forgot_password.html')


@login_required
def dashboard_view(request):
    # Get user dashboard data from API
    api_url = f"{request.scheme}://{request.get_host()}/api/v1/accounts/dashboard/"
    
    # Get user's token
    token = None
    if hasattr(request.user, 'auth_token'):
        token = request.user.auth_token.key
    
    if not token:
        messages.error(request, 'No authentication token found. Please log in again.')
        return redirect('login')
    
    headers = {'Authorization': f'Token {token}'}
    
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            dashboard_data = response.json()
            return render(request, 'dashboard/dashboard.html', dashboard_data)
        else:
            messages.error(request, 'Failed to load dashboard data.')
            return render(request, 'dashboard/dashboard.html', {})
    except Exception as e:
        messages.error(request, f"Failed to load dashboard: {str(e)}")
        return render(request, 'dashboard/dashboard.html', {})


@login_required
def profile_view(request):
    # Get user's token for API calls
    token = None
    if hasattr(request.user, 'auth_token'):
        token = request.user.auth_token.key
    
    context = {
        'auth_token': token
    }
    return render(request, 'dashboard/profile.html', context)


@login_required
def billing_view(request):
    # Get user's subscription data
    api_url = f"{request.scheme}://{request.get_host()}/api/v1/accounts/subscription/"
    
    # Get user's token
    token = None
    if hasattr(request.user, 'auth_token'):
        token = request.user.auth_token.key
    
    if not token:
        messages.error(request, 'No authentication token found. Please log in again.')
        return redirect('login')
    
    headers = {'Authorization': f'Token {token}'}
    
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            subscription_data = response.json()
            return render(request, 'dashboard/billing.html', subscription_data)
        else:
            messages.error(request, 'Failed to load subscription data.')
            return render(request, 'dashboard/billing.html', {})
    except Exception as e:
        messages.error(request, f"Failed to load billing data: {str(e)}")
        return render(request, 'dashboard/billing.html', {})


@login_required
def dashboard_api_view(request):
    """Dashboard API tab with Interactive API Explorer"""
    # Get user's token for API calls
    token = None
    if hasattr(request.user, 'auth_token'):
        token = request.user.auth_token.key
    
    context = {
        'auth_token': token
    }
    return render(request, 'dashboard/api.html', context)


@login_required
def dashboard_analytics_view(request):
    """Dashboard Analytics tab with comprehensive email tracking"""
    from api.analytics_service import AnalyticsService
    import json
    
    # Get analytics data directly
    days = int(request.GET.get('days', 30))
    stats = AnalyticsService.get_email_stats(request.user, days)
    recent_events = AnalyticsService.get_recent_events(request.user, 20)
    top_recipients = AnalyticsService.get_top_recipients(request.user, 10)
    
    context = {
        'user': request.user,
        'analytics_data': json.dumps({
            'stats': stats,
            'recent_events': recent_events,
            'top_recipients': top_recipients,
            'days': days
        }),
        'current_period': days
    }
    return render(request, 'dashboard/analytics.html', context)


@login_required
@require_http_methods(["POST"])
def create_api_key(request):
    """Create a new API key via AJAX"""
    name = request.POST.get('name')
    if not name:
        return JsonResponse({'success': False, 'message': 'API key name is required'})
    
    # Get user's token
    token = None
    if hasattr(request.user, 'auth_token'):
        token = request.user.auth_token.key
    
    if not token:
        return JsonResponse({'success': False, 'message': 'No authentication token found'})
    
    api_url = f"{request.scheme}://{request.get_host()}/api/v1/accounts/api-keys/"
    headers = {'Authorization': f'Token {token}'}
    data = {'name': name}
    
    try:
        response = requests.post(api_url, json=data, headers=headers)
        if response.status_code == 201:
            result = response.json()
            return JsonResponse(result)
        else:
            error_data = response.json()
            return JsonResponse({'success': False, 'message': error_data.get('message', 'Failed to create API key')})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@require_http_methods(["POST"])
def delete_api_key(request, key_id):
    """Delete an API key via AJAX"""
    # Get user's token
    token = None
    if hasattr(request.user, 'auth_token'):
        token = request.user.auth_token.key
    
    if not token:
        return JsonResponse({'success': False, 'message': 'No authentication token found'})
    
    api_url = f"{request.scheme}://{request.get_host()}/api/v1/accounts/api-keys/{key_id}/delete/"
    headers = {'Authorization': f'Token {token}'}
    
    try:
        response = requests.delete(api_url, headers=headers)
        if response.status_code == 200:
            result = response.json()
            return JsonResponse(result)
        else:
            error_data = response.json()
            return JsonResponse({'success': False, 'message': error_data.get('message', 'Failed to delete API key')})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# Legal and Company Pages
class PrivacyPolicyView(TemplateView):
    template_name = 'legal/privacy.html'


class TermsOfServiceView(TemplateView):
    template_name = 'legal/terms.html'


class CookiePolicyView(TemplateView):
    template_name = 'legal/cookies.html'


class AboutUsView(TemplateView):
    template_name = 'company/about.html'


class SecurityView(TemplateView):
    template_name = 'company/security.html'


class ComplianceView(TemplateView):
    template_name = 'company/compliance.html'




class StatusView(TemplateView):
    template_name = 'service/status.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Import here to avoid circular imports
        from api.status_service import StatusService
        
        # Get real status data
        status_data = StatusService.get_current_status()
        metrics_data = StatusService.get_performance_metrics()
        
        context.update({
            'status_data': status_data,
            'metrics_data': metrics_data,
        })
        
        return context


class BlogView(TemplateView):
    template_name = 'service/blog.html'


class CommunityView(TemplateView):
    template_name = 'service/community.html'
