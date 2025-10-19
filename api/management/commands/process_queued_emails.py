from django.core.management.base import BaseCommand
from api.models import EmailLog
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger('api')


class Command(BaseCommand):
    help = 'Process all queued emails and attempt to send them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually sending emails',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit the number of emails to process (0 = all)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('Running in dry-run mode - no emails will be sent')
            )
        
        # Get queued emails
        queued_emails = EmailLog.objects.filter(status='queued').order_by('created_at')
        
        if limit > 0:
            queued_emails = queued_emails[:limit]
        
        total_count = queued_emails.count()
        self.stdout.write(f'Found {total_count} queued emails to process')
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('No queued emails found'))
            return
        
        success_count = 0
        error_count = 0
        
        for email in queued_emails:
            self.stdout.write(f'Processing email ID {email.id}: {email.subject} -> {email.to}')
            
            if dry_run:
                self.stdout.write(f'  [DRY RUN] Would send: {email.subject}')
                continue
            
            try:
                # Send the email using Django's send_mail
                result = send_mail(
                    subject=email.subject,
                    message='',  # EmailLog doesn't store the actual content
                    from_email=email.from_email,
                    recipient_list=[email.to],
                    fail_silently=False
                )
                
                if result:
                    # Mark as sent
                    email.mark_sent(f'processed-{email.id}')
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Sent successfully')
                    )
                else:
                    # Mark as failed
                    email.mark_failed('Failed to send - no result from send_mail')
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Failed to send')
                    )
                    
            except Exception as e:
                # Mark as failed
                email.mark_failed(f'Processing error: {str(e)}')
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error: {str(e)}')
                )
                logger.error(f"Error processing email {email.id}: {str(e)}")
        
        # Summary
        if not dry_run:
            self.stdout.write('\n' + '='*50)
            self.stdout.write(f'Processing complete:')
            self.stdout.write(f'  Successfully sent: {success_count}')
            self.stdout.write(f'  Failed: {error_count}')
            self.stdout.write(f'  Total processed: {success_count + error_count}')
            
            if success_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {success_count} emails sent successfully')
                )
            if error_count > 0:
                self.stdout.write(
                    self.style.ERROR(f'✗ {error_count} emails failed')
                )
        else:
            self.stdout.write(f'\n[DRY RUN] Would process {total_count} emails')
