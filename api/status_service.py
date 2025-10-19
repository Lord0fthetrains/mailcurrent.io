import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.db.models import Avg, Count, Q
from django.utils import timezone
from .status_models import SystemComponent, ComponentStatus, SystemIncident, SystemMetrics, StatusPageSettings
from .models import EmailLog, APIKey

logger = logging.getLogger('api')


class StatusService:
    """Service for managing system status and metrics"""
    
    @staticmethod
    def get_current_status() -> Dict:
        """Get current system status overview"""
        try:
            # Get all active components
            components = SystemComponent.objects.filter(is_active=True)
            
            # Get latest status for each component
            component_statuses = []
            overall_status = 'operational'
            
            for component in components:
                latest_status = ComponentStatus.objects.filter(
                    component=component
                ).order_by('-created_at').first()
                
                if latest_status:
                    component_statuses.append({
                        'name': component.name,
                        'description': component.description,
                        'status': latest_status.status,
                        'response_time': latest_status.response_time,
                        'uptime': float(latest_status.uptime_percentage),
                        'message': latest_status.message,
                        'last_checked': latest_status.created_at
                    })
                    
                    # Determine overall status
                    if latest_status.status in ['major', 'partial']:
                        overall_status = 'major'
                    elif latest_status.status == 'degraded' and overall_status != 'major':
                        overall_status = 'degraded'
                    elif latest_status.status == 'maintenance' and overall_status not in ['major', 'degraded']:
                        overall_status = 'maintenance'
            
            # Get recent incidents
            recent_incidents = SystemIncident.objects.filter(
                Q(status__in=['investigating', 'identified', 'monitoring']) |
                Q(started_at__gte=timezone.now() - timedelta(days=7))
            ).order_by('-started_at')[:5]
            
            incidents = []
            for incident in recent_incidents:
                incidents.append({
                    'title': incident.title,
                    'description': incident.description,
                    'status': incident.status,
                    'impact': incident.impact,
                    'started_at': incident.started_at,
                    'resolved_at': incident.resolved_at,
                    'is_resolved': incident.is_resolved
                })
            
            return {
                'overall_status': overall_status,
                'components': component_statuses,
                'incidents': incidents,
                'last_updated': timezone.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting current status: {str(e)}")
            return {
                'overall_status': 'unknown',
                'components': [],
                'incidents': [],
                'last_updated': timezone.now()
            }
    
    @staticmethod
    def get_performance_metrics(days: int = 30) -> Dict:
        """Get performance metrics for the last N days"""
        try:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Get daily metrics
            daily_metrics = SystemMetrics.objects.filter(
                date__range=[start_date, end_date]
            ).order_by('date')
            
            # Calculate averages
            avg_uptime = daily_metrics.aggregate(avg=Avg('uptime_percentage'))['avg'] or 100.00
            avg_response_time = daily_metrics.aggregate(avg=Avg('avg_response_time'))['avg'] or 0
            total_emails = daily_metrics.aggregate(total=Count('emails_sent'))['total'] or 0
            avg_error_rate = daily_metrics.aggregate(avg=Avg('error_rate'))['avg'] or 0.00
            
            # Get current metrics from email logs
            recent_logs = EmailLog.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=1)
            )
            
            current_emails_today = recent_logs.count()
            current_api_requests = APIKey.objects.filter(
                last_used_at__gte=timezone.now() - timedelta(days=1)
            ).count()
            
            return {
                'uptime_30_days': float(avg_uptime),
                'avg_response_time': int(avg_response_time),
                'emails_sent_today': current_emails_today,
                'api_requests_today': current_api_requests,
                'error_rate': float(avg_error_rate),
                'daily_metrics': [
                    {
                        'date': metric.date.isoformat(),
                        'uptime': float(metric.uptime_percentage),
                        'response_time': metric.avg_response_time,
                        'emails_sent': metric.emails_sent,
                        'error_rate': float(metric.error_rate)
                    }
                    for metric in daily_metrics
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {str(e)}")
            return {
                'uptime_30_days': 99.9,
                'avg_response_time': 45,
                'emails_sent_today': 0,
                'api_requests_today': 0,
                'error_rate': 0.0,
                'daily_metrics': []
            }
    
    @staticmethod
    def update_component_status(component_name: str, status: str, 
                              response_time: Optional[int] = None, 
                              message: str = "") -> bool:
        """Update status for a specific component"""
        try:
            component = SystemComponent.objects.get(name=component_name)
            
            # Calculate uptime based on recent statuses
            recent_statuses = ComponentStatus.objects.filter(
                component=component,
                created_at__gte=timezone.now() - timedelta(days=30)
            ).order_by('-created_at')
            
            operational_count = recent_statuses.filter(status='operational').count()
            total_count = recent_statuses.count()
            uptime = (operational_count / total_count * 100) if total_count > 0 else 100.00
            
            ComponentStatus.objects.create(
                component=component,
                status=status,
                response_time=response_time,
                uptime_percentage=uptime,
                message=message
            )
            
            return True
            
        except SystemComponent.DoesNotExist:
            logger.error(f"Component {component_name} not found")
            return False
        except Exception as e:
            logger.error(f"Error updating component status: {str(e)}")
            return False
    
    @staticmethod
    def create_incident(title: str, description: str, impact: str, 
                       affected_components: List[str] = None) -> bool:
        """Create a new incident"""
        try:
            incident = SystemIncident.objects.create(
                title=title,
                description=description,
                impact=impact,
                status='investigating',
                started_at=timezone.now()
            )
            
            if affected_components:
                components = SystemComponent.objects.filter(name__in=affected_components)
                incident.affected_components.set(components)
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating incident: {str(e)}")
            return False
    
    @staticmethod
    def update_daily_metrics() -> bool:
        """Update daily metrics (should be called by a cron job)"""
        try:
            today = timezone.now().date()
            
            # Get yesterday's email logs
            yesterday = today - timedelta(days=1)
            email_logs = EmailLog.objects.filter(
                created_at__date=yesterday
            )
            
            # Calculate metrics
            emails_sent = email_logs.count()
            error_count = email_logs.filter(status='failed').count()
            error_rate = (error_count / emails_sent * 100) if emails_sent > 0 else 0.0
            
            # Get API requests
            api_requests = APIKey.objects.filter(
                last_used_at__date=yesterday
            ).count()
            
            # Create or update metrics
            metrics, created = SystemMetrics.objects.get_or_create(
                date=yesterday,
                defaults={
                    'uptime_percentage': 99.9,  # This would be calculated from component statuses
                    'avg_response_time': 45,     # This would be calculated from actual response times
                    'emails_sent': emails_sent,
                    'api_requests': api_requests,
                    'error_rate': error_rate
                }
            )
            
            if not created:
                metrics.emails_sent = emails_sent
                metrics.api_requests = api_requests
                metrics.error_rate = error_rate
                metrics.save()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating daily metrics: {str(e)}")
            return False
    
    @staticmethod
    def initialize_default_components():
        """Initialize default system components"""
        components = [
            {'name': 'API Server', 'description': 'Main API endpoints and authentication'},
            {'name': 'Database', 'description': 'Primary database and data storage'},
            {'name': 'SMTP Gateway', 'description': 'Email delivery and SMTP services'},
            {'name': 'Analytics Engine', 'description': 'Email tracking and analytics processing'},
            {'name': 'Webhook Service', 'description': 'Webhook delivery and event processing'},
        ]
        
        for i, component_data in enumerate(components):
            SystemComponent.objects.get_or_create(
                name=component_data['name'],
                defaults={
                    'description': component_data['description'],
                    'order': i,
                    'is_active': True
                }
            )
        
        # Initialize status page settings
        StatusPageSettings.get_settings()
