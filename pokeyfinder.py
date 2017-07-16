#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# * * * * * * * * * * * * * * * * * * * *
#   pokeyfinder.py : find web pages using a word list
#   https://github.com/wnormandin/pokeyfinder
#   Requires python3
# * * * * * * * * * * * * * * * * * * * *
#
#   MIT License
#
#   Copyright (c) 2017 William Normandin
#
#   Permission is hereby granted, free of charge, to any person obtaining a copy
#   of this software and associated documentation files (the "Software"), to deal
#   in the Software without restriction, including without limitation the rights
#   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#   copies of the Software, and to permit persons to whom the Software is
#   furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included in all
#   copies or substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#   SOFTWARE.
#
# * * * * * * * * * * * * * * * * * * * *
import sys
import queue
import threading
import requests
import argparse
import time
import json
import os
import datetime
from urllib.parse import urljoin

this = sys.modules[__name__]
DEF_UA = ''
session = requests.Session()

class Formatter(argparse.RawDescriptionHelpFormatter):
    def _split_lines(self, text, width):
        text = self._whitespace_matcher.sub(' ', text).strip()
        return _textwrap.wrap(text, width)

def cprint(val, col=None, verbose=False):
    if not args.verbose and verbose:
        return
    if col==None:
        msg = val
    else:
        msg = color_wrap(val, col)
    print(msg)

def color_wrap(val, col):
    if args.nocolor:
        return str(val)
    return ''.join([col, str(val), Color.END])

class Color:
    BLACK_ON_GREEN = '\x1b[1;30;42m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    MSG = '\x1b[1;32;44m'
    ERR = '\x1b[1;31;44m'
    TST = '\x1b[7;34;46m'

def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', nargs='*', help='Specify target URL(s)', required=True)
    parser.add_argument('--word-list', type=str, help='Specify a word list', required=True)
    parser.add_argument('--max-threads', type=int, default=5, help='Max concurrent worker threads per target')
    parser.add_argument('--ua', type=str, help='Specify a user agent', default=DEF_UA)
    parser.add_argument('--nocolor', action='store_true', help='Suppress colors in output')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--ext-list', nargs='*', type=str, help='Specify an optional extension list')
    parser.add_argument('--showall', action='store_true', help='Show failed attempts')
    parser.add_argument('--outfile', type=str, help='Specify output file (default=./{1st target}.{date}.json)')
    parser.add_argument('--resume', type=str, help='Specify a word from which to resume (for failed scans)')
    parser.add_argument('--timeout', type=int, help='Specify a request timeout for faster scanning', default=2)
    this.args = parser.parse_args()
    if args.outfile is None:
        if '/' in args.target[0]:
            tgt = args.target[0].split('/')[2]
        else:
            tgt = args.target[0]
        ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        args.outfile = os.path.join(os.getcwd(), '{}.{}.json'.format(tgt, ts))
    cprint('[*] Output file: {}'.format(args.outfile), Color.MSG)
    this.session.headers.update({'user-agent':args.ua}) # Set UA string in session headers

def list_builder():
    with open(args.word_list) as wl:
        w_list = wl.readlines()
    _resume = False
    words = queue.Queue()
    for w in [wrd.rstrip() for wrd in w_list]:
        if args.resume is not None:
            if _resume:
                words.put(w)
            else:
                if w == args.resume:
                    _resume = True
                    cprint('[*] Resuming from {}'.format(args.resume), Color.MSG)
        else:
            words.put(w)
    cprint(' -  Found {} words'.format(words.qsize()), Color.BLUE, True)
    return words

def directory_bruter(word_q, target, result_q, run_event):
    while not word_q.empty() and run_event.is_set():
        attempt = word_q.get()
        att_list = []
        fmt = '/{}' if '.' in attempt else '/{}/'
        att_list.append(fmt.format(attempt))
        if args.ext_list:
            for ext in args.ext_list:
                att_list.append('/{}{}'.format(attempt, ext))
        for item in att_list:
            try:
                url = urljoin(target, item)
                resp = session.get(url, timeout=args.timeout)
                code = resp.status_code
                if code == 200:
                    col = Color.GREEN
                elif code in range(300,305):
                    col = Color.CYAN
                elif code in range(400,404):
                    col = Color.CYAN
                else:
                    col = Color.RED
                if (code != 200 and args.showall) or code == 200:
                    cprint('{} -> {} ({})'.format(resp.status_code, url, resp.url), col)
                result_q.put((resp.status_code, url, resp.url))
            except Exception as e:
                cprint('{} -> {}'.format(url, str(e)[:50]), Color.ERR)
                continue
        word_q.task_done()

def gather_results(q):
    this.results = {'http_response_code':{'requested_url':'response_url'}}
    while not q.empty():
        code, url, r_url = q.get()
        if code not in results:
            this.results[code] = {}
        this.results[code][url] = r_url
        q.task_done()

if __name__ == '__main__':
    try:
        cli()
        cprint(' -  CLI arguments parsed', Color.BLUE, True)
        threads = []
        result_q = queue.Queue()
        run_event = threading.Event()
        run_event.set()
        cprint(' -  Run event set', Color.BLUE, True)
        try:
            for target in args.target:
                if not target.startswith('http://') and not target.startswith('https://'):
                    target = 'http://{}'.format(target)
                cprint('[*] Building word list', Color.MSG)
                word_q = list_builder()
                for i in range(args.max_threads):
                    t = threading.Thread(target=directory_bruter,
                                         args=(word_q, target,
                                              result_q, run_event))
                    t.start()
                    threads.append(t)
            cprint('[*] {} total threads started'.format(len(threads)), Color.MSG)
            for t in threads:
                t.join()
        except KeyboardInterrupt:
            print()
            cprint('[*] Keyboard interrupt detected', Color.ERR)
            cprint(' -  Gathering results, Ctrl+C again to force quit', Color.BLUE)
            run_event.clear()
            cprint(' -  Run event cleared', Color.BLUE, True)
            for t in threads:
                t.join()

        gather_results(result_q)
        with open(args.outfile, 'w+') as ofile:
            cprint(' -  {} opened for writing'.format(args.outfile), Color.BLUE, True)
            json.dump(results, ofile, indent=2)
        cprint('[*] Results written successfully', Color.MSG)
    except KeyboardInterrupt:
        print()
        cprint('[*] Exiting', Color.ERR)
        sys.exit(0)
