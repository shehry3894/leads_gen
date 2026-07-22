FROM python:3.11-slim

WORKDIR /app

# Install uv up front (rarely changes → cached layer)
RUN pip install --no-cache-dir uv

# Copy the project and install dependencies from pyproject.toml
COPY . .
RUN uv pip install --system --no-cache-dir .

EXPOSE 8501

ENV STREAMLIT_SERVER_HEADLESS=true

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
