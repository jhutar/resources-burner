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
RUN for p in $( seq 0 7 ); do dd if=/dev/urandom of=./resources-burner-reads-$p.data bs=16384 count=64; done \
    && python doit.py --iterations 1 --processes 8 --loops 500000 --memory-load 200 --disk-write-load 20 --disk-write-destination ./resources-burner-writes-{i}-{p}.data --disk-read-load 20 --disk-read-source ./resources-burner-reads-{p}.data -d \
    && rm -rf ./resources-burner-reads-*.data \
    && ls -alh

# Run the workload indefinetely at container run time
CMD python doit.py --iterations -1 --processes 1 --loops 10000 --memory-load 1000 -v
