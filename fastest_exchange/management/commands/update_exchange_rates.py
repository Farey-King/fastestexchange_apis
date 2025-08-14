"""
Django Management Command: Update Exchange Rates

This command fetches the latest exchange rates from external APIs
and updates the database. Can be run manually or via cron job.

Usage:
    python manage.py update_exchange_rates
    python manage.py update_exchange_rates --currency-pairs NGN_USD USD_NGN
    python manage.py update_exchange_rates --force-refresh
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from decimal import Decimal
from fastest_exchange.exchange_rate_service import ExchangeRateService
from fastest_exchange.models import ExchangeRate
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Update exchange rates from external APIs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--currency-pairs',
            nargs='+',
            type=str,
            help='Specific currency pairs to update (e.g., NGN_USD USD_NGN)',
            default=None
        )
        
        parser.add_argument(
            '--force-refresh',
            action='store_true',
            help='Force refresh all rates, ignoring cache',
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )

    def handle(self, *args, **options):
        self.verbosity = 1
        if options['verbose']:
            self.verbosity = 2
            
        self.stdout.write(
            self.style.SUCCESS('[{}] Starting exchange rate update...'.format(
                timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
        )

        # Determine which currency pairs to update
        if options['currency_pairs']:
            pairs_to_update = []
            for pair in options['currency_pairs']:
                if '_' in pair:
                    from_curr, to_curr = pair.split('_', 1)
                    pairs_to_update.append((from_curr.upper(), to_curr.upper()))
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Invalid currency pair format: {pair}. Use FORMAT: FROM_TO')
                    )
        else:
            # Default pairs to update
            pairs_to_update = [
                ('NGN', 'USD'), ('USD', 'NGN'),
                ('UGX', 'NGN'), ('NGN', 'UGX'),
                ('USD', 'UGX'), ('UGX', 'USD')
            ]

        if self.verbosity >= 2:
            self.stdout.write(f'Currency pairs to update: {pairs_to_update}')

        # Clear cache if force refresh is requested
        if options['force_refresh']:
            self.stdout.write('Force refresh enabled - clearing rate cache...')
            from django.core.cache import cache
            for from_curr, to_curr in pairs_to_update:
                cache_key = f"exchange_rate_{from_curr}_{to_curr}"
                cache.delete(cache_key)

        # Update rates
        updated_rates = []
        failed_pairs = []
        
        for from_currency, to_currency in pairs_to_update:
            try:
                success = self.update_currency_pair(
                    from_currency, 
                    to_currency, 
                    options['dry_run']
                )
                
                if success:
                    updated_rates.append(f"{from_currency}_{to_currency}")
                else:
                    failed_pairs.append(f"{from_currency}_{to_currency}")
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error updating {from_currency}->{to_currency}: {e}')
                )
                failed_pairs.append(f"{from_currency}_{to_currency}")

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Exchange rate update completed!'))
        self.stdout.write(f'Successfully updated: {len(updated_rates)} pairs')
        self.stdout.write(f'Failed: {len(failed_pairs)} pairs')
        
        if updated_rates:
            self.stdout.write(self.style.SUCCESS(f'Updated pairs: {", ".join(updated_rates)}'))
            
        if failed_pairs:
            self.stdout.write(self.style.WARNING(f'Failed pairs: {", ".join(failed_pairs)}'))

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No actual changes were made'))

        self.stdout.write('='*50)

    def update_currency_pair(self, from_currency, to_currency, dry_run=False):
        """Update a single currency pair"""
        
        if self.verbosity >= 2:
            self.stdout.write(f'Updating {from_currency} -> {to_currency}...')

        try:
            # Try to fetch from external APIs
            api_rate = ExchangeRateService._fetch_external_rate(from_currency, to_currency)
            
            if not api_rate or 'error' in api_rate:
                if self.verbosity >= 2:
                    self.stdout.write(
                        self.style.WARNING(f'  No API rate available for {from_currency}->{to_currency}')
                    )
                return False

            new_rate = Decimal(str(api_rate['rate']))
            source = api_rate.get('source', 'unknown')
            
            # Get current rate for comparison
            current_rate_obj = ExchangeRate.objects.filter(
                currency_from=from_currency,
                currency_to=to_currency
            ).order_by('-created_at').first()
            
            current_rate = current_rate_obj.rate if current_rate_obj else None
            
            # Check if rate has changed significantly (more than 0.1% change)
            rate_changed = True
            if current_rate:
                change_pct = abs((new_rate - current_rate) / current_rate * 100)
                rate_changed = change_pct >= 0.1  # Update if change is >= 0.1%
                
                if self.verbosity >= 2:
                    self.stdout.write(
                        f'  Current: {current_rate}, New: {new_rate}, Change: {change_pct:.2f}%'
                    )
            
            if not rate_changed and not dry_run:
                if self.verbosity >= 2:
                    self.stdout.write(f'  Rate change too small, skipping update')
                return True

            # Update the rate
            if not dry_run:
                rate_obj = ExchangeRateService.update_exchange_rate(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=new_rate
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Updated {from_currency}->{to_currency}: {new_rate} (from {source})'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  [DRY RUN] Would update {from_currency}->{to_currency}: {new_rate} (from {source})'
                    )
                )
                
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ✗ Failed to update {from_currency}->{to_currency}: {e}')
            )
            return False
