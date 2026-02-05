from mcp_launcher import server
import uvicorn
from fastapi import Request, FastAPI
app = FastAPI()


@app.post("/send_email")
async def send_email(req: Request):
    """Gets a call from the scheduler to send an email after datetime is met"""
    data = await req.json()
    await server.send_email(**data)




if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=911)
