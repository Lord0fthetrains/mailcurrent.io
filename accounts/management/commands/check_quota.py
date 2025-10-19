from django.core.management.base import BaseCommand
from accounts.quota_service import QuotaNotificationService
import logging

logger = logging.getLogger('api')


class Command(BaseCommand):
    help = 'Check all user quotas and send notifications if needed'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without actually sending emails',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('Running in dry-run mode - no emails will be sent')
            )
        
        try:
            self.stdout.write('Checking user quotas...')
            
            if not dry_run:
                QuotaNotificationService.check_and_send_quota_notifications()
                self.stdout.write(
                    self.style.SUCCESS('Quota check completed successfully')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('Dry run completed - no emails sent')
                )
                
        except Exception as e:
            logger.error(f"Error in quota check command: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )
