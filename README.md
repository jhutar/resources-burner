Resources burner
================

This repo implements simple container that consumes resources (CPU, memory
and disk) both during build (commented out right now) and during run time.
See `./doit.py --help` for more details.


What it does
------------

 * It runs a sequence of given number of *iterations*.
   * During each iteration, given number of parallel *processes* is started.
     * Each process runs given number of *loops* and during each iteration:
       * *cpu_load* inner loops is executed to put some load on CPU.
       * *memory_load* bytes string is allocated to consume some memory (so memory consumption raises through loops).
       * *disk_write_load* bytes is written to the disk (no overwrites, target file gets bigger through loops).
       * *disk_read_load* bytes is read from the disk.
 * With debug, besides other messages, some per process metrics are printed. Log can be found in `/tmp/resources-burner.log`.


Development
-----------

You need these dependencies:

    dnf install -y python3-psutil python3-Pympler

Or if you prefer pip:

    python -m venv venv
    source venv/bin/activate
    python -m pip install psutil pympler


Build container
---------------

To build container locally:

    podman build -f Containerfile -t localhost/resources-burner:latest .

To run container locally with some cpu and memory limits (not sure if these are correct options):

    podman run --rm -ti --cpus 1 --memory 1g localhost/resources-burner:latest
