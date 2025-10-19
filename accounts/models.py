from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from decimal import Decimal


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Extended user model with additional fields for the email service"""
    username = None  # Remove username field
    email = models.EmailField(unique=True)
    company_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, help_text="Designates whether this user account is active. Unselect this instead of deleting accounts.")
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    # Override the related names to avoid conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    
    def __str__(self):
        return self.email


class Plan(models.Model):
    """Pricing plans with different features and limits"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Usage limits
    emails_per_month = models.IntegerField(help_text="Maximum emails per month")
    api_keys_limit = models.IntegerField(help_text="Maximum API keys allowed")
    
    # Feature flags
    custom_templates = models.BooleanField(default=False)
    attachments = models.BooleanField(default=False)
    webhooks = models.BooleanField(default=False)
    analytics = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    
    # Stripe integration
    stripe_price_id_monthly = models.CharField(max_length=100, blank=True)
    stripe_price_id_yearly = models.CharField(max_length=100, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['price_monthly']
    
    def __str__(self):
        return self.name


class Subscription(models.Model):
    """User subscription to a plan"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('unpaid', 'Unpaid'),
        ('trialing', 'Trialing'),
    ]
    
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trialing')
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLE_CHOICES, default='monthly')
    
    # Stripe integration
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_payment_method_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Billing dates
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    trial_end = models.DateTimeField(null=True, blank=True)
    
    # Usage tracking
    emails_sent_this_period = models.IntegerField(default=0)
    last_reset_date = models.DateTimeField(auto_now_add=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"
    
    def is_trial_active(self):
        """Check if user is still in trial period"""
        if not self.trial_end:
            return False
        return timezone.now() < self.trial_end
    
    def can_send_email(self):
        """Check if user can send more emails this period"""
        if self.status not in ['active', 'trialing']:
            return False
        
        # Check if we need to reset the counter for new period
        if self._should_reset_usage():
            self._reset_usage()
        
        return self.emails_sent_this_period < self.plan.emails_per_month
    
    def _should_reset_usage(self):
        """Check if usage should be reset for new billing period"""
        now = timezone.now()
        if self.billing_cycle == 'monthly':
            return now >= self.current_period_end
        else:  # yearly
            return now >= self.current_period_end
    
    def _reset_usage(self):
        """Reset usage counter for new billing period"""
        self.emails_sent_this_period = 0
        self.last_reset_date = timezone.now()
        self.save(update_fields=['emails_sent_this_period', 'last_reset_date'])
    
    def increment_usage(self):
        """Increment email usage counter"""
        self.emails_sent_this_period += 1
        self.save(update_fields=['emails_sent_this_period'])


class UsageLog(models.Model):
    """Detailed usage tracking for billing and analytics"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='usage_logs')
    api_key = models.ForeignKey('api.APIKey', on_delete=models.CASCADE, related_name='usage_logs')
    emails_sent = models.IntegerField(default=1)
    timestamp = models.DateTimeField(auto_now_add=True)
    cost = models.DecimalField(max_digits=10, decimal_places=4, default=Decimal('0.0000'))
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.email} - {self.emails_sent} emails - {self.timestamp}"


class BillingHistory(models.Model):
    """Billing history and invoices"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='billing_history')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='billing_history')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    # Stripe integration
    stripe_invoice_id = models.CharField(max_length=100, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)
    
    status = models.CharField(max_length=20, choices=[
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ], default='pending')
    
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - ${self.amount} - {self.status}"