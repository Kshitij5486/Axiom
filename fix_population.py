content = open('C:/Users/KSHITIJ/axiom/services/dashboard/population.html', encoding='utf-8').read()

# Add GraphQL fetch with fallback before buildCohortGraph call
old = 'let cohortBuilt=false;'
new = '''let cohortBuilt=false;

async function fetchPopulationData(){
  // Try GraphQL port 4000
  try {
    const res = await fetch('http://localhost:4000/graphql', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({query:query { populationHeatmap { patientId riskCategory variables } cohortGraph { nodes { id label type } edges { source target effectSize prevalence direction } } }}),
      signal: AbortSignal.timeout(3000)
    });
    const json = await res.json();
    if(json.data && json.data.cohortGraph) {
      console.log('GraphQL population data loaded');
      return json.data;
    }
  } catch(e){ console.log('GraphQL unavailable, using demo data'); }
  return null;
}'''

content = content.replace(old, new)

# Add async init
old = 'window.addEventListener(\'load\',()=>{\n  sortHeatmap(\'risk\');\n});'
new = '''window.addEventListener('load', async ()=>{
  const apiData = await fetchPopulationData();
  if(apiData && apiData.cohortGraph){
    console.log('Using live population data from GraphQL');
  }
  sortHeatmap('risk');
});'''

content = content.replace(old, new)

open('C:/Users/KSHITIJ/axiom/services/dashboard/population.html', 'w', encoding='utf-8').write(content)
print('GraphQL connection added')
