
from fastmcp import FastMCP
from api.main import app


mcp = FastMCP.from_fastapi(app=app, name="email_mcp")
if __name__ == "__main__":
    mcp.run()