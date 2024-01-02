#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import argparse
import multiprocessing
import psutil
import logging
import logging.handlers
import time

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


def child(loops, cpu_load, storing):
    logger = logging.getLogger("child")
    logger.debug(f"Started child witl loops={loops} cpu_load={cpu_load} storing={storing}")

    store = []
    store_once = " " * storing

    loop = 0
    while loop < loops:
        # This simulates some actual CPU workload
        inner = 0
        while inner < cpu_load:
            inner += 1

        # This simulates some actual consumed memory
        # store.append(store_once)   # no copy if reusing the same string!
        store.append((str(loop) + store_once)[:storing])

        loop += 1

    self_process = multiprocessing.current_process()
    psutil_process = psutil.Process(self_process.pid)
    psutil_meminfo = psutil_process.memory_info()
    storage_size = pympler.asizeof.asizeof(store)
    logging.info(
        f"Used memory {psutil_meminfo} and storage itself had {storage_size} B"
    )


def spawn(args):
    logger = logging.getLogger("spawn")
    processes_list = list()
    kwargs = {
        "loops": args.loops,
        "cpu_load": args.cpu_load,
        "storing": args.storing,
    }
    for _ in range(args.processes):
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
        "--storing",
        help="How many bytes to store per loop per process",
        default=10000,
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
            spawn(args=args)
            i += 1
    else:
        for i in range(args.iterations):
            logging.debug(f"Starting iteration {i} of {args.iterations}")
            spawn(args=args)


if __name__ == "__main__":
    main()
