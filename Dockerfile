# Use the official Python image as the base image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file to the container
COPY requirements.txt .


# Install the project dependencies
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8400

# Set the environment variables
ENV DJANGO_SETTINGS_MODULE=taskscheduler.settings
ENV PYTHONPATH=/app

# Start the Gunicorn web server
CMD ["gunicorn", "taskscheduler.wsgi:application", "--bind", "0.0.0.0:8400"]
