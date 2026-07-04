FROM python:3.10-slim

# Set the current working directory inside the container
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything from your local directory explicitly into the current WORKDIR (.)
COPY . .

EXPOSE 80

# Run python directly on main.py which is now guaranteed to sit right in /app
CMD ["python", "main.py"]