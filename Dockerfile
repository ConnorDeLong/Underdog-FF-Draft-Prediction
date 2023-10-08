# Use an official Python runtime as the base image
FROM python:3.8-slim

# Copy the current directory (on your machine) into the container at /app
COPY . .

# Update the package lists for upgrades for packages that need upgrading, as well as new package installations
RUN apt-get update

# Install wget and unzip
RUN apt-get install -y wget unzip gnupg


# # Add Google Chrome's public key
# RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -

# # Add Google Chrome to the repository sources
# RUN echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list

# # Install Google Chrome
# RUN apt-get update && apt-get install -y google-chrome-stable

# RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
# RUN ls -l
# RUN echo "y" | dpkg -i google-chrome-stable_current_amd64.deb || apt-get install -f


# ARG CHROME_VERSION="117.0.5938.92"
# RUN wget --no-verbose -O /tmp/chrome.deb https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_${CHROME_VERSION}_amd64.deb \
#   && apt install -y /tmp/chrome.deb \
#   && rm /tmp/chrome.deb


# RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
# RUN echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list

RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
# Adding Google Chrome to the repositories
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'

# Updating apt to see and install Google Chrome
RUN apt-get -y update

# Magic happens
RUN apt-get install -y google-chrome-stable

# Install ChromeDriver
ENV CHROMEDRIVER_PATH /usr/local/bin/chromedriver
RUN wget -q https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/117.0.5938.92/linux64/chromedriver-linux64.zip -O /tmp/chromedriver-linux64.zip \
    && mv /tmp/chromedriver-linux64.zip /tmp/chromedriver.zip \
    && unzip /tmp/chromedriver.zip -d /opt/ \
    && rm /tmp/chromedriver.zip \
    && chmod +x /opt/chromedriver-linux64/chromedriver \
    && ln -fs /opt/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver

# RUN wget -q https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/117.0.5938.92/linux64/chromedriver-linux64.zip -O /tmp/chromedriver-linux64.zip
# RUN mv /tmp/chromedriver-linux64.zip /tmp/chromedriver.zip
# RUN unzip /tmp/chromedriver.zip -d /opt/
# RUN rm /tmp/chromedriver.zip
# RUN chmod +x /opt/chromedriver-linux64/chromedriver
# RUN ln -fs /opt/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver

# Install any needed packages specified in requirements.txt
RUN pip install -e .

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Set the working directory t
WORKDIR /UD_draft_model/app

# Specify the command to run on container start
CMD ["streamlit", "run", "app.py"]
