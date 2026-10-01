const assert=require('node:assert/strict'),crypto=require('node:crypto'),core=require('./core.js');
const hash=async s=>crypto.createHash('sha256').update(s).digest('hex');
async function packet(path=[0,1,3],n=3){const p={schema:'asin-hhc.cp8.snake-proof.v1.1',dimension:n,path_decimal:path,path_binary:path.map(v=>v.toString(2).padStart(n,'0')),path_vertices:path.length,path_edges:path.length-1,state_space_vertices:1<<n};return {...p,content_seal:{algorithm:'SHA-256',canonicalization:'recursive_key_sort_compact_json_excluding_content_seal',digest:await hash(JSON.stringify(core.canonicalize(p)))}}}
(async()=>{
 assert(core.verify([0,1,3],3).ok);
 for(const p of [[],[0,1,0],[0,1,3,2],[0,3],['0',1],[0,NaN],[0,8]])assert(!core.verify(p,3).ok);
 const gray=Array.from({length:256},(_,i)=>i^(i>>1));assert(!core.verify(gray,8).ok);
 const state={n:3,path:[0],seal:'old',other:{protected:7}},snapshot=JSON.stringify(state);
 for(const bad of [await packet([0,1,3,2]),{...await packet(),dimension:'3'},{...await packet(),content_seal:null},{...await packet(),path_vertices:99}]){
  await assert.rejects(core.importInto(state,bad,hash));assert.equal(JSON.stringify(state),snapshot);
 }
 const p=await packet(),next=await core.importInto(state,p,hash);assert.deepEqual(next.path,[0,1,3]);assert.equal(JSON.stringify(state),snapshot);
 const edited=JSON.parse(JSON.stringify(p));edited.path_decimal[2]=5;await assert.rejects(core.importInto(state,edited,hash));
 for(const strategy of ['baseline','cp8_phi'])for(const seed of [1,7,42])for(const budget of [0,1,50,1000]){
  const a=core.search(5,budget,seed,strategy);assert(a.nodes<=budget);assert(core.verify(a.path,5).ok);assert.deepEqual(a,core.search(5,budget,seed,strategy));
 }
 for(const n of [3,4,5,8]){
  const r=core.search(n,2000,42,'cp8_phi');assert(core.verify(r.path,n).ok);
  const perm=r.path.map(v=>{let out=0;for(let b=0;b<n;b++)if(v&(1<<b))out|=1<<(n-1-b);return out});assert(core.verify(perm,n).ok);
 }
 assert.throws(()=>core.search(8,-1));
 console.log('CP8 checks PASS: adversarial paths/imports, budget, repeatability, bit permutation');
 const results=[];for(const seed of [1,7,42])for(const strategy of ['baseline','cp8_phi']){const r=core.search(8,10000,seed,strategy);results.push({seed,strategy,budget:r.budget,nodes:r.nodes,edges:r.path.length-1,valid:core.verify(r.path,8).ok,optimality_claim:false})}
 console.log(JSON.stringify({schema:'cp8-benchmark-v0.1',results},null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
