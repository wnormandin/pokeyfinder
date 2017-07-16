# pokeyfinder
### A simple tool to discover web pages based on a word list.
* Download a word list (i.e. [SVN Digger](https://www.netsparker.com/blog/web-security/svn-digger-better-lists-for-forced-browsing/) against which to compare each target domain.
* Set a default User Agent string in the script if desired.
* Use --ext-list to pass a list of file extensions to be tested for each word.
* Max-threads is PER TARGET.
```
usage: pokeyfinder.py [-h] --target [TARGET [TARGET ...]] --word-list
                      WORD_LIST [--max-threads MAX_THREADS] [--ua UA]
                      [--nocolor] [--verbose]
                      [--ext-list [EXT_LIST [EXT_LIST ...]]] [--showall]
                      [--outfile OUTFILE] [--resume RESUME]
                      [--timeout TIMEOUT]

optional arguments:
  -h, --help            show this help message and exit
  --target [TARGET [TARGET ...]]
                        Specify target URL(s)
  --word-list WORD_LIST
                        Specify a word list
  --max-threads MAX_THREADS
                        Max concurrent worker threads per target
  --ua UA               Specify a user agent
  --nocolor             Suppress colors in output
  --verbose             Enable verbose output
  --ext-list [EXT_LIST [EXT_LIST ...]]
                        Specify an optional extension list
  --showall             Show failed attempts
  --outfile OUTFILE     Specify output file (default=./{1st
                        target}.{date}.json)
  --resume RESUME       Specify a word from which to resume (for failed scans)
  --timeout TIMEOUT     Specify a request timeout for faster scanning
```

Basic usage (with interrupt)
```
# python pokeyfinder.py --word-list ../.lists/all.txt --showall --target test.com test.net test.org                                
[*] Output file: /home/user/test.com.20170716-141423.json
[*] Building word list
[*] Building word list
[*] Building word list
[*] 15 total threads started
200 -> http://test.com/CVS/ (https://www.test.com/)
200 -> http://test.com/common/ (https://www.test.com/)
...
[*] Keyboard interrupt detected
[*] Results written successfully
```
A single keyboard interrupt signals the worker threads to exit and begins gathering results for writing.  Send another interrupt to abort and exit.

Results are written in JSON with the structure: {'http_response_code':{'requested_url':'response_url'}}
