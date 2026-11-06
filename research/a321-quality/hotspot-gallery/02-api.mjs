const task=await taskSpace(13),p=task.page("p1");
const fs=await import("node:fs/promises");
const base="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
const health=await p.fetch("/api/health");
const result=await p.fetch("/api/datasets/open",{method:"POST",headers:{"content-type":"application/json"},
 body:JSON.stringify({path:"research/a321-quality/artifacts/snappy-03",timeIndex:"last"})});
if(!health.ok||!result.ok)throw Error(JSON.stringify({health:health.status,dataset:result.status}));
const id=JSON.parse(result.body).datasetId;
if(typeof id!=="string")throw Error(result.body);
const read=await p.fetch("/api/datasets/"+encodeURIComponent(id));
const mesh=JSON.parse(read.body);
if(!read.ok||mesh.cellCount!==462113||mesh.source!=="polymesh")throw Error(JSON.stringify(mesh));
await fs.writeFile(base+"/studio-api-20261107.json",JSON.stringify({
 health:JSON.parse(health.body),openStatus:result.status,readStatus:read.status,id,source:mesh.source,
 cells:mesh.cellCount,points:mesh.pointCount,fields:mesh.fields.length,times:mesh.times.length,solverExecuted:false
},null,2)+"\n");
console.log({id,cells:mesh.cellCount,points:mesh.pointCount,fields:mesh.fields.length});
console.log(await p.evaluate(()=>[...document.querySelectorAll("[data-path]")].filter(n=>n.getAttribute("data-path").includes("a321-quality")).slice(0,12).map(n=>({path:n.getAttribute("data-path"),expanded:n.getAttribute("aria-expanded")}))));
