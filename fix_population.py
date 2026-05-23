content = open('C:/Users/KSHITIJ/axiom/services/dashboard/population.html', encoding='utf-8').read()

# The edge tooltip innerHTML uses template literal with edge.source/target
# After D3 simulation, source/target become node objects - fix in showEdgeTip function
old = 'function showEdgeTip(event, edge){'
new = '''function showEdgeTip(event, edge){
  edge = Object.assign({}, edge);
  edge.source = (typeof edge.source==="object") ? edge.source.id : edge.source;
  edge.target = (typeof edge.target==="object") ? edge.target.id : edge.target;'''

content = content.replace(old, new)
open('C:/Users/KSHITIJ/axiom/services/dashboard/population.html', 'w', encoding='utf-8').write(content)
print('Fixed')
