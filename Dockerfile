FROM python:3.10-slim

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything explicitly into /app
COPY . /app

EXPOSE 80

# Run using Python directly, which looks straight at your main.py file
CMD ["python", "main.py"]