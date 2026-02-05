FROM python:3.11-slim

WORKDIR /app

# Copy requirements.txt first to leverage caching
COPY requirements.txt .

# Install uv and project dependencies (using requirements.txt inside the container)
RUN pip install --no-cache-dir uv \
    && uv pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

EXPOSE 8501

ENV STREAMLIT_SERVER_HEADLESS=true

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
