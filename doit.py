#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import argparse
import multiprocessing
import psutil
import logging
import logging.handlers
import time
import os

import pympler.asizeof


def setup_logger(stderr_log_lvl):
    """
    Create logger that logs to both stderr and log file but with different log level
    """
    # Remove all handlers from root logger if any
    logging.basicConfig(level=logging.NOTSET, handlers=[])
    # Change root logger level from WARNING (default) to NOTSET in order for all messages to be delegated.
    logging.getLogger().setLevel(logging.NOTSET)

    # Log message format
    formatter = logging.Formatter(
        "%(asctime)s %(name)s %(processName)s %(threadName)s %(levelname)s %(message)s"
    )
    formatter.converter = time.gmtime

    # Add stderr handler, with level INFO
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(stderr_log_lvl)
    logging.getLogger("root").addHandler(console)

    # Add file rotating handler, with level DEBUG
    rotating_handler = logging.handlers.RotatingFileHandler(
        filename="/tmp/resources-burner.log",
        maxBytes=100 * 1000,
        backupCount=2,
    )
    rotating_handler.setLevel(logging.DEBUG)
    rotating_handler.setFormatter(formatter)
    logging.getLogger().addHandler(rotating_handler)

    return logging.getLogger("root")


def child(**kwargs):
    logger = logging.getLogger("child")
    logger.debug(f"Started child with {kwargs}")

    store = []
    store_once = " " * kwargs["memory_load"]

    if kwargs["disk_write_load"] > 0:
        write_load = b" " * kwargs["disk_write_load"]
        write_path = kwargs["disk_write_destination"].replace("{i}", str(kwargs["iteration"])).replace("{p}", str(kwargs["process"]))
        write_fd = open(write_path, "wb", buffering=kwargs["disk_buffer"])

    if kwargs["disk_read_load"] > 0:
        read_load = bytearray(kwargs["disk_read_load"])
        read_path = kwargs["disk_read_source"].replace("{i}", str(kwargs["iteration"])).replace("{p}", str(kwargs["process"]))
        read_fd = open(read_path, "rb", buffering=kwargs["disk_buffer"])
        assert os.path.getsize(kwargs["disk_read_source"]) > 0, "File to read have to have size > 0"

    loop = 0
    while loop < kwargs["loops"]:
        # This simulates some actual CPU workload
        inner = 0
        while inner < kwargs["cpu_load"]:
            inner += 1

        # This simulates some actual consumed memory
        # store.append(store_once)   # no copy if reusing the same string!
        store.append((str(loop) + store_once)[:kwargs["memory_load"]])

        # This simulated some actual disk write activity
        if kwargs["disk_write_load"] > 0:
            write_fd.write(write_load)

        # This simulated some actual disk read activity
        if kwargs["disk_read_load"] > 0:
            remaining = kwargs["disk_read_load"]
            while remaining > 0:
                read = read_fd.readinto(read_load)
                remaining -= read
                if read == 0:
                    logger.debug("Skipping to the beginning of the read file")
                    read_fd.seek(0)

        loop += 1

    if kwargs["disk_write_load"] > 0:
        write_fd.close()
    if kwargs["disk_read_load"] > 0:
        read_fd.close()

    self_process = multiprocessing.current_process()
    psutil_process = psutil.Process(self_process.pid)

    psutil_cpuinfo = psutil_process.cpu_times()
    logging.info(f"CPU stats: {psutil_cpuinfo}")

    psutil_meminfo = psutil_process.memory_info()
    storage_size = pympler.asizeof.asizeof(store)
    logging.info(f"Memory stats: {psutil_meminfo} (storage: {storage_size})")

    psutil_ioinfo = psutil_process.io_counters()
    logging.info(f"IO stats: {psutil_ioinfo}")


def spawn(args, iteration):
    logger = logging.getLogger("spawn")
    processes_list = list()
    kwargs = {
        "iteration": iteration,
        "loops": args.loops,
        "cpu_load": args.cpu_load,
        "memory_load": args.memory_load,
        "disk_write_load": args.disk_write_load,
        "disk_write_destination": args.disk_write_destination,
        "disk_read_load": args.disk_read_load,
        "disk_read_source": args.disk_read_source,
        "disk_buffer": args.disk_buffer,
    }
    for i in range(args.processes):
        kwargs.update({"process": i})
        p = multiprocessing.Process(target=child, kwargs=kwargs)
        p.start()
        processes_list.append(p)
        logger.debug(f"Started process {p}")
    logger.info("All processes started")

    for p in processes_list:
        p.join()
        if p.exitcode != 0:
            logger.error(f"Process {p} failed with exit code {p.exitcode}")
        else:
            logger.info(f"Finished process {p} with exit code {p.exitcode}")
    logger.info("All processes finished")


def main():
    n_cpus = psutil.cpu_count()
    meminfo = psutil.virtual_memory()

    parser = argparse.ArgumentParser(
        prog="Resources Burner",
        description="Just burn resources",
    )
    parser.add_argument(
        "--iterations",
        help="How many times to do all of this, use -1 to do it indefinetely",
        default=1,
        type=int,
    )
    parser.add_argument(
        "--processes",
        help="How many processes to start",
        default=n_cpus,
        type=int,
    )
    parser.add_argument(
        "--loops",
        help="How many loops to perform per process",
        default=10**5,
        type=int,
    )
    parser.add_argument(
        "--cpu-load",
        help="How many iterations should inner loop do per loop per process",
        default=1000,
        type=int,
    )
    parser.add_argument(
        "--memory-load",
        help="How many bytes to store per loop per process",
        default=10000,
        type=int,
    )
    parser.add_argument(
        "--disk-write-load",
        help="How many bytes to write to the disk per loop per process, use 0 to disable",
        default=0,
        type=int,
    )
    parser.add_argument(
        "--disk-write-destination",
        help="File name template to write to, use '{i}' for iteration and '{p}' for process",
        default="/var/tmp/resources-burner-writes-{i}-{p}.data",
        type=str,
    )
    parser.add_argument(
        "--disk-read-load",
        help="How many bytes to read from the disk per loop per process, use 0 to disable",
        default=0,
        type=int,
    )
    parser.add_argument(
        "--disk-read-source",
        help="File name template to to read from, use '{i}' for iteration and '{p}' for process, you can create file with: dd if=/dev/urandom of=... bs=... count=...",
        default="/var/tmp/resources-burner-reads.data",
        type=str,
    )
    parser.add_argument(
        "--disk-buffer",
        help="Open function buffer. -1 to use default, 0 to turn it off.",
        default=-1,
        type=int,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Verbose output",
        action="store_true",
    )
    parser.add_argument(
        "-d",
        "--debug",
        help="Debug output",
        action="store_true",
    )
    args = parser.parse_args()

    if args.debug:
        logger = setup_logger(logging.DEBUG)
    elif args.verbose:
        logger = setup_logger(logging.INFO)
    else:
        logger = setup_logger(logging.WARNING)

    logger.debug(f"Args: {args}")

    logger.info(f"CPUs available={n_cpus}")
    logger.info(
        f"Memory total={meminfo.total} available={meminfo.available} percent={meminfo.percent}"
    )

    if args.iterations == -1:
        i = 0
        while True:
            logging.debug(f"Starting iteration {i}")
            spawn(args=args, iteration=i)
            i += 1
    else:
        for i in range(args.iterations):
            logging.debug(f"Starting iteration {i} of {args.iterations}")
            spawn(args=args, iteration=i)


if __name__ == "__main__":
    main()
