#!/usr/bin/python3
"""
Create or update Confluence pages from markdown
"""

from os import getenv
import os.path
import sys

from MarkdownConfluenceSync import MarkdownConfluenceSync
import argparse

if __name__ == "__main__":

    # ArgumentParser to parse arguments and options
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "markdownFile", help="Full path of the markdown file to convert and upload.")
    parser.add_argument('spacekey', nargs='?', default='',
                        help="Confluence Space key for the page. If omitted, will use user space.")
    parser.add_argument('-u', '--username', default=getenv('CONFLUENCE_USERNAME',
                                                           None), help='Confluence username if $CONFLUENCE_USERNAME not set.')
    parser.add_argument('-p', '--password', default=getenv('CONFLUENCE_PASSWORD',
                                                           None), help='Confluence password if $CONFLUENCE_PASSWORD not set.')
    parser.add_argument('-o', '--orgname', default=getenv('CONFLUENCE_ORGNAME', None),
                        help='Confluence organisation if $CONFLUENCE_ORGNAME not set, e.g., https://XXX.atlassian.net')
    parser.add_argument(
        '-a', '--ancestor', help='Parent page under which page will be created or moved. (Specify the title, not the id.)')
    parser.add_argument('-t', '--attachments', nargs='+',
                        help='Attachment(s) to upload to page. Paths relative to the markdown file.')
    parser.add_argument('-c', '--contents', action='store_true',
                        default=False, help='Use this option to generate a contents page.')  # TODO what does this mean? and how is it related to the addContents method and TOC in MarkdownConfluenceSync?
    parser.add_argument('-n', '--nossl', action='store_true', default=False,
                        help='Use this option if NOT using SSL. Will use HTTP instead of HTTPS.')
    parser.add_argument('-d', '--delete', action='store_true', default=False,
                        help='Use this option to delete the page instead of creating it.')  # TODO will it be overwritten then or just deleted?
    args = parser.parse_args()

    if not os.path.exists(args.markdownFile):
        sys.exit(
            'Error: Markdown file: "{}" does not exist.'.format(
                os.path.abspath(args.markdownFile)
            )
        )

    if not all([args.username, args.password, args.orgname]):
        print(
            'Please provide a username, a password, and an organisation name ' +
            'explicitly or via environment variables, see below. Both can ' +
            'be mixed.'
        )
        print()
        sys.exit(parser.format_help())

    MarkdownConfluenceSync(args).run()
