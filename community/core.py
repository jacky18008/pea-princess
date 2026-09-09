"""Strict public-only feedback validation and local aggregation (stdlib, no network).

Only curated place identifiers and fixed choices enter public data. Private notes
are a separate browser feature: this module has no note field or content filter.
"""
import datetime
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
MAX_PAYLOAD_BYTES = 16384
MAX_CATALOG_BYTES = 131072
MAX_PLACES = 500
MAX_REPORTS = 10000
RATINGS = ('very_bad', 'bad', 'mixed', 'good', 'very_good', 'unknown', 'not_applicable')
DIMENSIONS = ('cleanliness', 'noise', 'transport', 'facilities', 'maintenance')
KINDS = ('lived', 'visited', 'hearsay', 'undisclosed')
OVERALL = ('would_return', 'would_not_return', 'unsure', 'not_applicable')
LICENSE = 'CC0-1.0'
IDENTIFIER = re.compile(r'^[a-z][a-z0-9-]{2,63}$')
MONTH = re.compile(r'^[0-9]{4}-(0[1-9]|1[0-2])$')


class Rejected(ValueError):
    """Codes are fixed strings, never derived from untrusted input or filenames."""


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise Rejected('duplicate_json_key')
        out[key] = value
    return out


def load_json(path, limit=MAX_PAYLOAD_BYTES):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise Rejected('input_must_be_regular_file')
    if path.stat().st_size > limit:
        raise Rejected('input_too_large')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise Rejected('input_too_large')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Rejected('invalid_json')))
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise Rejected('invalid_json') from None


def catalog(value):
    if not isinstance(value, dict) or set(value) != {'schema_version', 'catalog_id', 'demo', 'places'}:
        raise Rejected('invalid_catalog')
    if type(value['schema_version']) is not int or value['schema_version'] != 1:
        raise Rejected('invalid_catalog')
    if not isinstance(value['catalog_id'], str) or not IDENTIFIER.fullmatch(value['catalog_id']):
        raise Rejected('invalid_catalog')
    if type(value['demo']) is not bool or not isinstance(value['places'], list) or not 1 <= len(value['places']) <= MAX_PLACES:
        raise Rejected('invalid_catalog')
    seen = set()
    for place in value['places']:
        if not isinstance(place, dict) or set(place) != {'place_id', 'name'}:
            raise Rejected('invalid_catalog')
        identifier, name = place['place_id'], place['name']
        if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier) or identifier in seen:
            raise Rejected('invalid_catalog')
        if not isinstance(name, str) or not 1 <= len(name) <= 100 or any(ord(c) < 32 for c in name):
            raise Rejected('invalid_catalog')
        if value['demo'] and not identifier.startswith('demo-'):
            raise Rejected('demo_catalog_requires_demo_ids')
        seen.add(identifier)
    return value


def load_catalog(path=None):
    return catalog(load_json(path or HERE / 'catalog.json', MAX_CATALOG_BYTES))


def schema(places):
    properties = {
        'schema_version': {'type': 'integer', 'const': 1},
        'place_id': {'type': 'string', 'enum': [p['place_id'] for p in places['places']]},
        'experience_month': {'type': 'string', 'pattern': MONTH.pattern,
                             'description': 'A completed UTC month within the previous 60 months; enforced by both validators.'},
        'experience_kind': {'type': 'string', 'enum': list(KINDS)},
    }
    properties.update({key: {'type': 'string', 'enum': list(RATINGS)} for key in DIMENSIONS})
    properties.update({'overall': {'type': 'string', 'enum': list(OVERALL)},
                       'consent': {'type': 'boolean', 'const': True},
                       'license': {'type': 'string', 'const': LICENSE}})
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema',
            'title': 'Public community feedback v1 (private notes excluded)',
            'type': 'object', 'additionalProperties': False,
            'required': list(properties), 'properties': properties}


def validate(value, places, today=None, allow_older=False):
    definition = schema(places)
    if not isinstance(value, dict) or set(value) != set(definition['required']):
        raise Rejected('public_fields_must_match_schema')
    for key, spec in definition['properties'].items():
        item = value[key]
        expected = {'integer': int, 'boolean': bool, 'string': str}[spec['type']]
        if type(item) is not expected:
            raise Rejected('invalid_public_choice')
        if 'const' in spec and item != spec['const'] or 'enum' in spec and item not in spec['enum']:
            raise Rejected('invalid_public_choice')
    month = value['experience_month']
    if not MONTH.fullmatch(month):
        raise Rejected('invalid_experience_month')
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    current = today.year * 12 + today.month - 1
    year, month_number = map(int, month.split('-'))
    offset = current - (year * 12 + month_number - 1)
    if offset < 1 or (offset > 60 and not allow_older):
        raise Rejected('experience_month_must_be_past_60_completed_months')
    # Copy only the validated shape, independent from caller-owned objects.
    return {key: value[key] for key in definition['required']}


def aggregate(records, places, place_id=None, today=None):
    ids = {p['place_id'] for p in places['places']}
    if place_id is not None and place_id not in ids:
        raise Rejected('unknown_place_id')
    if len(records) > MAX_REPORTS:
        raise Rejected('store_capacity_exceeded')
    groups = {}
    for raw in records:
        row = validate(raw, places, today, allow_older=True)
        if place_id and row['place_id'] != place_id:
            continue
        group = groups.setdefault(row['place_id'], {'sample_count': 0, 'months': {},
            'experience_kind': {key: 0 for key in KINDS},
            'ratings': {dimension: {key: 0 for key in RATINGS} for dimension in DIMENSIONS},
            'overall': {key: 0 for key in OVERALL}})
        group['sample_count'] += 1
        group['months'][row['experience_month']] = group['months'].get(row['experience_month'], 0) + 1
        group['experience_kind'][row['experience_kind']] += 1
        group['overall'][row['overall']] += 1
        for dimension in DIMENSIONS:
            group['ratings'][dimension][row[dimension]] += 1
    items = []
    for place in places['places']:
        if place_id and place['place_id'] != place_id:
            continue
        item = {'place_id': place['place_id'], 'name': place['name'], 'unverified': True}
        item.update(groups.get(place['place_id'], {'sample_count': 0}))
        items.append(item)
    return {'schema_version': 1, 'catalog_id': places['catalog_id'], 'demo': places['demo'],
            'evidence_class': 'S', 'unverified': True,
            'sample_unit': 'distinct_active_payloads_not_verified_people',
            'sample_count': sum(item['sample_count'] for item in items), 'places': items}
