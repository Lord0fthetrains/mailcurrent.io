import re
import dns.resolver
import dns.exception
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from .security_models import (
    BlacklistEntry, SpamScore, SpamRule, EmailSecurityLog,
    DKIMRecord, SPFRecord, DMARCRecord
)
from .models import EmailLog
import logging

logger = logging.getLogger('api')


class SecurityService:
    """Service for email security, spam detection, and blacklist management"""
    
    @staticmethod
    def check_blacklist(email_address, domain=None, ip_address=None):
        """Check if email address, domain, or IP is blacklisted"""
        blacklist_entries = []
        
        # Check email address
        if email_address:
            email_entries = BlacklistEntry.objects.filter(
                entry_type='email',
                value__iexact=email_address,
                is_active=True
            )
            blacklist_entries.extend(email_entries)
        
        # Check domain
        if domain:
            domain_entries = BlacklistEntry.objects.filter(
                entry_type='domain',
                value__iexact=domain,
                is_active=True
            )
            blacklist_entries.extend(domain_entries)
        
        # Check IP address
        if ip_address:
            ip_entries = BlacklistEntry.objects.filter(
                entry_type='ip',
                value=ip_address,
                is_active=True
            )
            blacklist_entries.extend(ip_entries)
        
        # Check pattern matches
        pattern_entries = BlacklistEntry.objects.filter(
            entry_type='pattern',
            is_active=True
        )
        for entry in pattern_entries:
            try:
                if re.search(entry.value, email_address or '', re.IGNORECASE):
                    blacklist_entries.append(entry)
            except re.error:
                logger.warning(f"Invalid regex pattern in blacklist: {entry.value}")
        
        return blacklist_entries
    
    @staticmethod
    def calculate_spam_score(email_log, html_content=None, text_content=None):
        """Calculate spam score for an email"""
        score = 0.0
        triggered_rules = []
        
        # Get active spam rules
        rules = SpamRule.objects.filter(is_active=True)
        
        # Content analysis
        content = (html_content or '') + ' ' + (text_content or '')
        subject = email_log.subject or ''
        
        for rule in rules:
            try:
                if rule.rule_type == 'content':
                    if re.search(rule.pattern, content, re.IGNORECASE):
                        score += rule.score
                        triggered_rules.append({
                            'rule': rule.name,
                            'score': rule.score,
                            'type': rule.rule_type
                        })
                
                elif rule.rule_type == 'header':
                    if re.search(rule.pattern, subject, re.IGNORECASE):
                        score += rule.score
                        triggered_rules.append({
                            'rule': rule.name,
                            'score': rule.score,
                            'type': rule.rule_type
                        })
                
                elif rule.rule_type == 'sender':
                    if re.search(rule.pattern, email_log.from_email or '', re.IGNORECASE):
                        score += rule.score
                        triggered_rules.append({
                            'rule': rule.name,
                            'score': rule.score,
                            'type': rule.rule_type
                        })
                
                elif rule.rule_type == 'recipient':
                    if re.search(rule.pattern, email_log.to or '', re.IGNORECASE):
                        score += rule.score
                        triggered_rules.append({
                            'rule': rule.name,
                            'score': rule.score,
                            'type': rule.rule_type
                        })
                
                elif rule.rule_type == 'technical':
                    # Technical analysis (HTML structure, etc.)
                    if html_content and re.search(rule.pattern, html_content, re.IGNORECASE):
                        score += rule.score
                        triggered_rules.append({
                            'rule': rule.name,
                            'score': rule.score,
                            'type': rule.rule_type
                        })
            
            except re.error:
                logger.warning(f"Invalid regex pattern in spam rule: {rule.pattern}")
        
        # Normalize score to 0-1 range
        score = max(0.0, min(1.0, score))
        
        return {
            'score': score,
            'triggered_rules': triggered_rules
        }
    
    @staticmethod
    def get_spam_action(score):
        """Get action to take based on spam score"""
        try:
            spam_config = SpamScore.objects.filter(is_active=True).order_by('-threshold').first()
            if not spam_config:
                return 'allow', 0.0
            
            if score >= spam_config.threshold:
                return spam_config.action, spam_config.threshold
            else:
                return 'allow', spam_config.threshold
                
        except Exception as e:
            logger.error(f"Error getting spam action: {e}")
            return 'allow', 0.0
    
    @staticmethod
    def log_security_event(email_log, event_type, details=None, score=None, action_taken=None):
        """Log security-related event"""
        try:
            EmailSecurityLog.objects.create(
                email_log=email_log,
                event_type=event_type,
                details=details or {},
                score=score,
                action_taken=action_taken or ''
            )
        except Exception as e:
            logger.error(f"Error logging security event: {e}")
    
    @staticmethod
    def validate_email_security(email_log, html_content=None, text_content=None):
        """Comprehensive email security validation"""
        security_issues = []
        action = 'allow'
        
        # Check blacklist
        domain = email_log.to.split('@')[1] if '@' in email_log.to else None
        blacklist_entries = SecurityService.check_blacklist(
            email_log.to, domain=domain
        )
        
        if blacklist_entries:
            security_issues.append({
                'type': 'blacklist',
                'message': f"Email address or domain is blacklisted",
                'entries': [str(entry) for entry in blacklist_entries]
            })
            action = 'reject'
            
            SecurityService.log_security_event(
                email_log, 'blacklist_check', 
                {'blacklist_entries': [str(entry) for entry in blacklist_entries]},
                action_taken='rejected'
            )
        
        # Calculate spam score
        spam_result = SecurityService.calculate_spam_score(
            email_log, html_content, text_content
        )
        
        spam_action, threshold = SecurityService.get_spam_action(spam_result['score'])
        
        if spam_action != 'allow':
            security_issues.append({
                'type': 'spam',
                'message': f"Spam score {spam_result['score']:.3f} exceeds threshold {threshold:.3f}",
                'score': spam_result['score'],
                'threshold': threshold,
                'triggered_rules': spam_result['triggered_rules']
            })
            action = spam_action
            
            SecurityService.log_security_event(
                email_log, 'spam_score',
                {
                    'score': spam_result['score'],
                    'threshold': threshold,
                    'triggered_rules': spam_result['triggered_rules']
                },
                score=spam_result['score'],
                action_taken=spam_action
            )
        
        return {
            'action': action,
            'issues': security_issues,
            'spam_score': spam_result['score'],
            'spam_threshold': threshold
        }


