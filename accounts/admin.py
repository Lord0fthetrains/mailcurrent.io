from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Plan, Subscription, UsageLog, BillingHistory


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom user admin"""
    list_display = ('email', 'username', 'first_name', 'last_name', 'company_name', 'is_verified', 'date_joined')
    list_filter = ('is_verified', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'company_name')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('company_name', 'phone', 'is_verified')}),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('company_name', 'phone')}),
    )


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """Pricing plan admin"""
    list_display = ('name', 'price_monthly', 'price_yearly', 'emails_per_month', 'api_keys_limit', 'is_active')
    list_filter = ('is_active', 'custom_templates', 'attachments', 'webhooks', 'analytics', 'priority_support')
    search_fields = ('name', 'description')
    ordering = ('price_monthly',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Subscription admin"""
    list_display = ('user', 'plan', 'status', 'billing_cycle', 'current_period_end', 'emails_sent_this_period')
    list_filter = ('status', 'billing_cycle', 'plan')
    search_fields = ('user__email', 'user__username', 'stripe_subscription_id')
    readonly_fields = ('created_at', 'updated_at', 'emails_sent_this_period', 'last_reset_date')
    ordering = ('-created_at',)


@admin.register(UsageLog)
class UsageLogAdmin(admin.ModelAdmin):
    """Usage log admin"""
    list_display = ('user', 'api_key', 'emails_sent', 'cost', 'timestamp')
    list_filter = ('timestamp', 'user')
    search_fields = ('user__email', 'api_key__name')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)


@admin.register(BillingHistory)
class BillingHistoryAdmin(admin.ModelAdmin):
    """Billing history admin"""
    list_display = ('user', 'subscription', 'amount', 'currency', 'status', 'created_at', 'paid_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('user__email', 'stripe_invoice_id', 'stripe_payment_intent_id')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)