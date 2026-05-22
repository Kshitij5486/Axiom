const fs = require("fs");
let content = fs.readFileSync("src/resolvers.js", "utf8");
content = content.replace(
  "nodeCount: graphData.node_count || 0,\n          edgeCount: graphData.edge_count || 0,",
  "nodeCount: graphData.node_list?.length || Object.keys(graphData.effect_sizes || {}).length || 0,\n          edgeCount: graphData.adjacency_json?.length || Object.keys(graphData.effect_sizes || {}).length || 0,"
);
fs.writeFileSync("src/resolvers.js", content);
console.log("Fixed");