const task=await taskSpace(12),p=task.page("p1");
const base="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p1").targetId});
await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
await p.cdp("Page.bringToFront");
for(const [file,label] of [["research/a321-integration/models/A321_AIRFRAME_SHELL_R3.stl","r3"],["research/a321-quality/artifacts/snappy-03/calculation-wall-v5.stl","wall"]]){
 await p.click('loc=css:[data-tab-id="geometry:'+file+'"]');
 const xy=await p.evaluate(()=>{
  const c=[...document.querySelectorAll("canvas")].find(c=>c.clientWidth>200&&c.getBoundingClientRect().width>200);
  const r=c.getBoundingClientRect();
  return [r.x+r.width*.52,r.y+r.height*.57];
 });
 await p.mouse.move(xy[0],xy[1],{label:"Center aircraft camera zoom"});
 await p.mouse.wheel(0,-530,{label:"Zoom aircraft for comparison"});
 await p.screenshot({path:base+"/studio-20261107-"+label+".png"});
}
await p.click('loc=css:[data-testid="tab-viewer"]');
console.log((await p.snapshot()).split("\n").filter(s=>s.includes("462,113")).slice(0,2));
