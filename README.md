# pullman

Pull request manager for PyTorch ghstack developers.

`pullman` lists your open ghstack pull requests, checks them out, prints git
references for them, prints or opens URLs, and can download unit test failures
from the CI.

You can specify pull requests with a pull request ID, or any commit ID which
has ghstack information in it, or using string search.

None of this would be useful without a local cache: getting all the needed information
from github takes one to two seconds per pull request the first time.

## Examples

### List all your pull requests

    $ pullman
    $ pullman l
    $ pullman list

    #131354: [dynamo] Fix constant propagation in builtins and UserClasses
    #144621: [inductor] Add tests for new docstring_linter features (fix #142496)
    #144622: [inductor] Enable docstring_linter on _inductor
    ...

### List requests matching a string

    $ pullman list Add tests
    $ pullman Add tests
    #144621: [inductor] Add tests for new docstring_linter features (fix #142496)

### Print URLs of pull request, optionally open them in a browser

    $ pullman url  # Looks at ghstack information in HEAD
    https://github.com/pytorch/pytorch/pull/148358

    $ pullman url other-branch  # Looks at ghstack information in some other branch
    https://github.com/pytorch/pytorch/pull/148358

    $ pullman url linter  # searches for pull requests matching "linter"
    https://github.com/pytorch/pytorch/pull/144621

    $ pullman url -o  # Also opens the URL in the browser
    https://github.com/pytorch/pytorch/pull/148358

    $ pullman hud_url
    https://hudtorch.org/pr/148358

    # Choose from `url`, `commit_url`, `hud_url`, `ref_url`

### Print ghstack branch ref

    $ pullman ref
    upstream/gh/rec/136/orig

    $ pullman ref :/linter
    upstream/gh/rec/137/orig

### Download errors from a pull request

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
