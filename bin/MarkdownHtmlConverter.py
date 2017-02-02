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

    def __init__(self, markdownfilename):
        self.convertMarkdownToHtml(markdownfilename)

    def convertMarkdownToHtml(self, markdownfilename):
        with open(markdownfilename, 'r') as inp:
            html = markdown.markdown(inp.read(), extensions=MD_EXTENSIONS)
            self.soup = BeautifulSoup(html, "html.parser")

    def getTitle(self):
        return self.soup.find('h1').extract().text