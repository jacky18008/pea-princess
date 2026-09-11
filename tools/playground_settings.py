"""Recorded test configuration, distinct from observed model compliance."""
import copy

DEPTHS = ('lite', 'standard', 'deep')
EFFORTS = ('low', 'medium', 'high')
SOURCES = ('user_selected', 'host_default', 'persona_card', 'legacy_record',
           'unrecorded', 'not_applicable')
FIELDS = ('research_depth', 'reasoning_effort', 'research_depth_source', 'reasoning_effort_source')


def unknown():
    return dict(research_depth=None, reasoning_effort=None,
                research_depth_source='unrecorded', reasoning_effort_source='unrecorded')


def validate(value, allow_unknown=False):
    if not isinstance(value, dict) or set(value) != set(FIELDS):
        raise ValueError('invalid execution settings fields')
    for field, choices in (('research_depth', DEPTHS), ('reasoning_effort', EFFORTS)):
        item, source = value[field], value[field+'_source']
        if not isinstance(source, str) or source not in SOURCES:
            raise ValueError('invalid execution settings source')
        if item is None:
            if field == 'research_depth' and source == 'not_applicable':
                continue
            if allow_unknown and source == 'unrecorded':
                continue
            raise ValueError('missing execution setting')
        if not isinstance(item, str) or item not in choices or source in ('unrecorded', 'not_applicable'):
            raise ValueError('invalid '+field)
    return copy.deepcopy(value)


def configured(data, mode, card=None):
    fallback = ((card or {}).get('settings') or {}).get('budget_mode', 'standard') if mode == 'fixture' else 'standard'
    value = dict(research_depth=data.get('research_depth', fallback),
                 reasoning_effort=data.get('reasoning_effort', 'low'),
                 research_depth_source='user_selected' if 'research_depth' in data else 'persona_card' if mode == 'fixture' else 'host_default',
                 reasoning_effort_source='user_selected' if 'reasoning_effort' in data else 'host_default')
    return validate(value)


def read_session(session):
    if 'execution_settings' in session:
        return validate(session['execution_settings'], allow_unknown=True)
    # Preserve only values actually stored in old records. The skill's default
    # or the current launcher's effort is not proof of an old call's settings.
    result = unknown()
    depth = (session.get('runtime_settings') or {}).get('budget_mode')
    if isinstance(depth, str) and depth in DEPTHS:
        result.update(research_depth=depth, research_depth_source='legacy_record')
    return result


def for_call(session, actor):
    result = validate(read_session(session))
    if actor == 'persona':
        result.update(research_depth=None, research_depth_source='not_applicable')
    return result


def depth_instruction(settings):
    depth = validate(settings)['research_depth']
    return ('\n\nCONFIGURED RESEARCH SCOPE (internal; never announce as a banner)\n'
            'Initial budget_mode: '+depth+'. Use this baseline when choosing research depth '
            'and depth parameters for shipped tools. It does not change the user\'s conditions '
            'or require an intake questionnaire. Later explicit user requests override this '
            'baseline within their scope, including requests to do less or more research. '
            'Retain those changes in the conversation; a configured setting is not proof of '
            'completed research. Answer the current question in plain language.')
