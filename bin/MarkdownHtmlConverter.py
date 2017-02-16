'''
Created on Feb 1, 2017

@author: tobias-vogel-seerene
'''

import os
import re

from bs4 import BeautifulSoup, CData
import markdown
from pip._vendor.pyparsing import line


MD_EXTENSIONS = [
    'markdown.extensions.tables',
    'markdown.extensions.fenced_code',
    # maybe more: https://pythonhosted.org/Markdown/extensions/
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
        self.markdownfilename = markdownfilename
        html = self.convertMarkdownToHtml()
        self.soup = BeautifulSoup(html, "html.parser")
        self.finetuneSoup()
        self.normalized2OriginalSrcMapping = {}
        self.replaceIncludesOfLocalResources()

    def convertMarkdownToHtml(self):
        with open(self.markdownfilename, 'r') as inp:
            mdtext = inp.read()
            mdtext = self.preprocessMarkdownContent(mdtext)
            html = markdown.markdown(mdtext, extensions=MD_EXTENSIONS)
            return html

    def getTitle(self):
        try:
            return self.soup.find('h1').extract().text
        except:
            return os.path.splitext(os.path.basename(self.markdownfilename))[0]

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
        # first, replace local images references
        self.replaceIncludesOfLocalImages()

        # second, replace references to other local resources (pdf, json, zip,
        # etc.) that may be decorated with an image (thus, the images have been
        # converted before)
        self.replaceIncludesOfLocalAttachments()

    def replaceIncludesOfLocalImages(self):
        for img in self.soup.findAll('img'):
            src = img['src']
            if self.isLocalReference(src):
                normalizedSrc = self.normalizePath(src)
                self.cautiouslyAddMapping(normalizedSrc, src)
                img['src'] = normalizedSrc
                self.transformImgToConfluenceImageInclude(img)

    def transformImgToConfluenceImageInclude(self, img):
        ''' that is how it should look like:
            <ac:image ac:title="titeltext" ac:alt="alttext" ac:height="250"><ri:attachment ri:filename="bla.jpg" /></ac:image></p>
            (actually beautiful soup does not create a self-closing ri:attachment tag, but a regular one, but it still works
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

    def replaceIncludesOfLocalAttachments(self):
        for a in self.soup.findAll('a'):
            href = a['href']
            if self.isLocalReference(href):
                normalizedHref = self.normalizePath(href)
                self.cautiouslyAddMapping(normalizedHref, href)
                a['href'] = normalizedHref
                self.transformAToConfluenceAttachmentInclude(a)

    def transformAToConfluenceAttachmentInclude(self, a):
        ''' that is how it should look like:
            <ac:link><ri:attachment ri:filename="somefile.dat" /><ac:link-body>whatever was inside the original <a> tag</ac:link-body></ac:link>
            (actually beautiful soup does not create a self-closing ri:attachment tag, but a regular one, but it still works
            '''
        anchorElement = self.soup.new_tag('ac:link')
        attachmentElement = self.soup.new_tag(
            'ri:attachment', **{'ri:filename': a['href']})
        linkBodyElement = self.soup.new_tag('ac:link-body')
        linkBodyElement.contents = a.contents
        anchorElement.append(attachmentElement)
        anchorElement.append(linkBodyElement)
        a.replaceWith(anchorElement)

    def isLocalReference(self, srcAttribute):
        return not srcAttribute.startswith('http')

    def normalizePath(self, file):
        filename = os.path.split(file)[1]
        return filename

    def getNormalized2OriginalSrcMapping(self):
        return self.normalized2OriginalSrcMapping

    def finetuneSoup(self):
        self.replaceCodeBlocks()
        self.replaceUnorderedLists()

    def replaceCodeBlocks(self):
        ''' this is how it should look like:
        <ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="168f7514-4b7f-4202-9832-76ca4d2f9650">
            <ac:plain-text-body>
                <![CDATA[first line
second line
third line]]>
            </ac:plain-text-body>
        </ac:structured-macro>

        code blocks are initially created as <pre><code>code...</code></pre>
        '''
        for codeblock in self.soup.findAll('pre'):
            children = codeblock.findChildren()
            if len(children) == 1:
                firstChild = children[0]
                if firstChild.name == 'code':
                    codeText = firstChild.text
                    structuredMacroElement = self.soup.new_tag(
                        'ac:structured-macro', **{'ac:name': 'code', 'ac:schema-version': 1})
                    plainTextBodyElement = self.soup.new_tag(
                        'ac:plain-text-body')
                    cdata = CData(codeText)
                    plainTextBodyElement.append(cdata)
                    structuredMacroElement.append(plainTextBodyElement)
                    codeblock.replaceWith(structuredMacroElement)

    def replaceUnorderedLists(self):
        print(self.soup.prettify())
        pass

    def preprocessMarkdownContent(self, mdtext):
        mdtext = self.enableLists(mdtext)
        return mdtext

    def enableLists(self, mdtext):
        '''
        Unfortunately, lists are not recognized when they do not have a blank line before the first entry. In this case, the asterisks are interpreted as emphasize markup.
        Therefore, a newline has to be added before 
        '''
        lines = reversed(mdtext.splitlines())
        outputLines = []

        lastLineWasListItem = False
        for line in lines:
            isListItem = self.isProbablyListItem(line)

            if isListItem and lastLineWasListItem:
                outputLines.append(line)
            elif isListItem and not lastLineWasListItem:
                outputLines.append(line)
                lastLineWasListItem = True
            elif not isListItem and lastLineWasListItem:
                outputLines.append('')
                outputLines.append(line)
                lastLineWasListItem = True
            else:
                outputLines.append(line)

        return '\n'.join(outputLines.reverse())

    def isProbablyListItem(self, line):
        return re.fullmatch(r'\s*\*[^*]+', line) != None
