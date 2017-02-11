'''
Created on Feb 1, 2017

@author: tobias-vogel-seerene
'''

import os
import re

from bs4 import BeautifulSoup
import markdown

IMAGE_FILETYPES = ['jpg', 'gif', 'png']
#TRUSTED_PATHS_TO_COPY = ['https://github.com/{}'.format(orgname)]

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
        html = self.convertMarkdownToHtml(markdownfilename)
        #resources = self.findUsageOfLocalResources(html)
        html, resourceMapping = self.replaceIncludesOfLocalResources(html)
        self.soup = BeautifulSoup(html, "html.parser")

    def convertMarkdownToHtml(self, markdownfilename):
        with open(markdownfilename, 'r') as inp:
            html = markdown.markdown(inp.read(), extensions=MD_EXTENSIONS)
            return html

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

    def replaceIncludesOfLocalResources(self, html):
        # first, replace local images
        modifiedHtml, resourceMappingImage = self.replaceIncludesOfLocalImages(
            html)

        # second, replace other local resources (pdf, json, zip, etc.)
        modifiedHtml, resourceMappingOther = self.__replaceIncludesOfLocalResources(
            modifiedHtml, 'a', 'href', self.transformAToConfluenceImageInclude)

        # merge both mappings
        # (https://stackoverflow.com/questions/38987/how-to-merge-two-python-dictionaries-in-a-single-expression)
        resourceMapping = {**resourceMappingImage, **resourceMappingOther}
        return resourceMapping, html

    def replaceIncludesOfLocalImages(self, html):
        result = ''
        # the following regex splits up html like this
        # input: a<img src="x.jpg" alt="a" title="t"/>b<img src="y.jpg" alt="e" title="z"/>c
        # output: a, <img src="x.jpg" alt="a" title="t"/>, b, <img src="y.jpg"
        # alt="e" title="z"/>, c
        parts = re.split(r'(<img .*?/>)', html)
        for part in parts:
            if part.startswith('<img'):
                attributes = {
                    'src': None,
                    'alt': None,
                    'title': None,
                }
                for attribute in attributes.keys():
                    match = re.search(
                        '(?<={}=").*?(?=")'.format(attribute), part)
                    attributes[attribute] = None if match == None else match[0]

                if self.isLocalReference(attributes['src']):
                    result += self.transformImgToConfluenceImageInclude(
                        attributes)
                else:
                    result += part
            else:
                result += part
        return result

    def replaceIncludesOfLocalAnchors(self, html):
        result = ''
        # the following regex splits up html like this
        # input: a<a href="x">b</a>c<a href="x">d</a>e
        # output: a, <a href="x">b</a>, c, <a href="x">d</a>, e
        parts = re.split('r(<a .*?/>.*?</a>)', html)
        for part in parts:
            if part.startswith('<a'):
                match = re.search('(<a[^>]+>)(.*?)(</a>)', part)
                openingTag = match[1]
                href = re.search('(?<=href=").*?(?=")', openingTag)[0]
                content = match[2]
                if self.isLocalReference(href):
                    result += part
                else:
                    result += self.transformAToConfluenceImageInclude(
                        href, content)
            else:
                result += part
        return result

    def transformImgToConfluenceImageInclude(self, attributes):
        result = '<ac:image '
        if 'title' in attributes.keys():
            result += 'ac:title="{}"'.format(attributes['title'])
        if 'alt' in attributes.keys():
            result += 'ac:alt="{}"'.format(attributes['alt'])
        result += ' ac:height="250">'
        result += '<ri:url ri:value="{}" />'.format(
            self.removeDirectories(attributes['src']))
        result += '</ac:image>'
        return result

    def transformAToConfluenceImageInclude(self, href, content):
        result = '<ac:link><ri:attachment ri:filename="{}" /><ac:plain-text-link-body><![CDATA[{}]]></ac:plain-text-link-body></ac:link>'.format(
            href, content)
        return result

    def isLocalReference(self, srcAttribute):
        return not srcAttribute.startsWith('http')

    def removeDirectories(self, sourceAttribute):
        path, filename = os.path.split(sourceAttribute)
        return filename
