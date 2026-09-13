"""Mock provider output for transport tests; no model or semantic evaluation."""
import copy
import json


def attach_claims(reply, request):
    result = copy.deepcopy(reply)
    if request and 'intent_claims' in (request.get('response_schema') or {}).get('required', []):
        value = json.loads(request['prompt'].split('\n\nHOST INTENT FRAME\n', 1)[1].split('\n', 1)[0])
        result.setdefault('intent_claims', {'revision':value['revision'],
                          'conditions':[{k:row[k] for k in ('id','strength')} for row in value['conditions']]})
    return result
