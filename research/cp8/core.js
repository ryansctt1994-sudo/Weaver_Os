function CP8CoreFactory() {
  function verify(path,n) {
    if(!Number.isInteger(n)||n<3||n>10||!Array.isArray(path)||path.length===0||path.length>(1<<n))
      return {ok:false,reason:'INVALID STRUCTURE'};
    const seen=new Set(), dist=(a,b)=>{let x=a^b,k=0;while(x){x&=x-1;k++}return k};
    for(let i=0;i<path.length;i++){
      const v=path[i];
      if(!Number.isInteger(v)||v<0||v>=(1<<n))return {ok:false,index:i,reason:'STATE OUT OF RANGE'};
      if(seen.has(v))return {ok:false,index:i,reason:'REPEATED STATE'};seen.add(v);
      if(i&&dist(path[i-1],v)!==1)return {ok:false,index:i,reason:'NOT ADJACENT'};
      for(let j=0;j<i-1;j++)if(dist(path[j],v)===1)return {ok:false,index:i,other:j,reason:'CHORD'};
    }
    return {ok:true,vertices:path.length,edges:path.length-1,reason:'INDUCED PATH VERIFIED'};
  }
  function canonicalize(o){
    if(Array.isArray(o))return o.map(canonicalize);
    if(o&&typeof o==='object'){const x=Object.create(null);Object.keys(o).sort().forEach(k=>x[k]=canonicalize(o[k]));return x}
    return o;
  }
  async function validateImport(o,digest){
    if(!o||o.schema!=='asin-hhc.cp8.snake-proof.v1.1')throw Error('SCHEMA');
    const n=o.dimension,path=o.path_decimal,vr=verify(path,n);
    if(!vr.ok)throw Error(vr.reason);
    if(o.path_vertices!==path.length||o.path_edges!==path.length-1||o.state_space_vertices!==(1<<n))throw Error('COUNTS');
    if(!Array.isArray(o.path_binary)||o.path_binary.length!==path.length||
      o.path_binary.some((v,i)=>v!==path[i].toString(2).padStart(n,'0')))throw Error('BINARY REPRESENTATION');
    const seal=o.content_seal;
    if(!seal||seal.algorithm!=='SHA-256'||seal.canonicalization!=='recursive_key_sort_compact_json_excluding_content_seal'||
       !/^[a-f0-9]{64}$/.test(seal.digest))throw Error('REQUIRED SEAL');
    const unsigned={...o};delete unsigned.content_seal;
    if(await digest(JSON.stringify(canonicalize(unsigned)))!==seal.digest)throw Error('SEAL MISMATCH');
    return {n,path:[...path],seal:seal.digest,verification:vr};
  }
  async function importInto(state,o,digest){
    const c=await validateImport(o,digest);
    return {...state,n:c.n,path:c.path,best:[...c.path],seal:c.seal,imported:true};
  }
  function search(n,budget,seed=1,strategy='baseline',onBest=()=>{}){
    if(!Number.isInteger(n)||n<3||n>10||!Number.isSafeInteger(budget)||budget<0||budget>1000000||
       !Number.isInteger(seed)||seed<0||seed>0xffffffff||!['baseline','cp8_phi'].includes(strategy))throw Error('SEARCH INPUT');
    const visited=new Uint8Array(1<<n),path=[0];visited[0]=1;
    let nodes=0,best=[0],rng=seed>>>0||1;
    const rand=()=>{rng^=rng<<13;rng^=rng>>>17;rng^=rng<<5;return (rng>>>0)/4294967296};
    function options(v){
      const out=[];
      for(let b=0;b<n;b++){
        const u=v^(1<<b);if(visited[u])continue;
        let count=0;for(let k=0;k<n;k++)count+=visited[u^(1<<k)];if(count!==1)continue;
        let onward=0;
        for(let k=0;k<n;k++){const z=u^(1<<k);if(visited[z])continue;let c=0;for(let j=0;j<n;j++)c+=visited[z^(1<<j)];if(c===1)onward++}
        out.push({u,onward,tie:strategy==='cp8_phi'?(((u+1)*137.507764+path.length*111)%360)/360:rand()});
      }
      return out.sort((a,b)=>a.onward-b.onward||a.tie-b.tie||a.u-b.u).map(a=>a.u);
    }
    const stack=[{opts:options(0),idx:0}];
    while(stack.length&&nodes<budget){
      nodes++;const top=stack.at(-1);
      if(top.idx>=top.opts.length){stack.pop();if(path.length>1)visited[path.pop()]=0;continue}
      const u=top.opts[top.idx++];visited[u]=1;path.push(u);
      if(path.length>best.length){best=[...path];onBest(best,nodes)}
      stack.push({opts:options(u),idx:0});
    }
    return {dimension:n,path:best,nodes,budget,seed,strategy,exhaustive:stack.length===0,optimality_claim:false};
  }
  return {verify,canonicalize,validateImport,importInto,search};
}
const CP8Core=CP8CoreFactory();
if(typeof module!=='undefined')module.exports=CP8Core;

