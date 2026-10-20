import json, urllib.request
for n in ('canaux_irrigation','aire_sechage'):
    try:
        r = urllib.request.urlopen(f'http://127.0.0.1:5000/api/{n}')
        data = json.load(r)
        print(n, 'features', len(data.get('features',[])))
        if data.get('features'):
            print('  sample props:', data['features'][0].get('properties'))
    except Exception as e:
        print('ERR', n, e)
