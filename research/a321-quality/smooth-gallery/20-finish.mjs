// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
const task=await taskSpace(10);
const p=task.page("p1");
const state=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");const api=getViewerApi();
 const r=await api.execute({type:"setCamera",position:[49,35,38],target:[22,0,6],projection:"perspective"});
 if(!r.ok)throw Error(JSON.stringify(r.error));return api.getState();
});
console.log({leftForUser:state.datasetName,cells:state.cellCount,report:"http://127.0.0.1:8776/a321-quality/report.html"});
await task.finish({keep:["p1","p2"]});
