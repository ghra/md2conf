'''
Created on Jan 31, 2017

@author: tobias-vogel-seerene
'''

import os.path
import sys

from ConfluenceAdapter import ConfluenceAdapter
from MarkdownHtmlConverter import MarkdownHtmlConverter


class MarkdownConfluenceSync(object):
    '''
    classdocs
    '''
    # TODO: create classdocs

    def __init__(self, args):
        self.args = args
        self.sourceFolder = os.path.dirname(
            os.path.abspath(self.args.markdownFile))

        self.confluenceAdapter = ConfluenceAdapter(
            args.nossl,
            args.orgname,
            args.username,
            args.password,
            args.spacekey,
        )

    def run(self):
        self.markdownHtmlConverter = MarkdownHtmlConverter(
            self.args.markdownFile)

        # Extract the document title
        self.title = self.markdownHtmlConverter.getTitle()

        self.printWelcomeMessage()

        # Add a TOC
        # TODO: perhaps this should be done only if it is requested by the
        # corresponding parameter?
        if self.args.contents:
            self.markdownHtmlConverter.addContents()

        targetPageInfo = self.confluenceAdapter.getPageInfo(self.title)

        if self.args.delete:
            self.confluenceAdapter.deletePage(targetPageInfo)
            return

        self.ancestorSnippet = self.getAncestorsSnippet()

        self.confluenceAdapter.uploadPage(
            targetPageInfo,
            self.markdownHtmlConverter.soup.contents
        )

    def getAncestorsSnippet(self):
        if self.args.ancestor:
            parentPageInfo = self.confluenceAdapter.getPageInfo(
                self.args.ancestor)
            if parentPageInfo:
                return [
                    {'type': 'page', 'id': parentPageInfo.id}
                ]
            else:
                print(
                    '* Error: Parent page does not exist: {}'.format(self.args.ancestor))
                # TODO: print an error message (will count as exit code 1) or
                # better throw exception
                sys.exit(1)
        else:
            return []

    def printWelcomeMessage(self):
        print('''------------------------
Markdown Confluence Sync
------------------------

Markdown file: "{}"
Space key:     "{}"
Title:         "{}"
Parent title:  "{}"
'''.format(os.path.abspath(self.args.markdownFile),
           # TODO: print something if no spacekey is provided (username or so
           # will then be the spacekey)
           # TODO: the username is an email address which does not work as
           # private space, i think. better double-check this
           self.args.spacekey or '(nothing provided, will use ~username instead)',
           self.title,
           # TODO: what will be used?
           self.args.ancestor or '(nothing provided, will use ??? instead)'
           )
        )
