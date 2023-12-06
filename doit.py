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


def child(counting, storing):
    store = []
    store_once = " " * storing
    counter = 0
    while counter < counting:
        # This simulates some actual workload
        inner = 0
        while inner < 1000:
            inner += 1

        counter += 1
        # store.append(store_once)   # no copy if reusing the same string!
        store.append((str(counter) + store_once)[:storing])

    self_process = multiprocessing.current_process()
    psutil_process = psutil.Process(self_process.pid)
    psutil_meminfo = psutil_process.memory_info()
    storage_size = pympler.asizeof.asizeof(store)
    logging.info(
        f"Used memory {psutil_meminfo} and storage itself had {storage_size} B"
    )


def spawn(processes, counting, storing):
    logger = logging.getLogger("spawn")
    processes_list = list()
    for _ in range(processes):
        p = multiprocessing.Process(
            target=child, kwargs={"counting": counting, "storing": storing}
        )
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
        "--inner",
        help="How many loops should inner loop do",
        default=1000,
        type=int,
    )
    parser.add_argument(
        "--counting",
        help="How many loops to perform per process",
        default=10**5,
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
        while True:
            spawn(
                processes=args.processes, counting=args.counting, storing=args.storing
            )
    else:
        for i in range(args.iterations):
            logging.debug(f"Starting iteration {i}")
            spawn(
                processes=args.processes, counting=args.counting, storing=args.storing
            )


if __name__ == "__main__":
    main()
