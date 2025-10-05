# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "fastapi[standard]",
#   "unicorn",
# ]
# ///

from fastapi import FastAPI
app = FastAPI()

# post endpoint that takes json objext with follwoing fields: email, secret,task,round,nonce,breif,checks(array),evaluation_url,attachments(arrary with object and url )
@app.post("/handle_task")
async def handle_task(data:dict):
  #print the data
  print(data)
  return {"message":"Task received","data":data}



