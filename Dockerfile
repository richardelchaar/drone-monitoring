# Use the official Python image
FROM python:3.9-slim


# Set the working directory inside the container
WORKDIR /app

# Copy the entire scripts folder into the container
COPY scripts/ /app/

# Install the required Python libraries
RUN pip install kafka-python

# Define the default command to run the data generator
CMD ["python", "drone_simulator.py"]
