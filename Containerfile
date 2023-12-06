FROM registry.access.redhat.com/ubi9/python-311

# Add application sources with correct permissions for OpenShift
USER 0
ADD doit.py requirements.txt .
RUN chown -R 1001:0 ./
USER 1001

# Install requirements
RUN pip install -U pip \
    && pip install --no-cache-dir -r requirements.txt

# Run the workload during build
RUN python doit.py --iterations 1 --processes 8 --counting 1000000 --storing 100 -d

# Run the workload indefinetely at container run time
CMD python doit.py --iterations -1 --processes 1 --counting 10000 --storing 1000 -v
