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


class MarkdownHtmlConverter(object):

    @classmethod
    def convertMarkdownToHtml(cls, markdownfilename):
        with open(markdownfilename, 'r') as inp:
            html = markdown.markdown(inp.read(), extensions=MD_EXTENSIONS)
            return BeautifulSoup(html, "html.parser")