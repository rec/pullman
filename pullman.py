#!/bin/env python3

import argparse
import dataclasses as dc
import json
import os
import re
import stat
import subprocess
import sys
import webbrowser
from argparse import Namespace
from contextlib import nullcontext, suppress
from functools import cache, cached_property
from operator import attrgetter
from pathlib import Path
from subprocess import CalledProcessError, run
from typing import Any, Optional, Sequence


try:
    import bs4
except ImportError:
    bs4 = None
try:
    import requests
except ImportError:
    requests = None


UPDATE_SUBMODULES = "git submodule update --init --recursive"
CONFLICT_MSG = f"""
After resolving any conflicts, type:

    git rebase --continue
    {UPDATE_SUBMODULES}"
"""

DEFAULT_CACHE_PATH = Path("~/.cache/pullman/pullman.json").expanduser()
DEFAULT_OUT = "unit-test-failures.sh"

_COMMANDS = {
    "checkout": "Call `ghstack checkout` on this pull request",
    "commit_url": "Show gitub URL for the commit for this pull request",
    "errors": "Download all the errors for a pull request",
    "hud_url": "HUD URL for a pull request",
    "list": "List all pull requests",
    "ref": "Show git ref id of a pull request",
    "ref_url": "Show git ref id URL for a pull request",
    "url": "Show the URL for a pull request",
}

HELP = ""

TOKEN_NAMES = "PULL_MANAGER_GIT_TOKEN", "GIT_TOKEN"
GIT_TOKEN = next((token for n in TOKEN_NAMES if (token := os.environ.get(n))), None)

API_ROOT = "https://api.github.com/repos/pytorch/pytorch"

_PULL_PREFIX = "https://github.com/pytorch/pytorch/pull/"
_GHSTACK_SOURCE = "ghstack-source-id:"
_HUD_PREFIX = "https://hud.pytorch.org/pr/"
_PULL_REQUEST_RESOLVED = "Pull Request resolved:"
_REF_PREFIX = "https://github.com/pytorch/pytorch/tree/"
_COMMIT_PREFIX = "https://github.com/pytorch/pytorch/commit/"

FIELDS = "is_open", "pull_message", "pull_number", "ref"
DEBUG = True
VERBOSE = False


class PullError(ValueError):
    pass


@dc.dataclass
class PullRequest:
    ref: str

    @cached_property
    def user(self) -> str:
        return self._user_index[0]

    @cached_property
    def ghstack_index(self) -> int:
        return self._user_index[1]

    @cached_property
    def pull_number(self) -> str:
        return _get_ghstack_message(self.ref)[0]

    @cached_property
    def pull_message(self) -> list[str]:
        return _get_ghstack_message(self.ref)[1]

    @cached_property
    def subject(self) -> str:
        return self.pull_message[0]

    @cached_property
    def is_open(self) -> bool:
        url = f"{_curl_command()}/{self.pull_number}"
        info = _run_json(url)
        if info.get("status") == "404":
            raise ValueError(f"{url=}\n{json.dumps(info, indent=2)}")
        return info["state"] == "open"

    @cached_property
    def commit_id(self) -> str:
        return _run(f"git show-ref -s {self.ref}")[0].strip()

    @cached_property
    def url(self) -> str:
        return f"{_PULL_PREFIX}{self.pull_number}"

    @cached_property
    def commit_url(self) -> str:
        return f"{_COMMIT_PREFIX}{self.commit_id}"

    @cached_property
    def hud_url(self) -> str:
        return f"{_HUD_PREFIX}{self.pull_number}"

    @cached_property
    def ref_url(self) -> str:
        upstream, _, ref = self.ref.partition("/")
        return f"{_REF_PREFIX}{ref}"

    def asdict(self) -> dict[str, Any]:
        return {f: v for f in FIELDS if (v := self.__dict__.get(f)) is not None}

    @classmethod
    def fromdict(cls, ref: str, **kwargs: Any) -> "PullRequest":
        pr = cls(ref)
        pr.__dict__.update(kwargs)
        return pr

    @cached_property
    def _user_index(self) -> tuple[str, int]:
        parts = self.ref.split("/")
        if len(parts) == 5:
            remote, gh, user, index, branch = parts
            if branch != "orig":
                raise PullError("Waiting for orig branch")
            if remote == "upstream" and gh == "gh" and index.isnumeric():
                return user, int(index)

        raise PullError(f"Do not understand git reference '{self.ref}'")


