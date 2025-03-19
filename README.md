# pullman

Pull request manager for ghstack developers (currently hardcoded for pytorch)


## How to install

Download the file pullman.py from this directory.

`pullman.py error` depends on `bs4` and `requests` being installed but none of the other
commands have any dependencies

## What it does

`pullman` lists your ongoing ghstack pull requests, prints and git
references for them, prints or opens URLs, and can download unit test failures.

##

```
usage: pullman.py [-h] {commit_url,errors,hud_url,list,ref,ref_url,url} ...

positional arguments:
  {commit_url,errors,hud_url,list,ref,ref_url,url}
                        Commands:
    commit_url          Print git ref id URL for a pull request
    errors              Download all the errors for a pull request
    hud_url             HUD URL for a pull request
    list                List all pull requests
    ref                 Print git ref id of a pull request
    ref_url             Print git ref id URL for a pull request
    url                 Print the URL for a pull request

optional arguments:
  -h, --help            show this help message and exit

(pytorch-dev-hint) (main) rec@qgpu3:~/git/torch-build$
```
