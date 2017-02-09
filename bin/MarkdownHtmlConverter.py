'''
Created on Feb 1, 2017

@author: tobias-vogel-seerene
'''

from bs4 import BeautifulSoup
import markdown

MD_EXTENSIONS = [
    'markdown.extensions.tables',
    'markdown.extensions.fenced_code',
]

TOC_PARAMS = {
    'printable': 'true',
    'style': 'disc',
    'maxLevel': '5',
    'minLevel': '1',
    'class': 'rm-contents',
    'exclude': '',
    'type': 'list',
    'outline': 'false',
    'include': '',
}


class MarkdownHtmlConverter(object):

    def __init__(self, markdownfilename):
        self.convertMarkdownToHtml(markdownfilename)

    def convertMarkdownToHtml(self, markdownfilename):
        with open(markdownfilename, 'r') as inp:
            html = markdown.markdown(inp.read(), extensions=MD_EXTENSIONS)
            self.soup = BeautifulSoup(html, "html.parser")

    def getTitle(self):
        return self.soup.find('h1').extract().text

        # Add contents page
    def addContents(self):

        toc = self.soup.new_tag(
            'ac:structured-macro', **{'ac:name': 'toc'})

        for key, val in TOC_PARAMS.items():
            param = self.soup.new_tag('ac:parameter', **{'ac:name': key})
            param.string = val
            toc.append(param)

        self.soup.insert(0, toc)
