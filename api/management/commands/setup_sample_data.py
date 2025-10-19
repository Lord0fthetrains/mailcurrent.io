from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import APIKey, EmailTemplate
from datetime import datetime


class Command(BaseCommand):
    help = 'Set up sample data for MailCurrent.io'

    def handle(self, *args, **options):
        self.stdout.write('Setting up sample data...')
        
        # Create sample API key
        api_key, created = APIKey.objects.get_or_create(
            name='Sample Service',
            defaults={
                'is_active': True,
                'rate_limit': 1000,
                'default_from_email': 'noreply@example.com',
                'default_from_name': 'Sample Service',
                'allowed_domains': ['example.com', 'test.com']
            }
        )
        
        if created:
            self.stdout.write(f'Created API key: {api_key.key}')
        else:
            self.stdout.write(f'API key already exists: {api_key.key}')
        
        # Create sample email templates
        templates_data = [
            {
                'name': 'welcome',
                'subject': 'Welcome to {{ app_name }}!',
                'html_content': self._get_welcome_html(),
                'text_content': self._get_welcome_text(),
                'description': 'Welcome email for new users',
                'required_variables': ['user_name', 'app_name'],
                'is_active': True
            },
            {
                'name': 'verification',
                'subject': 'Verify your email address - {{ app_name }}',
                'html_content': self._get_verification_html(),
                'text_content': self._get_verification_text(),
                'description': 'Email verification template',
                'required_variables': ['user_name', 'app_name', 'verification_link'],
                'is_active': True
            },
            {
                'name': 'notification',
                'subject': '{{ notification_title }} - {{ app_name }}',
                'html_content': self._get_notification_html(),
                'text_content': self._get_notification_text(),
                'description': 'General notification template',
                'required_variables': ['user_name', 'app_name', 'notification_title', 'notification_message'],
                'is_active': True
            }
        ]
        
        for template_data in templates_data:
            template, created = EmailTemplate.objects.get_or_create(
                name=template_data['name'],
                defaults=template_data
            )
            
            if created:
                self.stdout.write(f'Created template: {template.name}')
            else:
                self.stdout.write(f'Template already exists: {template.name}')
        
        self.stdout.write(
            self.style.SUCCESS('Sample data setup completed successfully!')
        )
        self.stdout.write(f'API Key: {api_key.key}')
        self.stdout.write('Admin user: admin / admin123')

    def _get_welcome_html(self):
        return '''<!DOCTYPE html>
<html>
<head>
    <title>Welcome to {{ app_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #007bff; color: white; padding: 20px; text-align: center; }
        .content { padding: 30px; background: #f9f9f9; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to {{ app_name }}!</h1>
        </div>
        <div class="content">
            <p>Hello {{ user_name }},</p>
            <p>Welcome to {{ app_name }}! We're excited to have you on board.</p>
            <p>Best regards,<br>The {{ app_name }} Team</p>
        </div>
    </div>
</body>
</html>'''

    def _get_welcome_text(self):
        return '''Welcome to {{ app_name }}!

Hello {{ user_name }},

Welcome to {{ app_name }}! We're excited to have you on board.

Best regards,
The {{ app_name }} Team'''

    def _get_verification_html(self):
        return '''<!DOCTYPE html>
<html>
<head>
    <title>Email Verification - {{ app_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #28a745; color: white; padding: 20px; text-align: center; }
        .content { padding: 30px; background: #f9f9f9; }
        .cta-button { background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Email Verification</h1>
        </div>
        <div class="content">
            <p>Hello {{ user_name }},</p>
            <p>Please verify your email address by clicking the button below:</p>
            <p><a href="{{ verification_link }}" class="cta-button">Verify Email</a></p>
            <p>Best regards,<br>The {{ app_name }} Team</p>
        </div>
    </div>
</body>
</html>'''

    def _get_verification_text(self):
        return '''Email Verification - {{ app_name }}

Hello {{ user_name }},

Please verify your email address by visiting:
{{ verification_link }}

Best regards,
The {{ app_name }} Team'''

    def _get_notification_html(self):
        return '''<!DOCTYPE html>
<html>
<head>
    <title>{{ notification_title }} - {{ app_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #6c757d; color: white; padding: 20px; text-align: center; }
        .content { padding: 30px; background: #f9f9f9; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ notification_title }}</h1>
        </div>
        <div class="content">
            <p>Hello {{ user_name }},</p>
            <p>{{ notification_message }}</p>
            <p>Best regards,<br>The {{ app_name }} Team</p>
        </div>
    </div>
</body>
</html>'''

    def _get_notification_text(self):
        return '''{{ notification_title }} - {{ app_name }}

Hello {{ user_name }},

{{ notification_message }}

Best regards,
The {{ app_name }} Team'''
