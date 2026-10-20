from pathlib import Path
text = Path('templates/dashboard.html').read_text(encoding='utf-8')
start = text.index('<script>')
end = text.rindex('</script>')
js = text[start+len('<script>'):end]
counts = {'(':0, ')':0, '{':0, '}':0, '[':0, ']':0}
for ch in js:
    if ch in counts: counts[ch]+=1
print(counts)
# print snippet around suspected location
for token in ['new Chart(', 'loadMapLayers()', 'loadData()', 'L.control.layers', 'catch (error)']:
    idx = js.find(token)
    print(token, idx)
    if idx != -1:
        print(js[idx:idx+200].replace('\n',' '))
