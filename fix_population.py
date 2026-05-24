content = open('C:/Users/KSHITIJ/axiom/services/dashboard/population.html', encoding='utf-8').read()

# Fix the broken GraphQL query string - missing backticks
content = content.replace(
    'body: JSON.stringify({query:query { populationHeatmap { patientId riskCategory variables } cohortGraph { nodes { id label type } edges { source target effectSize prevalence direction } } }}),',
    'body: JSON.stringify({query:"{ populationHeatmap { patientId riskCategory variables } cohortGraph { nodes { id label type } edges { source target effectSize prevalence direction } } }"}), '
)

open('C:/Users/KSHITIJ/axiom/services/dashboard/population.html', 'w', encoding='utf-8').write(content)
print('Fixed')
