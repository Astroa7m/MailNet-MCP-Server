FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Run as an unprivileged user. This process decrypts every user's OAuth tokens
# and handles attachment bytes from third parties, so it should not be root.
RUN useradd -r -u 10001 -m appuser && chown -R appuser /app
USER appuser

EXPOSE 9111
CMD ["python", "-m", "mcp_launcher.server"]
