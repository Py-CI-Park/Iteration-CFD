// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
const task=await taskSpace(10),p=task.page("p2");
await p.goto("https://www.grc.nasa.gov/www/wind/valid/tutorial/tutorial.html",{waitUntil:"domcontentloaded",timeout:30000});
const result=await p.evaluate(()=>({url:location.href,title:document.title,headings:[...document.querySelectorAll("h1,h2,h3")].map(n=>n.textContent),intro:document.body.innerText.slice(0,800)}));
const fs=await import("node:fs/promises");
await fs.writeFile("D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/smooth-study-nasa-source.json",JSON.stringify(result,null,2)+"\n");
await p.goto("http://127.0.0.1:8776/a321-quality/report.html",{waitUntil:"domcontentloaded",timeout:30000});
console.log({url:result.url,title:result.title,headings:result.headings.slice(0,10)});
