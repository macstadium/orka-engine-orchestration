FROM semaphoreui/semaphore:latest

USER root

RUN apk add --no-cache sshpass

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

RUN mkdir -p /home/semaphore/.cache/ansible_facts

USER semaphore