@cache
def _get_ghstack_message(ref: str) -> tuple[str, list[str]]:
    lines = _run(f"git log --pretty=medium -1 {ref}", print_error=False)
    lines = [i[4:] for i in lines if i[:4] == "    "]
    assert lines

    urls = [u for s in lines if (u := s.partition(_PULL_REQUEST_RESOLVED)[2].strip())]
    if not urls:
        raise PullError("not a ghstack pull request")
    if len(urls) > 1:
        raise PullError("Malformed ghstack pull requst")

    end = next((i for i, s in enumerate(lines) if s.startswith(_GHSTACK_SOURCE)), -1)
    lines = lines[:end]
    while lines and not lines[-1].strip():
        lines.pop()
    pull = urls[0].partition(_PULL_PREFIX)[2].strip()
    assert pull.isnumeric() and len(pull) in (6, 7), pull  # We're around 145636 now
    return pull, lines


@dc.dataclass
class PullRequests:
    argv: Optional[Sequence[str]] = None
    path: Path = DEFAULT_CACHE_PATH

    def load(self) -> None:
        if self.path.exists() and (pulls := json.loads(self.path.read_text())):
            self.pulls = {
                k: [PullRequest.fromdict(**i) for i in v] for k, v in pulls.items()
            }

    def save(self) -> None:
        if (pulls := self.__dict__.get("pulls")) is not None:
            d = {k: [i.asdict() for i in v] for k, v in pulls.items()}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(d, indent=2))

    @cached_property
    def pulls(self) -> dict[str, list[PullRequest]]:
        result: dict[str, list[PullRequest]] = {}
        for branch in _run("git branch -r"):
            pr = PullRequest(branch.strip())
            with suppress(PullError):
                if getattr(self.args, "all", False) or pr.user == self.user:
                    result.setdefault(pr.user, []).append(pr)
        return result

    def __call__(self) -> None:
        global VERBOSE
        VERBOSE = self.args.verbose

        if self.args.fetch:
            _run("git fetch upstream")

        if not (self.args.ignore_cache or self.args.rewrite_cache):
            self.load()

        try:
            getattr(self, "_" + self.args.command, self._url_command)()
        except PullError as e:
            arg = getattr(self.args, "pull", None) or getattr(self.args, "search", None)
            msg = f"ERROR: {e.args[0]}"
            if arg and not arg in msg:
                msg = f"{msg} for {arg}"
            sys.exit(msg)

        if not self.args.ignore_cache:
            self.save()

    def _checkout(self):
        fields = "rebase_against", "rebase_main", "rebase_strict"
        if sum(bool(getattr(self.args, f)) for f in fields) > 1:
            flags = ", ".join("--" + f for f in fields)
            sys.exit(f"At most one of {flags} can be set")

        _run(f"ghstack checkout {self._matching_pull().url}")
        if rebase := (
            self.args.rebase_against
            or (self.args.rebase_main and 'upstream/main')
            or (self.args.rebase_strict and 'upstream/viable/strict')
        ):
            try:
                _run("git rebase upstream/viable/strict")
            except CalledProcessError:
                sys.exit(CONFLICT_MSG)
            _run(UPDATE_SUBMODULES)

    def _url_command(self):
        value = getattr(self._matching_pull(), self.args.command)
        print(value)
        if self.args.command.endswith("url") and self.args.open:
            webbrowser.open(value)

    def _list(self):
        search = " ".join(self.args.search)
        if search.startswith(":/"):
            search = search[2:]

        def clean_and_sort(user: str) -> list[PullRequest]:
            pulls = []
            if user not in self.pulls:
                print(self.pulls)

            for p in self.pulls[user]:
                with suppress(PullError):
                    p.pull_number
                    if search in p.subject and (self.args.closed or p.is_open):
                        pulls.append(p)

            key = attrgetter("subject" if self.args.sort else "pull_number")
            return sorted(pulls, key=key, reverse=self.args.reverse)

        if self.args.all:
            for user in self.pulls:
                for p in clean_and_sort(user):
                    print(f"{user}: #{p.pull_number}: {p.subject}")
        else:
            for p in clean_and_sort(self.user):
                print(f"#{p.pull_number}: {p.subject}")

    def _get_pull(self, pull_number: str) -> PullRequest:
        user_pulls = self.pulls.values()
        pulls = (p for pr in user_pulls for p in pr)
        pull_requests_by_number = {p.pull_number: p for p in pulls}
        try:
            return pull_requests_by_number[pull_number]
        except KeyError:
            msg = "No such pull request (rerun with -fw if you know it exists)"
            raise PullError(msg) from None

    def _matching_pull(self) -> PullRequest:
        def search(s: str) -> PullRequest:
            if pl := [p for p in self.pulls[self.user] if s in p.subject]:
                return pl[-1]
            raise PullError(f"Can't find any commits matching '{self.pull}'")

        if self.pull.startswith("#"):
            return self._get_pull(self.pull[1:])

        if self.pull.startswith(":/"):
            return search(self.pull[2:])

        with suppress(CalledProcessError):
            return self._get_pull(_get_ghstack_message(self.pull)[0])

        if self.pull.isnumeric():
            with suppress(PullError):
                return self._get_pull(self.pull)

        return search(self.pull)

    def _errors(self) -> None:
        if bad := ["bs4"] * (bs4 is None) + ["requests"] * (requests is None):
            cmd = f"{sys.executable} -m pip install {' '.join(bad)}"
            msg = f"To use `pullman errors`, install {', '.join(bad)} with\n\n    {cmd}"
            raise PullError(msg)

        pull = self._matching_pull()
        if self.args.output_to_terminal:
            context, file = nullcontext(), sys.stdout
            print(f"Reading {pull.url}", file=sys.stderr)
        else:
            context = file = open(self.args.output, "w")
            msg = f"Writing {self.args.output} for {pull.url}"
            print(msg, file=sys.stderr)

        with context:
            if not self.args.output_to_terminal:
                print(f"#!/bin/bash\n\n# Failed tests for {pull.url}\n", file=file)
                if self.args.before:
                    print(f"{self.args.before}\n", file=file)

                if self.args.python or (self.args.python_default and sys.executable):
                    if not os.path.isdir(self.args.python):
                        python = os.path.dirname(self.args.python)
                    print(f"export PATH={self.args.python}:$PATH\n", file=file)
            run_error_command(pull.pull_number, self.args, file)

        if not self.args.output_to_terminal:
            st = os.stat(self.args.output)
            os.chmod(self.args.output, st.st_mode | stat.S_IEXEC)

    @cached_property
    def pull(self) -> str:
        return self.args.pull or 'HEAD'

    @cached_property
    def args(self):
        return parse(self.argv)

    @cached_property
    def remotes(self):
        """Will add an upstream remote if it doesn't exist!"""
        remotes = {}
        for s in _run("git remote -v"):
            remote, url, _ = s.split()
            user = url.partition(":")[2].partition("/")[0]
            remotes[remote] = user

        if "upstream" not in remotes:
            remote = "git@github.com:pytorch/pytorch.git"
            _run(f"git remote add upstream {remote}")
            remotes["upstream"] = remote

        return remotes

    @cached_property
    def user(self):
        if len(self.remotes) != 1:
            return self.remotes["origin"]
        for r in self.remotes.values():
            return r


