# Step 1: Use the official Python base image
FROM python:3.9-slim

# Step 2: Set the working directory
WORKDIR /app

# Step 3: Copy the current directory's code into the container
COPY . /app

# Step 4: Install dependencies (Flask and requests must be installed)
RUN pip install --no-cache-dir flask requests

# Step 5: Expose the Flask service port
EXPOSE 5000

# Step 6: Define the container startup command
CMD ["python", "app.py"]
