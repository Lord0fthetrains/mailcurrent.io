from django.core.management.base import BaseCommand
from accounts.models import Plan


class Command(BaseCommand):
    help = 'Create initial pricing plans'

    def handle(self, *args, **options):
        plans_data = [
            {
                'name': 'Free Trial',
                'description': 'Perfect for testing and small projects. 14-day trial with basic features.',
                'price_monthly': 0.00,
                'price_yearly': 0.00,
                'emails_per_month': 1000,
                'api_keys_limit': 2,
                'custom_templates': False,
                'attachments': False,
                'webhooks': False,
                'analytics': False,
                'priority_support': False,
            },
            {
                'name': 'Starter',
                'description': 'Great for small businesses and startups. All basic features included.',
                'price_monthly': 9.99,
                'price_yearly': 99.99,
                'emails_per_month': 10000,
                'api_keys_limit': 5,
                'custom_templates': True,
                'attachments': True,
                'webhooks': False,
                'analytics': False,
                'priority_support': False,
            },
            {
                'name': 'Professional',
                'description': 'Perfect for growing businesses. Advanced features and higher limits.',
                'price_monthly': 29.99,
                'price_yearly': 299.99,
                'emails_per_month': 50000,
                'api_keys_limit': 15,
                'custom_templates': True,
                'attachments': True,
                'webhooks': True,
                'analytics': True,
                'priority_support': False,
            },
            {
                'name': 'Enterprise',
                'description': 'For large organizations with high volume needs. All features included.',
                'price_monthly': 99.99,
                'price_yearly': 999.99,
                'emails_per_month': 200000,
                'api_keys_limit': 50,
                'custom_templates': True,
                'attachments': True,
                'webhooks': True,
                'analytics': True,
                'priority_support': True,
            },
        ]

        for plan_data in plans_data:
            plan, created = Plan.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created plan: {plan.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Plan already exists: {plan.name}')
                )

        self.stdout.write(
            self.style.SUCCESS('Successfully set up pricing plans!')
        )
