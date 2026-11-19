"""Run the engine's test suite across the machine's cores.

    python tools/run_tests.py                          (from 50_ENGINE)
    python tools/run_tests.py --jobs 8
    python tools/run_tests.py test_style.py test_checklist.py

`python -m unittest discover -s tests` runs every file one after another in
one process: twenty-six minutes on a machine with sixteen threads, fifteen
of them idle. This runs each file in a process of its own, as many at a time as
`--jobs` says (the core count unless told), and gathers what they report
into one summary: the tests run, every failure with its output, and the
slowest files. The discover command still works and stays the fallback; the
two run the same tests, and the count each reports is the check.

Each process loads its file the way discover does, from the same start
folder with the same top-level folder, so `_fixture` imports as it does
there and a file's count here is its count there. Each process builds its
own sandboxes, as each already did in its own `tempfile.mkdtemp` folder, and
each browser opens its own profile on a port the system picks, so nothing a
test makes is shared between processes. A file that alone would outlast the
rest of the run is split by its tests into several processes (`SPLIT`),
each loading the whole file and running its part. A file that cannot share
the machine runs after the others, alone (`SERIAL`, empty while no file
needs it).

The longest go first, by the times the last run took, which are kept in the
temporary folder (`TIMES`) and never in the repository; a file with no time
yet goes first of all, since it may be the long one.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ENGINE = Path(__file__).resolve().parents[1]
TESTS = ENGINE / "tests"

#: discover's own default, so a file named `testsomething.py` is not left out here.
PATTERN = "test*.py"

#: Files run as several processes: each tuple is a process of its own, and
#: one more runs every test no tuple names, so a test added or renamed still
#: runs. A name is a test class, or one test of a class (`TestJoin.test_x`)
#: where a class alone outlasts the rest of the run; a class split that way
#: runs its `setUpClass` in each process that takes a part of it. A name the
#: file no longer has fails the run rather than leaving the split to drift.
#: Chosen by the times the classes take, which their test counts do not tell.
SPLIT: Dict[str, Tuple[Tuple[str, ...], ...]] = {
    # Seconds alone on 2026-10-27, against the rest of each file: these were
    # the five files still running at the end of the first run, sixteen at
    # a time, where every file took about three times its time alone.
    "test_compose.py": (("TestAssembleEndpoints",),),                 # 67 against 30
    "test_drawing_dropped.py": (("TestTheSameAsTheCommand",),),       # 46 against 58
    "test_importer_and_app.py": (("TestStaticSiteExport",),),         # 48 against 49
    "test_source_editors.py": (("TestEntitySourceEditor",),),         # 52 against 47
    # One class, nineteen tests, each building a seeded sandbox of its own:
    # 53, 53 and the rest 53, of the 159 the file takes alone.
    "test_join.py": (
        ("TestJoin.test_the_change_is_a_picture_of_the_new_among_the_faded",
         "TestJoin.test_with_correct_the_change_picture_shows_what_would_be_corrected",
         "TestJoin.test_a_correction_to_what_a_shape_made_goes_under_the_products_overrides",
         "TestJoin.test_the_picture_from_the_command_and_the_door",
         "TestJoin.test_an_owner_of_the_estate_takes_the_placeholders_place"),
        ("TestJoin.test_a_workbook_of_the_pictures_comes_back_corrected",
         "TestJoin.test_a_row_the_estate_has_among_several_is_recorded_and_corrects_nothing",
         "TestJoin.test_with_correct_a_differing_cell_is_written_into_the_records_own_file",
         "TestJoin.test_a_corrected_connection_is_a_heavy_line_between_its_ends",
         "TestJoin.test_with_correct_a_relation_rows_qualifier_takes_the_sketchs",
         "TestJoin.test_a_page_of_the_estates_own_view_on_a_subject_is_not_a_view_to_add"),
    ),
}

#: Files that run after the pool, one at a time, with why.
SERIAL: Dict[str, str] = {}

#: The last run's time for each process, read to put the longest first.
TIMES = Path(tempfile.gettempdir()) / "terrane-test-times.json"

#: How a worker's result reaches the runner: the last line of its output.
MARK = "@@terrane-test-result "


def _flat(suite) -> List[unittest.TestCase]:
    out: List[unittest.TestCase] = []
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            out.extend(_flat(test))
        else:
            out.append(test)
    return out


def _names(test: unittest.TestCase) -> set:
    cls = type(test).__name__
    return {cls, "%s.%s" % (cls, getattr(test, "_testMethodName", ""))}


def _share(suite, name: str, index: int) -> unittest.TestSuite:
    """The part of a file one share runs: the tests `SPLIT` names for it,
    or, for the last share, every test it does not name."""
    tests = _flat(suite)
    named = SPLIT[name]
    twice = [test.id() for test in tests if sum(1 for share in named if set(share) & _names(test)) > 1]
    if twice:
        raise SystemExit("SPLIT gives %s to two processes of %s" % (", ".join(twice), name))
    if index < len(named):
        wanted = set(named[index])
        keep = [test for test in tests if wanted & _names(test)]
        missing = wanted - set().union(*(_names(test) for test in keep))
        if missing:
            raise SystemExit("SPLIT names %s, which %s does not have" % (", ".join(sorted(missing)), name))
    else:
        taken = {one for share in named for one in share}
        keep = [test for test in tests if not taken & _names(test)]
    # A flat suite in the file's own order: unittest runs setUpModule and
    # each class's setUpClass as the first test of each comes up.
    return unittest.TestSuite(keep)


def worker(name: str, shard: str, verbosity: int) -> int:
    # As `python -m unittest` would have it: the working folder first on the
    # path where this script's own folder was, and output that cannot fail
    # to encode, since a pipe is not the console and Windows gives a pipe
    # its code page, which has no arrow for a test to print.
    sys.path[0] = str(ENGINE)
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    suite = unittest.TestLoader().discover(str(TESTS), pattern=name, top_level_dir=str(TESTS))
    if shard:
        suite = _share(suite, name, int(shard.split("/")[0]) - 1)
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=verbosity).run(suite)
    sys.stderr.flush()
    report = {"run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "skipped": len(result.skipped), "expected_failures": len(result.expectedFailures),
              "unexpected_successes": len(result.unexpectedSuccesses), "ok": result.wasSuccessful()}
    print(MARK + json.dumps(report), flush=True)
    return 0 if result.wasSuccessful() else 1


class Job:
    def __init__(self, name: str, shard: str = "") -> None:
        self.name, self.shard = name, shard
        self.label = "%s [%s]" % (name, shard) if shard else name
        self.seconds = 0.0
        self.output = ""
        self.report: Optional[dict] = None
        self.problem = ""

    def argv(self, verbosity: int) -> List[str]:
        argv = [sys.executable, str(Path(__file__).resolve()), "--worker", self.name, "--verbosity", str(verbosity)]
        return argv + (["--shard", self.shard] if self.shard else [])

    @property
    def ok(self) -> bool:
        return bool(self.report and self.report["ok"]) and not self.problem


_LIVE: Dict[int, subprocess.Popen] = {}
_LIVE_LOCK = threading.Lock()
_STOP = threading.Event()


def _kill_tree(proc: subprocess.Popen) -> None:
    """End a worker and what it started: a browser left behind holds its
    profile folder, and on Windows a killed parent leaves its children."""
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass


def run(job: Job, verbosity: int, timeout: float) -> Job:
    start = time.perf_counter()
    extra = {} if os.name == "nt" else {"start_new_session": True}
    with _LIVE_LOCK:
        # Under the lock, so a stop cannot fall between the check and the start.
        if _STOP.is_set():
            job.problem = "not started"
            return job
        proc = subprocess.Popen(job.argv(verbosity), cwd=str(ENGINE), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, **extra)
        _LIVE[proc.pid] = proc
    try:
        raw, _ = proc.communicate(timeout=timeout or None)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        raw, _ = proc.communicate()
        job.problem = "still running after %d seconds, stopped" % timeout
    finally:
        with _LIVE_LOCK:
            _LIVE.pop(proc.pid, None)
    job.seconds = time.perf_counter() - start
    text = raw.decode("utf-8", errors="replace").replace("\r\n", "\n")
    lines = text.rstrip("\n").split("\n")
    if lines and lines[-1].startswith(MARK):
        job.report = json.loads(lines[-1][len(MARK):])
        text = "\n".join(lines[:-1]) + "\n"
    elif not job.problem:
        # No result line: the process ended before unittest finished, and
        # how many tests it ran is not known, so the total is not either.
        job.problem = "ended with exit code %s before reporting a result" % proc.returncode
    job.output = text
    return job


def _clock(seconds: float) -> str:
    minutes, rest = divmod(int(round(seconds)), 60)
    return "%dm %02ds" % (minutes, rest) if minutes else "%.1fs" % seconds


def _count(n: int, one: str, many: str = "") -> str:
    return "%d %s" % (n, one if n == 1 else (many or one + "s"))


def _remembered() -> Dict[str, float]:
    try:
        data = json.loads(TIMES.read_text(encoding="utf-8"))
        return {str(k): float(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _remember(jobs: List[Job]) -> None:
    times = _remembered()
    times.update({job.label: round(job.seconds, 1) for job in jobs if job.report and not job.problem})
    # Two runs at once (two worktrees) each write whole files, never half of one.
    scratch = TIMES.with_name("%s.%d" % (TIMES.name, os.getpid()))
    try:
        scratch.write_text(json.dumps(times, indent=0, sort_keys=True), encoding="utf-8")
        os.replace(scratch, TIMES)
    except OSError:
        pass


def plan(names: List[str]) -> Tuple[List[Job], List[Job]]:
    pool: List[Job] = []
    tail: List[Job] = []
    for name in names:
        count = len(SPLIT[name]) + 1 if name in SPLIT else 1
        jobs = [Job(name, "%d/%d" % (i, count)) for i in range(1, count + 1)] if count > 1 else [Job(name)]
        (tail if name in SERIAL else pool).extend(jobs)
    times = _remembered()
    pool.sort(key=lambda job: (job.label in times, -times.get(job.label, 0.0), -(TESTS / job.name).stat().st_size))
    return pool, tail


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the engine's tests, a file per process, across the cores.")
    parser.add_argument("files", nargs="*", help="test files to run (default: every %s in tests/)" % PATTERN)
    parser.add_argument("--jobs", "-j", type=int, default=os.cpu_count() or 1,
                        help="processes at a time (default: the core count, %(default)s)")
    parser.add_argument("--timeout", type=float, default=1800,
                        help="seconds one process may take before it is stopped and failed (default: %(default)s)")
    parser.add_argument("--verbose", "-v", action="store_true", help="print each file's output as it finishes, every test by name")
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    parser.add_argument("--shard", default="", help=argparse.SUPPRESS)
    parser.add_argument("--verbosity", type=int, default=1, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker:
        return worker(args.worker, args.shard, args.verbosity)
    # A failure's output goes to a log file as often as to a console, and a
    # log file takes the code page unless told otherwise.
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

    every = sorted(p.name for p in TESTS.glob(PATTERN) if p.is_file())
    names = [Path(f).name for f in args.files] or every
    unknown = [name for name in names if name not in every]
    if unknown:
        parser.error("no such test file in %s: %s" % (TESTS, ", ".join(unknown)))
    pool, tail = plan(names)
    total = len(pool) + len(tail)
    verbosity = 2 if args.verbose else 1
    jobs_at_once = max(1, args.jobs)
    print("%s, %s, %d at a time%s" % (_count(len(names), "file"), _count(total, "process", "processes"),
                                     jobs_at_once, ", then %d alone" % len(tail) if tail else ""), flush=True)

    done: List[Job] = []
    lock = threading.Lock()

    def finished(job: Job) -> None:
        with lock:
            done.append(job)
            ran = job.report["run"] if job.report else 0
            status = "ok" if job.ok else ("FAIL" if job.report else "LOST")
            print("[%3d/%d] %-4s %5d tests %8s  %s" % (len(done), total, status, ran, _clock(job.seconds), job.label),
                  flush=True)
            if args.verbose and job.ok:
                # A failure's output is printed in the summary, once.
                print(job.output.rstrip("\n"), flush=True)

    start = time.perf_counter()
    # Not `with`: leaving that block waits for every queued file to run,
    # so Ctrl+C would have stopped nothing.
    executor = ThreadPoolExecutor(max_workers=jobs_at_once)
    try:
        futures = [executor.submit(run, job, verbosity, args.timeout) for job in pool]
        for future in as_completed(futures):
            finished(future.result())
        executor.shutdown()
        for job in tail:
            finished(run(job, verbosity, args.timeout))
    except KeyboardInterrupt:
        _STOP.set()
        executor.shutdown(wait=False, cancel_futures=True)
        with _LIVE_LOCK:
            live = list(_LIVE.values())
        for proc in live:
            _kill_tree(proc)
        print("\nstopped; %d of %d processes had finished" % (len(done), total))
        return 130
    wall = time.perf_counter() - start
    _remember(done)
    return summary(done, wall, jobs_at_once, len(names))


def summary(done: List[Job], wall: float, jobs_at_once: int, files: int) -> int:
    failed = [job for job in done if not job.ok]
    for job in sorted(failed, key=lambda job: job.label):
        print("\n" + "=" * 70)
        print("%s: %s" % (job.label, job.problem or "failed"))
        print("=" * 70)
        print(job.output.rstrip("\n"))
    counts = {key: sum(job.report[key] for job in done if job.report)
              for key in ("run", "failures", "errors", "skipped", "expected_failures", "unexpected_successes")}
    slowest = sorted(done, key=lambda job: -job.seconds)[:10]
    print("\nSlowest:")
    for job in slowest:
        print("  %8s  %s" % (_clock(job.seconds), job.label))
    print("-" * 70)
    print("Ran %d tests in %.3fs" % (counts["run"], wall))
    print("%s in %s, %d at a time: %s; one after another they took %s" % (
        _count(files, "file"), _count(len(done), "process", "processes"), jobs_at_once, _clock(wall),
        _clock(sum(job.seconds for job in done))))
    lost = [job for job in done if not job.report or job.problem]
    if lost:
        print("NOT COUNTED: %s" % "; ".join("%s %s" % (job.label, job.problem) for job in lost))
    details = ["%s=%d" % (key, counts[key]) for key in ("failures", "errors") if counts[key]]
    details += ["%s=%d" % (key.replace("_", " "), counts[key])
                for key in ("skipped", "expected_failures", "unexpected_successes") if counts[key]]
    print()
    print(("FAILED" if failed else "OK") + (" (%s)" % ", ".join(details) if details else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
