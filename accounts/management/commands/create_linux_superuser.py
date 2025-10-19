import os
import getpass
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a Django superuser for the current Linux user'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Linux username (defaults to current user)',
        )

    def handle(self, *args, **options):
        # Get current Linux user
        current_user = getpass.getuser()
        username = options.get('username') or current_user
        
        self.stdout.write(f'Creating Django superuser for Linux user: {username}')
        
        try:
            # Check if user already exists by email
            email = f'{username}@mailcurrent.io'
            if User.objects.filter(email=email).exists():
                user = User.objects.get(email=email)
                user.is_staff = True
                user.is_superuser = True
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Updated existing user {username} with superuser privileges')
                )
            else:
                # Create new superuser
                user = User.objects.create_user(
                    email=email,
                    first_name=username.title(),
                    last_name='System User',
                    is_staff=True,
                    is_superuser=True,
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Created superuser: {username}')
                )
            
            self.stdout.write(f'Email: {user.email}')
            self.stdout.write(f'Staff: {user.is_staff}')
            self.stdout.write(f'Superuser: {user.is_superuser}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {str(e)}')
            )
