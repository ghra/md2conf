#!/usr/bin/python3

"""
Create or update Confluence pages from markdown
"""

import argparse
from os import getenv
import os.path
import sys

from MarkdownConfluenceSync import MarkdownConfluenceSync


if __name__ == "__main__":

    # ArgumentParser to parse arguments and options
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "markdownFile",
        help="Full path of the markdown file to convert and upload. If the page already exists, it will be overwritten."
    )
    parser.add_argument(
        'spacekey',
        nargs='?',
        default='',
        help="Confluence Space key for the page. If omitted, will use user space."
    )
    parser.add_argument(
        '-u',
        '--username',
        default=getenv('CONFLUENCE_USERNAME', None),
        help='Confluence username if $CONFLUENCE_USERNAME not set. (This should not be an email address.)'
    )
    parser.add_argument(
        '-p',
        '--password',
        default=getenv('CONFLUENCE_PASSWORD', None),
        help='Confluence password if $CONFLUENCE_PASSWORD not set.'
    )
    parser.add_argument(
        '-o',
        '--orgname',
        default=getenv('CONFLUENCE_ORGNAME', None),
        help='Confluence organisation if $CONFLUENCE_ORGNAME not set, e.g., https://XXX.atlassian.net'
    )
    parser.add_argument(
        '-a',
        '--ancestor',
        help='Parent page under which page will be created or moved. (Specify the title, not the id.)')
    parser.add_argument(
        '-t',
        '--attachments',
        nargs='+',
        help='Attachment(s) to upload to page. Paths relative to the markdown file. (Currently, attachments are uploaded automatically when referenced in the markdown file and you should not need this parameter.)'
    )
    parser.add_argument(
        '-c',
        '--contents',
        action='store_true',
        default=False,
        help='Use this option to generate a contents page. (Currently, it does not work and you should not use this parameter.'
    )
    parser.add_argument(
        '-n',
        '--nossl',
        action='store_true',
        default=False,
        help='Use this option if NOT using SSL. Will use HTTP instead of HTTPS.'
    )
    parser.add_argument(
        '-d',
        '--delete',
        action='store_true',
        default=False,
        help='Use this option to delete the page instead of creating/updating it. The markdown file is then used only to find out the name of the page to be deleted.'
    )
    parser.add_argument(
        '--force-wiki-url',
        default=getenv('CONFLUENCE_WIKI_URL', None),
        help='Use this option to force other than http(s)://<orgname>.atlassian.net/wiki url. Would disable <orgname> and <nossl> options. Also available as $CONFLUENCE_WIKI_URL env.'
    )
    args = parser.parse_args()

    if not os.path.exists(args.markdownFile):
        sys.exit(
            'Error: Markdown file: "{}" does not exist.'.format(
                os.path.abspath(args.markdownFile)
            )
        )

    if not all([args.username, args.password]) or (not args.orgname and not args.force_wiki_url):
        print(
            'Please provide a username, a password, and an organisation name ' +
            'explicitly or via environment variables, see below. Both can ' +
            'be mixed.'
        )
        print()
        sys.exit(parser.format_help())

    if ('@' in args.username):
        print(
            'Warning: Your username looks like an email address. This tool will most probably not work properly. For further details consult the README.md file.')

    if not args.spacekey:
        print(
            'Spacekey not provided. I will use your username "{}" instead. Fingers crossed that this will somehow work, too.'.format(args.username))
        args.spacekey = args.username

    try:
        MarkdownConfluenceSync(args).run()
    except Exception as e:
        print(e)
