import copy,json,subprocess,sys,tempfile,os
from pathlib import Path
from weaver_core import *
def ck(n,x): print(f"{n:.<25}{'PASS' if x else 'FAIL'}"); return x
r=Runtime(); out=[]
good=Command("C1","human","protected.counter","increment","WN-WITNESS-001","N1",True)
v1,rc1=r.execute(good); out+=[ck("AUTHORIZED",v1=="ACCEPT")]
bad=Command("C2","agent","protected.counter","increment","WN-WITNESS-001","N2",False)
h=r.state_hash(); v2,rc2=r.execute(bad); out+=[ck("UNAUTHORIZED",v2=="REJECT"),ck("STATE PRESERVED",h==r.state_hash())]
h=r.state_hash(); vr,_=r.execute(good); out+=[ck("REPLAY REJECTED",vr=="REJECT" and h==r.state_hash())]
with tempfile.NamedTemporaryFile("w",delete=False,suffix=".json") as f: json.dump({"cmd":good.__dict__},f); fn=f.name
p=subprocess.run([sys.executable,str(Path(__file__).with_name("fresh_replay.py")),fn],capture_output=True,text=True,check=True); os.unlink(fn)
fr=json.loads(p.stdout); out+=[ck("FRESH REPLAY",fr["verdict"]==v1 and fr["state_hash"]==rc1["state_after"])]
es=copy.deepcopy(r.chronicle.entries[:1]); out+=[ck("RECEIPT BASELINE",verify_receipt(rc1,es))]
x=copy.deepcopy(rc1); x["verdict"]="REJECT"; out+=[ck("RECEIPT TAMPER",not verify_receipt(x,es))]
x=copy.deepcopy(es); x[0]["event"]["verdict"]="REJECT"; out+=[ck("CHRONICLE TAMPER",not Chronicle.verify(x))]
x=copy.deepcopy(rc1); x["experiment_id"]="OTHER"; b={k:v for k,v in x.items() if k!="receipt_hash"}; x["receipt_hash"]=sha(b)
out+=[ck("IDENTITY SWAP",not verify_receipt(x,es))]
print("\nWITNESS:","PASS" if all(out) else "FAIL"); print("FINAL_STATE_HASH:",r.state_hash()); print("CHRONICLE_HEAD:",r.chronicle.entries[-1]["entry_hash"])
raise SystemExit(0 if all(out) else 1)
