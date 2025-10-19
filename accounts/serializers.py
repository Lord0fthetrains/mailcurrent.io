from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, Plan, Subscription, UsageLog, BillingHistory


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'company_name', 'phone', 'password', 'password_confirm')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            # First check if user exists and is inactive
            try:
                from .models import User
                user = User.objects.get(email=email)
                if not user.is_active:
                    raise serializers.ValidationError('Account suspended. Your account has been deactivated. Please contact support for assistance.')
            except User.DoesNotExist:
                pass  # User doesn't exist, continue with normal authentication
            
            # Use Django's authenticate function to handle multiple backends
            from django.contrib.auth import authenticate
            user = authenticate(username=email, password=password)
            
            if user:
                attrs['user'] = user
            else:
                raise serializers.ValidationError('Invalid credentials')
        else:
            raise serializers.ValidationError('Must include email and password')
        
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    subscription = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'company_name', 'phone', 'is_verified', 'is_active', 'date_joined', 'subscription')
        read_only_fields = ('id', 'date_joined', 'is_verified', 'is_active')
    
    def get_subscription(self, obj):
        if hasattr(obj, 'subscription'):
            return SubscriptionSerializer(obj.subscription).data
        return None


class PlanSerializer(serializers.ModelSerializer):
    """Serializer for pricing plans"""
    class Meta:
        model = Plan
        fields = ('id', 'name', 'description', 'price_monthly', 'price_yearly', 'emails_per_month', 
                 'api_keys_limit', 'custom_templates', 'attachments', 'webhooks', 'analytics', 'priority_support')


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for user subscription"""
    plan = PlanSerializer(read_only=True)
    plan_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Subscription
        fields = ('id', 'plan', 'plan_id', 'status', 'billing_cycle', 'current_period_start', 
                 'current_period_end', 'trial_end', 'emails_sent_this_period', 'created_at')
        read_only_fields = ('id', 'status', 'current_period_start', 'current_period_end', 
                           'trial_end', 'emails_sent_this_period', 'created_at')


class UsageLogSerializer(serializers.ModelSerializer):
    """Serializer for usage logs"""
    api_key_name = serializers.CharField(source='api_key.name', read_only=True)
    
    class Meta:
        model = UsageLog
        fields = ('id', 'api_key_name', 'emails_sent', 'timestamp', 'cost')


class BillingHistorySerializer(serializers.ModelSerializer):
    """Serializer for billing history"""
    class Meta:
        model = BillingHistory
        fields = ('id', 'amount', 'currency', 'status', 'period_start', 'period_end', 'created_at', 'paid_at')


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    new_password_confirm = serializers.CharField()
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value


class UpdateProfileSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'company_name', 'phone')
