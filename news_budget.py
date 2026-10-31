"""Local USD budget for this bot, not an account-wide KRW billing guarantee.

Reserve a conservative maximum BEFORE a paid request; settle against usage.
Ambiguous failures keep their reservation; later retries must reserve again.
No token-counting API, external pricing lookup or additional model call is used.
"""
from datetime import datetime, timezone
import json
import math
import os
import uuid

DEFAULT_MONTHLY_USD = 28.0


def maximum_request_usd(model, payload, options, rates):
    if model not in {'gpt-6-luna', 'gpt-6.1-sol'} or options.get('service_tier') != 'default':
        raise ValueError('예산 검증되지 않은 모델/서비스 등급')
    output = options.get('max_output_tokens')
    if type(output) is not int or not 0 < output <= 4096:
        raise ValueError('예산 검증되지 않은 출력 한도')
    encoded = json.dumps(payload, ensure_ascii=False).encode('utf8')
    # UTF-8 byte count is a conservative text-token bound; add envelope margin.
    # Image compression is unrelated to visual tokens: reserve the model's full
    # context bound for any vision request instead of counting base64 characters.
    inp = 1050000 if b'input_image' in encoded else min(1050000, len(encoded) + 4096)
    # Reserve all input at the more expensive 12h cache-write rate (2.5x),
    # even though this app normally uses the default 30m implicit cache.
    bound = (inp * rates[0] * 2.5 * (2 if inp > 272000 else 1)
             + output * rates[2] * (1.5 if inp > 272000 else 1)) / 1e6
    return math.ceil(bound * 1e9) / 1e9


class BudgetLedger:
    def __init__(self, store):
        self.store = store
        raw = os.environ.get('NEWS_MONTHLY_API_BUDGET_USD', str(DEFAULT_MONTHLY_USD))
        try: self.limit = float(raw)
        except ValueError: self.limit = 0.0
        if not math.isfinite(self.limit) or self.limit < 0: self.limit = 0.0
        self.month = datetime.fromtimestamp(store.clock(), timezone.utc).strftime('%Y-%m')
        self.pending = store.data.setdefault('budget_reservations_v1', {})
        self.reason = ''

    def spent(self):
        return sum(float(bucket.get('estimated_usd', 0))
                   for day, models in self.store.usage.items() if day.startswith(self.month)
                   for stages in models.values() for bucket in stages.values())

    def reserve(self, request_key, model, payload, options, rates):
        current = [v for v in self.pending.values() if v.get('month') == self.month]
        try: amount = maximum_request_usd(model, payload, options, rates)
        except ValueError as exc:
            self.reason = str(exc)
            return None
        used = self.spent() + sum(v['reserved_usd'] for v in current)
        if used + amount > self.limit:
            self.reason = f'월 API 예산 검토보류: {self.month} 사용·예약 ${used:.4f}, 한도 ${self.limit:.2f}'
            return None
        ticket = uuid.uuid4().hex
        self.pending[ticket] = {'month': self.month, 'request_key': request_key,
                                'reserved_usd': amount, 'model': model}
        self.store.persist()
        return ticket

    def settle(self, ticket, confirmed_cost):
        # A timeout or absent usage may still have been billed. Keep the maximum
        # reservation rather than falsely treating an ambiguous request as free.
        if confirmed_cost is not None:
            del self.pending[ticket]
        self.store.persist()
