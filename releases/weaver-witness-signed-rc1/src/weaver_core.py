from dataclasses import dataclass,asdict
import hashlib,json
def sha(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()
@dataclass(frozen=True)
class Command:
 command_id:str; actor:str; target:str; action:str; experiment_id:str; nonce:str; authorized:bool
class Chronicle:
 def __init__(self): self.entries=[]
 def append(self,event):
  prev=self.entries[-1]["entry_hash"] if self.entries else "GENESIS"
  body={"index":len(self.entries),"prev_hash":prev,"event":event}
  e={**body,"entry_hash":sha(body)}; self.entries.append(e); return e
 @staticmethod
 def verify(es):
  prev="GENESIS"
  for i,e in enumerate(es):
   body={"index":i,"prev_hash":prev,"event":e["event"]}
   if e.get("index")!=i or e.get("prev_hash")!=prev or e.get("entry_hash")!=sha(body): return False
   prev=e["entry_hash"]
  return True
class Runtime:
 def __init__(self,eid="WN-WITNESS-001"):
  self.experiment_id=eid; self.protected={"counter":0}; self.used=set(); self.chronicle=Chronicle()
 def state_hash(self): return sha(self.protected)
 def execute(self,c):
  before=self.state_hash(); reasons=[]
  if c.experiment_id!=self.experiment_id: reasons+=["experiment_mismatch"]
  if c.target!="protected.counter": reasons+=["target_mismatch"]
  if c.action!="increment": reasons+=["action_mismatch"]
  if not c.authorized: reasons+=["unauthorized"]
  if c.command_id in self.used: reasons+=["replay"]
  v="REJECT" if reasons else "ACCEPT"
  if v=="ACCEPT": self.protected["counter"]+=1; self.used.add(c.command_id)
  after=self.state_hash()
  e=self.chronicle.append({"command":asdict(c),"verdict":v,"reasons":reasons,"state_before":before,"state_after":after})
  b={"experiment_id":self.experiment_id,"command_id":c.command_id,"entry_hash":e["entry_hash"],"verdict":v,"state_before":before,"state_after":after}
  return v,{**b,"receipt_hash":sha(b)}
def verify_receipt(r,es):
 h=r.get("receipt_hash"); b={k:v for k,v in r.items() if k!="receipt_hash"}
 if h!=sha(b) or not Chronicle.verify(es): return False
 return any(e["entry_hash"]==r["entry_hash"] and e["event"]["command"]["command_id"]==r["command_id"] and e["event"]["command"]["experiment_id"]==r["experiment_id"] and e["event"]["verdict"]==r["verdict"] and e["event"]["state_before"]==r["state_before"] and e["event"]["state_after"]==r["state_after"] for e in es)
