# pullman

Pull request manager for ghstack developers (currently hardcoded for pytorch).

pullman lists your ongoing ghstack pull requests, prints and git references for
them, prints or opens URLs, and can download unit test failures from the CI.

This can be slow on the first run, over a second per pull request, but
by default pullman caches the results

## Examples


### List all the pull requests

    $ pullman.py
    $ pullman.py list

### List requests matching a string

    $ pullman.py list DRAFT

### Print URL of pull request

    $ pullman.py url  # on HEAD!
    https://github.com/pytorch/pytorch/pull/148358

    $ pullman.py url :/linter
    https://github.com/pytorch/pytorch/pull/148959

### Print ghstack branch ref for HEAD

    $ pullman.py ref
    upstream/gh/rec/136/orig

    $ pullman.py ref :/linter
    upstream/gh/rec/137/orig

### Print and perhaps open various URLs

    $ pullman.py ref_url
    https://github.com/pytorch/pytorch/tree/gh/rec/136/orig

    $ pullman.py

### Download errors from a pull request (requires `requests` and `bs4`)

    $ pullman errors
    python test/inductor/test_torchinductor_dynamic_shapes.py DynamicShapesCpuTests.test_input_mutation2_dynamic_shapes_cpu  # 38911198483
    python test/inductor/test_cpu_cpp_wrapper.py TestCppWrapper.test_linear_with_pointwise_batch_size_384_in_features_196_out_features_384_bias_False_epilogue_hardswish_cpu_bfloat16_cpp_wrapper  # 38911198944
    ....

## How to install

Download the file pullman.py from [here](https://github.com/rec/pullman/blob/main/pullman.py)
and put it in your path.
