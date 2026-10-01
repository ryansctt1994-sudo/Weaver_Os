import json,sys
from weaver_core import *
p=json.load(open(sys.argv[1])); c=Command(**p["cmd"]); r=Runtime(c.experiment_id); v,x=r.execute(c)
print(json.dumps({"verdict":v,"state_hash":x["state_after"]},sort_keys=True))