def _run_raw(cmd: str, print_error: bool = True):
    if VERBOSE:
        print("$", cmd, file=sys.stderr)
    try:
        return run(cmd, capture_output=True, text=True, check=True, shell=True).stdout
    except CalledProcessError as e:
        if print_error and e.stderr:
            print(f"Error on command `{cmd}`:\n", e.stderr, file=sys.stderr)
        raise


def _run(cmd: str, print_error: bool = True):
    return _run_raw(cmd, print_error).splitlines()


def _run_json(cmd: str):
    return json.loads(_run_raw(cmd))


@cache
def _curl_command() -> str:
    headers = (
        '-H "Accept: application/vnd.github+json" '
        '-H "X-GitHub-Api-Version: 2022-11-28"'
    )
    url = f"{API_ROOT}/pulls"
    if GIT_TOKEN:
        auth = f'-H "Authorization: Bearer {GIT_TOKEN}"'
    else:
        auth = ''
        print(
            f'WARNING: one of environment variable {TOKEN_NAMES} '
            'must be not set or github will rate-limit you sooner',
            file=sys.stderr
        )
    return f"curl {headers} {auth} {url}"


class ArgumentParser(argparse.ArgumentParser):
    """
    Adds better help formatting to argparse.ArgumentParser
    """
    _epilog: str = HELP

    def exit(self, status: int = 0, message: Optional[str] = None):
        """
        Overriding this method is a workaround for argparse throwing away all
        line breaks when printing the `epilog` section of the help message.
        """
        argv = sys.argv[1:]
        if self._epilog and not status and "-h" in argv or "--help" in argv:
            print(self._epilog)
        super().exit(status, message)


