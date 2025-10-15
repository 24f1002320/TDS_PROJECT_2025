# Use official Python image
FROM python:3.13.8-slim

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port (Hugging Face uses 7860 by default)
EXPOSE 7860

# Environment variable for Hugging Face Spaces
ENV PORT=7860

# Command to run the FastAPI app with uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7860"]