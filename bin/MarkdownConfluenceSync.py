'''
Created on Jan 31, 2017

@author: tobias-vogel-seerene
'''

import os.path

from ConfluenceAdapter import ConfluenceAdapter
from MarkdownHtmlConverter import MarkdownHtmlConverter


class MarkdownConfluenceSync(object):

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
        # FIXME: this currently does not work and produces garbage in the HTML
        if self.args.contents:
            self.markdownHtmlConverter.addContents()

        targetPageInfo = self.confluenceAdapter.getPageInfo(self.title)

        if self.args.delete:
            self.confluenceAdapter.deletePage(targetPageInfo, self.title)
        else:
            self.ancestorSnippet = self.getAncestorsSnippet()

            pageId = self.confluenceAdapter.uploadPage(
                targetPageInfo,
                self.title,
                self.markdownHtmlConverter.prettyPrint(),
                self.ancestorSnippet,
            )

            self.confluenceAdapter.uploadAttachments(
                self.sourceFolder,
                pageId,
                self.markdownHtmlConverter.getNormalized2OriginalSrcMapping())

        self.printGoodByeMessage()

    def getAncestorsSnippet(self):
        if self.args.ancestor:
            parentPageInfo = self.confluenceAdapter.getPageInfo(
                self.args.ancestor, 'parent')
            if parentPageInfo:
                return [
                    {'type': 'page', 'id': parentPageInfo.id}
                ]
            else:
                raise Exception(
                    'The parent page "{}" does not exist.'.format(self.args.ancestor))
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
           self.args.spacekey,
           self.title,
           # TODO: what will be used?
           self.args.ancestor or '(nothing provided, will create the page directly in the root of the selected space)'
           )
        )

    def printGoodByeMessage(self):
        print('Finished successfully.')