def parse(argv):
    parser = ArgumentParser()
    add_parser = parser.add_subparsers(help="Commands:", dest="command").add_parser
    parsers = Namespace(**{k: add_parser(k, help=v) for k, v in _COMMANDS.items()})

    for name, p in vars(parsers).items():
        help = "Perform git fetch"
        p.add_argument("--fetch", "-f", action="store_true")

        help = "Ignore pullman's cache"
        p.add_argument("--ignore-cache", "-i", action="store_true")

        help = "Print each command before it's executed"
        p.add_argument("--verbose", "-v", action="store_true")

        help = "Rewrite cache"
        p.add_argument("--rewrite-cache", "-w", action="store_true")

        if name == "errors":
            help = "Show tests with each env variable combination that fails"
            p.add_argument("--all-env-combos", "-a", action="store_true", help=help)

            help = "Code to insert before the test commands"
            p.add_argument("--before", "-b", default="", type=str, help=help)

            help = "Select a conda environment before running"
            p.add_argument("--conda", "-c", default="", type=str, help=help)

            help = "Write to an output file"
            p.add_argument("--output", "-o", default=DEFAULT_OUT, type=str, help=help)

            help = "Write to the terminal"
            p.add_argument("--output-to-terminal", "-O", action="store_true", help=help)

            help = "Add Python or bin directory to the PATH"
            p.add_argument("--python", "-p", default="", type=str, help=help)

            help = "Add path to current Python to the PATH"
            p.add_argument("--python-default", "-P", action="store_true", help=help)

            help = "Sort errors alphabetically"
            p.add_argument("--sort", "-s", action="store_true", help=help)

            help = "Seconds to wait, 0 means none"
            p.add_argument("--time", "-t", default=0, type=int, help=help)

        elif name == "checkout":
            help = "Also rebase against a given git ref"
            p.add_argument("--rebase-against", "-R", type=str, default="", help=help)

            help = "Also rebase against upstream/main"
            p.add_argument("--rebase-main", "-m", action="store_true", help=help)

            help = "Also rebase against upstream/viable/strict"
            p.add_argument("--rebase-strict", "-r", action="store_true", help=help)

        else:
            help = "The github user name"
            p.add_argument("--user", "-u", default=None, help=help)

        if name == "list":
            help = "A string to match in git subjects"
            p.add_argument("search", nargs="*", default="", help=help)

            help = "List all users"
            p.add_argument("--all", "-a", action="store_true")

            help = "Also show closed pull requests"
            p.add_argument("--closed", "-c", action="store_true", help=help)

            help = "Reverse order of pull requests"
            p.add_argument("--reverse", "-r", action="store_true", help=help)

            help = "Sort alphabetically"
            p.add_argument("--sort", "-s", action="store_true", help=help)

        else:
            help = (
                "An optional commit, PR index, pull request number (starts with #),"
                " or search term (starts with :/)"
            )
            p.add_argument("pull", nargs="?", default="", help=help)

            if name.endswith("url"):
                help = "Open the URL in the browser"
                p.add_argument("--open", "-o", action="store_true", help=help)

    argv = sys.argv[1:]
    if "-h" not in argv and "--help" not in argv:
        if not (argv and argv[0] in _COMMANDS):
            argv = "list", *argv

    return parser.parse_args(argv)


