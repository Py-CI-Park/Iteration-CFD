const task=await taskSpace(13),p=task.page("p1");
console.log(await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");
 return {state:getViewerApi().getState(), text:document.body.innerText.slice(-2600)};
}));
const r=await p.fetch("/api/datasets/open",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({
 path:"research/a321-quality/artifacts/snappy-04/native-layer-diagnostic.vtu",field:"native_layer_count"})});
console.log(r.body);
