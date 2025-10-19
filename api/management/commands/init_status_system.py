from django.core.management.base import BaseCommand
from api.status_service import StatusService


class Command(BaseCommand):
    help = 'Initialize the status monitoring system with default components'

    def handle(self, *args, **options):
        self.stdout.write('Initializing status monitoring system...')
        
        # Initialize default components
        StatusService.initialize_default_components()
        
        # Create initial status for each component
        components = [
            'API Server',
            'Database', 
            'SMTP Gateway',
            'Analytics Engine',
            'Webhook Service'
        ]
        
        for component_name in components:
            StatusService.update_component_status(
                component_name=component_name,
                status='operational',
                response_time=45,
                message='All systems functioning normally'
            )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully initialized status monitoring system!')
        )
        self.stdout.write('Created default components and initial status records.')