class DKIMService:
    """Service for DKIM configuration and verification"""
    
    @staticmethod
    def generate_dkim_record(domain, selector='default'):
        """Generate DKIM record for a domain"""
        try:
            # In a real implementation, you would generate actual RSA keys
            # For this example, we'll create placeholder keys
            private_key = f"-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----"
            public_key = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA..."
            
            dkim_record = DKIMRecord.objects.create(
                domain=domain,
                selector=selector,
                private_key=private_key,
                public_key=public_key
            )
            
            # Generate DNS TXT record
            dns_record = f"{selector}._domainkey.{domain} TXT \"v=DKIM1; k=rsa; p={public_key}\""
            
            return {
                'success': True,
                'dkim_record': dkim_record,
                'dns_record': dns_record
            }
            
        except Exception as e:
            logger.error(f"Error generating DKIM record: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def verify_dkim_record(domain, selector='default'):
        """Verify DKIM record exists in DNS"""
        try:
            record_name = f"{selector}._domainkey.{domain}"
            answers = dns.resolver.resolve(record_name, 'TXT')
            
            for answer in answers:
                txt_record = str(answer).strip('"')
                if 'v=DKIM1' in txt_record:
                    return {
                        'success': True,
                        'record': txt_record,
                        'valid': True
                    }
            
            return {
                'success': True,
                'record': None,
                'valid': False
            }
            
        except dns.exception.DNSException as e:
            logger.error(f"DNS error verifying DKIM: {e}")
            return {
                'success': False,
                'error': f"DNS error: {e}"
            }
        except Exception as e:
            logger.error(f"Error verifying DKIM record: {e}")
            return {
                'success': False,
                'error': str(e)
            }


class SPFService:
    """Service for SPF configuration and verification"""
    
    @staticmethod
    def generate_spf_record(domain, includes=None, ip_addresses=None):
        """Generate SPF record for a domain"""
        try:
            includes = includes or []
            ip_addresses = ip_addresses or []
            
            # Build SPF record
            spf_parts = ['v=spf1']
            
            # Add includes
            for include in includes:
                spf_parts.append(f'include:{include}')
            
            # Add IP addresses
            for ip in ip_addresses:
                spf_parts.append(f'ip4:{ip}')
            
            # Add default action
            spf_parts.append('~all')
            
            spf_record = ' '.join(spf_parts)
            
            spf_obj = SPFRecord.objects.create(
                domain=domain,
                spf_record=spf_record,
                includes=includes,
                ip_addresses=ip_addresses
            )
            
            return {
                'success': True,
                'spf_record': spf_obj,
                'dns_record': f"{domain} TXT \"{spf_record}\""
            }
            
        except Exception as e:
            logger.error(f"Error generating SPF record: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def verify_spf_record(domain):
        """Verify SPF record exists in DNS"""
        try:
            answers = dns.resolver.resolve(domain, 'TXT')
            
            for answer in answers:
                txt_record = str(answer).strip('"')
                if txt_record.startswith('v=spf1'):
                    return {
                        'success': True,
                        'record': txt_record,
                        'valid': True
                    }
            
            return {
                'success': True,
                'record': None,
                'valid': False
            }
            
        except dns.exception.DNSException as e:
            logger.error(f"DNS error verifying SPF: {e}")
            return {
                'success': False,
                'error': f"DNS error: {e}"
            }
        except Exception as e:
            logger.error(f"Error verifying SPF record: {e}")
            return {
                'success': False,
                'error': str(e)
            }


class DMARCService:
    """Service for DMARC configuration and verification"""
    
    @staticmethod
    def generate_dmarc_record(domain, policy='quarantine', percentage=100, rua=None, ruf=None):
        """Generate DMARC record for a domain"""
        try:
            dmarc_parts = [f'v=DMARC1; p={policy}; pct={percentage}']
            
            if rua:
                dmarc_parts.append(f'rua=mailto:{rua}')
            
            if ruf:
                dmarc_parts.append(f'ruf=mailto:{ruf}')
            
            dmarc_record = '; '.join(dmarc_parts)
            
            dmarc_obj = DMARCRecord.objects.create(
                domain=domain,
                policy=policy,
                percentage=percentage,
                rua=rua or '',
                ruf=ruf or ''
            )
            
            return {
                'success': True,
                'dmarc_record': dmarc_obj,
                'dns_record': f"_dmarc.{domain} TXT \"{dmarc_record}\""
            }
            
        except Exception as e:
            logger.error(f"Error generating DMARC record: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def verify_dmarc_record(domain):
        """Verify DMARC record exists in DNS"""
        try:
            dmarc_domain = f"_dmarc.{domain}"
            answers = dns.resolver.resolve(dmarc_domain, 'TXT')
            
            for answer in answers:
                txt_record = str(answer).strip('"')
                if txt_record.startswith('v=DMARC1'):
                    return {
                        'success': True,
                        'record': txt_record,
                        'valid': True
                    }
            
            return {
                'success': True,
                'record': None,
                'valid': False
            }
            
        except dns.exception.DNSException as e:
            logger.error(f"DNS error verifying DMARC: {e}")
            return {
                'success': False,
                'error': f"DNS error: {e}"
            }
        except Exception as e:
            logger.error(f"Error verifying DMARC record: {e}")
            return {
                'success': False,
                'error': str(e)
            }
