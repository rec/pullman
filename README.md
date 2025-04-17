# pullman

Pull request manager for PyTorch ghstack developers.

`pullman` lists your open ghstack pull requests, checks them out, prints git
references for them, prints or opens URLs, and can download unit test failures
from the CI.

You can specify pull requests with a pull request ID, or any commit ID which
has ghstack information in it, or using string search.

None of this would be useful without a local cache: getting all the needed information
from github takes one to two seconds per pull request the first time.

## A quick tour

    $ pullman
    #131354: [dynamo] Fix constant propagation in builtins and UserClasses
    #145150: [inductor] Simplify _inductor/utils.py slightly
    #145636: Simplify functional composition in _aot_autograd/dispatch_and_compile_graph.py
    #146845: Fix non-bitwise type annotations for Tensor operators (see #145838)
    #148959: Move token linter code into tools/linter/adaptors/_linter/
    #149958: [inductor] Add some typing to _inductor/ir.py
    #149959: [inductor] Add more typing to _inductor/ir.py
    #150767: [inductor] Clean typing in codegen/common.py and codecache.py

    $ git log -1 --oneline $(pm ref slightly)
    c2f0f86cff2 (upstream/gh/rec/124/orig) [inductor] Simplify _inductor/utils.py slightly

    $ pullman url -o functional  # Also opens #145636 in the browser
    https://github.com/pytorch/pytorch/pull/145636

    $ pullman errors constant
    Writing unit-test-failures.sh for https://github.com/pytorch/pytorch/pull/131354
    Loading jobs for 12893911506, segment=pull...
    run_id='12893911506', len(jobs)=86, len(failed)=44
    Loading jobs for 12893912723, segment=inductor...
    run_id='12893912723', len(jobs)=38, len(failed)=27

    # Wrote an executable shell file with commands to run the failed unit tests,
    # or at least the ones the program can figure out...

    $ pullman checkout --fetch --rewrite -r token
    # Throws away the pullman cache, then calls
    #
    #    git fetch upstream
    #    ghstack checkout https://github.com/pytorch/pytorch/pull/148959
    #    git rebase upstream/viable/strict
    #    git submodule update --init --recursive

## Commands

You can use any prefix of any of these commands, like `pullman l` or `pullman ch`.

### `pullman list`: list all your pull requests

    $ pullman
    $ pullman l
    $ pullman list

    #131354: [dynamo] Fix constant propagation in builtins and UserClasses
    #144621: [inductor] Add tests for new docstring_linter features (fix #142496)
    #144622: [inductor] Enable docstring_linter on _inductor
    ...

    $ pullman list Add tests
    $ pullman Add tests

    #144621: [inductor] Add tests for new docstring_linter features (fix #142496)

### `pullman url|commit_url|hud_url|ref_url`: print a URL, optionally open in a browser

    $ pullman url  # Looks at ghstack information in HEAD
    https://github.com/pytorch/pytorch/pull/148358

    $ pullman url other-branch  # Looks at ghstack information in some other branch
    https://github.com/pytorch/pytorch/pull/148358

    # Use :/ to force a string search
    $ pullman url :/other-branch
    ERROR: Can't find any commits matching ':/other-branch'

    $ pullman url linter  # searches for pull requests matching "linter"
    https://github.com/pytorch/pytorch/pull/144621

    $ pullman url -o  # Also opens the URL in the browser
    https://github.com/pytorch/pytorch/pull/148358

    $ pullman hud_url
    https://hudtorch.org/pr/148358

### `pullman checkout`: run `ghstack checkout` on a matching pull request

    $ pullman checkout
    # Calls `ghstack checkout` on the pull request that matches HEAD

    $ pullman ref :/linter
    upstream/gh/rec/137/orig

### `pullman ref`: print ghstack branch git ref

    $ pullman ref
    upstream/gh/rec/136/orig

    $ pullman ref linter
    upstream/gh/rec/137/orig

### `pullman errors`: download errors from a pull request

    $ pullman errors
    $ pull

    # Werite a file with failed unit tests, like this:
    #
    # python test/inductor/test_torchinductor_dynamic_shapes.py ...
    # PYTORCH_TEST_WITH_DYNAMO=1 python test/inductor/test_cpu_cpp_wrapper.py ...
    ....

## How to install

Download the file pullman.py from [here](https://github.com/rec/pullman/blob/main/pullman.py)
and put it in your path.
