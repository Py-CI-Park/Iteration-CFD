const task=await taskSpace(12),p=task.page("p2");
const fs=await import("node:fs/promises");
const dir="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p2").targetId});
await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
await p.cdp("Page.bringToFront");
await p.reload({waitUntil:"load"});
const check=await p.evaluate(()=>({
 title:document.title,
 rows:document.querySelector("main table tbody")?.rows.length,
 loadedImages:[...document.images].filter(i=>i.complete&&i.naturalWidth>0).length,
 imageCount:document.images.length,
 hasSourceSets:document.body.innerText.includes("underdeterminedCells"),
 hasArchive:document.querySelector(".archive h2")?.textContent?.includes("2026-11-06")
}));
if(check.rows!==8||check.loadedImages!==8||check.imageCount!==8||!check.hasSourceSets||!check.hasArchive)throw Error(JSON.stringify(check));
const qa=JSON.parse(await fs.readFile(dir+"/report-20261107-qa.json","utf8"));
await fs.writeFile(dir+"/report-20261107-qa.json",JSON.stringify({...qa,final:check},null,2)+"\n");
await p.screenshot({path:dir+"/report-20261107-desktop.png"});
console.log(check);
await task.finish({keep:["p1","p2"]});
