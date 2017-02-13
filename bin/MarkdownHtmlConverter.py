'''
Created on Feb 1, 2017

@author: tobias-vogel-seerene
'''

import os

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
        html = self.convertMarkdownToHtml(markdownfilename)
        self.soup = BeautifulSoup(html, "html.parser")
        self.normalized2OriginalSrcMapping = {}
        self.replaceIncludesOfLocalResources()

    def convertMarkdownToHtml(self, markdownfilename):
        with open(markdownfilename, 'r') as inp:
            html = markdown.markdown(inp.read(), extensions=MD_EXTENSIONS)
            return html

    def getTitle(self):
        return self.soup.find('h1').extract().text

    def cautiouslyAddMapping(self, normalizedPath, originalPath):
        existingOriginalPath = self.normalized2OriginalSrcMapping.get(
            normalizedPath)
        if existingOriginalPath == None:
            self.normalized2OriginalSrcMapping[normalizedPath] = originalPath
        elif existingOriginalPath != normalizedPath:
            raise Exception('There is a conflict with normalized file paths. "{}" and "{}" both are renamed to "{}"'.format(
                originalPath, existingOriginalPath, normalizedPath))

        # Add contents page
    def addContents(self):
        toc = self.soup.new_tag(
            'ac:structured-macro', **{'ac:name': 'toc'})

        for key, val in TOC_PARAMS.items():
            param = self.soup.new_tag('ac:parameter', **{'ac:name': key})
            param.string = val
            toc.append(param)

        self.soup.insert(0, toc)

    def replaceIncludesOfLocalResources(self):
        # first, replace local images
        self.replaceIncludesOfLocalImages()

        # second, replace other local resources (pdf, json, zip, etc.)
        self.replaceIncludesOfLocalAttachments()

    def replaceIncludesOfLocalImages(self):
        for img in self.soup.findAll('img'):
            src = img['src']
            if self.isLocalReference(src):
                normalizedSrc = self.normalizePath(src)
                self.cautiouslyAddMapping(normalizedSrc, src)
                img['src'] = normalizedSrc
                self.transformImgToConfluenceImageInclude(img)
#        result = ''
#        # the following regex splits up html like this
#        # input: a<img src="x.jpg" alt="a" title="t"/>b<img src="y.jpg" alt="e" title="z"/>c
#        # output: a, <img src="x.jpg" alt="a" title="t"/>, b, <img src="y.jpg"
#        # alt="e" title="z"/>, c
#        parts = re.split(r'(<img .*?/>)', html)
#        for part in parts:
#            if part.startswith('<img'):
#                attributes = {
#                    'src': None,
#                    'alt': None,
#                    'title': None,
#                }
#                for attribute in attributes.keys():
#                    match = re.search(
#                        '(?<={}=").*?(?=")'.format(attribute), part)
#                    attributes[attribute] = None if match == None else match[0]
#
#                if self.isLocalReference(attributes['src']):
#                    result += self.transformImgToConfluenceImageInclude(
#                        attributes)
#                else:
#                    result += part
#            else:
#                result += part
#        return result

    def transformImgToConfluenceImageInclude(self, img):
        ''' that is how it should look like:
            <ac:image ac:title="titeltext" ac:alt="alttext" ac:height="250"><ri:attachment ri:filename="bla.jpg" /></ac:image></p>
            '''
        attributes = {}
        if 'alt' in img.attrs.keys():
            attributes['ac:alt'] = img['alt']
        if 'title' in img.attrs.keys():
            attributes['ac:title'] = img['title']

        imageElement = self.soup.new_tag('ac:image', **attributes)
        attachmentElement = self.soup.new_tag(
            'ri:attachment', **{'ri:filename': img['src']})
        imageElement.append(attachmentElement)

        img.replaceWith(imageElement)
        print(self.soup.prettify())
# und außerdem noch die geänderte referenz rausreichen


#        result = '<ac:image '
#        if 'title' in attributes.keys():
#            result += 'ac:title="{}"'.format(attributes['title'])
#        if 'alt' in attributes.keys():
#            result += 'ac:alt="{}"'.format(attributes['alt'])
#        result += ' ac:height="250">'
#        result += '<ri:url ri:value="{}" />'.format(
#            self.removeDirectories(attributes['src']))
#        result += '</ac:image>'
#        return result

    def replaceIncludesOfLocalAttachments(self):
        for a in self.soup.findAll('a'):
            href = a['href']
            if self.isLocalReference(href):
                normalizedHref = self.normalizePath(href)
                self.cautiouslyAddMapping(normalizedHref, href)
                a['href'] = normalizedHref
                self.transformAToConfluenceAttachmentInclude(a)

#    def replaceIncludesOfLocalAnchors(self, html):
#        result = ''
#        # the following regex splits up html like this
#        # input: a<a href="x">b</a>c<a href="x">d</a>e
#        # output: a, <a href="x">b</a>, c, <a href="x">d</a>, e
#        parts = re.split('r(<a .*?/>.*?</a>)', html)
#        for part in parts:
#            if part.startswith('<a'):
#                match = re.search('(<a[^>]+>)(.*?)(</a>)', part)
#                openingTag = match[1]
#                href = re.search('(?<=href=").*?(?=")', openingTag)[0]
#                content = match[2]
#                if self.isLocalReference(href):
#                    result += part
#                else:
#                    result += self.transformAToConfluenceImageInclude(
#                        href, content)
#            else:
#                result += part
#        return result

#    def transformAToConfluenceImageInclude(self, href, content):
#        result = '<ac:link><ri:attachment ri:filename="{}" /><ac:plain-text-link-body><![CDATA[{}]]></ac:plain-text-link-body></ac:link>'.format(
#            href, content)
#        return result

    def transformAToConfluenceAttachmentInclude(self, a):
        ''' that is how it should look like:
            <ac:link><ri:attachment ri:filename="somefile.dat" /><ac:link-body>whatever was inside the original <a> tag</ac:link-body></ac:link>
            '''
        anchorElement = self.soup.new_tag('ac:link')
        attachmentElement = self.soup.new_tag(
            'ri:attachment', **{'ri:filename': a['href']})
        linkBodyElement = self.soup.new_tag('ac:link-body')
        linkBodyElement.contents = a.contents
        anchorElement.append(attachmentElement)
        anchorElement.append(linkBodyElement)
        a.replaceWith(anchorElement)
        print(self.soup.prettify())

    def isLocalReference(self, srcAttribute):
        return not srcAttribute.startswith('http')

    def normalizePath(self, file):
        filename = os.path.split(file)[1]
        return filename

    def getNormalized2OriginalSrcMapping(self):
        return self.normalized2OriginalSrcMapping