# from failed_test_commands.py

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {GIT_TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28",
}

MATCH_PYTHON_COMMAND_RE = re.compile(r"([A-Z_]+=.*)|python")

FAILURE = "failure"
CONCLUSION = "conclusion"
COMMAND = "To execute this test, run the following from the base repo dir"
SECONDS_TO_WAIT = 0
HREF_PREFIX = "/pytorch/pytorch/actions/runs/"


def run_error_command(pull_id, args, file):
    run_ids = _get_run_ids(pull_id)
    last_cmd = ''
    commands = _failed_test_commands(run_ids, args.time)
    if not args.all_env_combos:
        d = {}
        for c, job_id in commands:
            before, _, after = c.partition("python ")
            if before and any(c_id := d.get(after, (None, None))):
                cmd, id = c_id
                if len(c) >= len(cmd):
                    continue
            d[after] = c, job_id

        commands = d.values()

    if args.sort:
        commands = sorted(commands)

    for cmd, job_id in commands:
        if cmd != last_cmd:
            print(f"{cmd}  # {job_id}", file=file)
            last_cmd = cmd


def _get_run_ids(pull_id):
    assert pull_id.isnumeric()
    text = requests.get(f"{_PULL_PREFIX}{pull_id}/checks").text
    soup = bs4.BeautifulSoup(text, "html.parser")
    links = (i for i in soup.find_all("a", href=True) if i.text)
    for a in links:
        prefix, _, href = a["href"].partition(HREF_PREFIX)
        if not prefix and href.isnumeric():
            for span in a.find_all("span"):
                span = span.text.strip()
                if span in ('inductor', 'pull', 'trunk'):
                    yield span, href
                    break


def _failed_test_commands(run_ids, seconds):
    for segment, run_id in run_ids:
        for job in _get_failures(segment, run_id, seconds):
            command = _get_command(job["id"])
            if command:
                yield command, job["id"]


def _get_failures(segment, run_id, seconds):
    while True:
        print(f"Loading jobs for {run_id}, segment={segment}...", file=sys.stderr)
        json = _api_get(f"actions/runs/{run_id}/jobs?per_page=100").json()
        try:
            jobs = json["jobs"]
        except KeyError:
            print(json, file=sys.stderr)
            sys.exit(1)

        not_finished = sum(not j["conclusion"] for j in jobs)
        if not_finished:
            msg = f"{not_finished} job{'s' * (not_finished != 1)} not finished"
            print(msg, file=sys.stderr)

        if not (seconds and not_finished):
            break
        print("Waiting for", seconds, "seconds", file=sys.stderr)
        time.sleep(seconds)

    failed = [i for i in jobs if i[CONCLUSION] == FAILURE]
    print(f"{run_id=}, {len(jobs)=}, {len(failed)=}", file=sys.stderr)
    return failed


def _get_command(job_id):
    lines = _api_get(f"actions/jobs/{job_id}/logs").text.splitlines()
    command_lines = (i for i, li in enumerate(lines) if COMMAND in li)
    cmd_index = next(command_lines, -1)
    if cmd_index == -1:
        return ""

    words = lines[cmd_index + 1].split()
    while words and not MATCH_PYTHON_COMMAND_RE.match(words[0]):
        words.pop(0)

    return " ".join(words)


def _api_get(path):
    return requests.get(f"{API_ROOT}/{path}", headers=HEADERS)


if __name__ == '__main__':
    try:
        PullRequests()()
    except PullError as e:
        if DEBUG:
            raise
        msg = f'ERROR: {e.args[0]}'
        print(msg)
        sys.exit(-1)
