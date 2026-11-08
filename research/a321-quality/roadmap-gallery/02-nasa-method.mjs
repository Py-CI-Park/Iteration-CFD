// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
const task=await taskSpace(10),p=task.page("p1");
const sources=[];
for(const url of [
 "https://www.grc.nasa.gov/www/wind/valid/tutorial/process.html",
 "https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html"]){
 await p.goto(url,{waitUntil:"domcontentloaded",timeout:30000});
 const r=await p.evaluate(()=>({url:location.href,title:document.title,headings:[...document.querySelectorAll("h1,h2,h3")].map(n=>n.textContent.trim()),text:document.body.innerText.slice(0,7000)}));
 sources.push(r);
}
const fs=await import("node:fs/promises");
await fs.writeFile("D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/rebuild-roadmap-nasa-method.json",JSON.stringify({sources,scope:"primary public methodological reference, not aircraft validation"},null,2)+"\n");
await p.goto("http://127.0.0.1:8776/a321-quality/report.html",{waitUntil:"domcontentloaded",timeout:30000});
console.log(sources.map(s=>({title:s.title,headings:s.headings})));
