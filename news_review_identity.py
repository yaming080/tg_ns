"""Equivalent URL tracking and aware date spellings are not new source evidence."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def canonical_url(value):
    if not isinstance(value, str) or not value:
        return value
    try:
        p = urlsplit(value if '://' in value else 'https://' + value)
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
            return value
        params = parse_qsl(p.query, keep_blank_values=True)
        kept = [(k, v) for k, v in params if not k.lower().startswith('utm_')
                and k.lower() not in {'fbclid', 'gclid', 'dclid', 'msclkid'}]
        # Unknown query fields, article IDs, and duplicate parameter order survive.
        query = urlencode(kept) if kept != params else p.query
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, query, ''))
    except ValueError:
        return value


def canonical_date(value):
    if not isinstance(value, (str, datetime)) or not value:
        return value
    try:
        dt = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError):
            return value
    if dt.tzinfo is None:
        return value  # Unknown time zones must never be guessed.
    return dt.astimezone(timezone.utc).isoformat()


def canonical_scope(scope):
    if isinstance(scope, list):
        return [canonical_scope(v) for v in scope]
    if not isinstance(scope, dict):
        return scope
    return {k: canonical_url(v) if k == 'url' else
            canonical_date(v) if k in ('pub', 'published', 'page_published_at') else
            canonical_scope(v) for k, v in scope.items()}
