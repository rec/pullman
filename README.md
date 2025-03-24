# pullman

Pull request manager for ghstack developers (currently hardcoded for pytorch).

pullman lists your ongoing ghstack pull requests, prints and git references for
them, prints or opens URLs, and can download unit test failures from the CI.

This can be slow on the first run, over a second per pull request, but
by default pullman caches the results

## Examples


### List all your pull requests

    $ pullman.py
    $ pullman.py list

    #131354: [dynamo] Fix constant propagation in builtins and UserClasses
    #144621: [inductor] Add tests for new docstring_linter features (fix #142496)
    #144622: [inductor] Enable docstring_linter on _inductor
    ...

### List requests matching a string

    $ pullman.py list Add tests
    #144621: [inductor] Add tests for new docstring_linter features (fix #142496)

### Print URLs of pull request, optionally open them in a browser

    $ pullman.py url  # on HEAD!
    https://github.com/pytorch/pytorch/pull/148358

    $ pullman.py url -o  # Also opens the URL in the browser
    https://github.com/pytorch/pytorch/pull/148358

    $ pullman.py url :/linter
    https://github.com/pytorch/pytorch/pull/144621

    $ pullman.py hud_url
    https://hud.pytorch.org/pr/148358

    # Choose from `url`, `commit_url`, `hud_url`, `ref_url`


### Print ghstack branch ref

    $ pullman.py ref
    upstream/gh/rec/136/orig

    $ pullman.py ref :/linter
    upstream/gh/rec/137/orig

### Download errors from a pull request (requires `requests` and `bs4`)

    $ pullman errors
    python test/inductor/test_torchinductor_dynamic_shapes.py DynamicShapesCpuTests.test_input_mutation2_dynamic_shapes_cpu  # 38911198483
    python test/inductor/test_cpu_cpp_wrapper.py TestCppWrapper.test_linear_with_pointwise_batch_size_384_in_features_196_out_features_384_bias_False_epilogue_hardswish_cpu_bfloat16_cpp_wrapper  # 38911198944
    ....

## How to install

Download the file pullman.py from [here](https://github.com/rec/pullman/blob/main/pullman.py)
and put it in your path.
