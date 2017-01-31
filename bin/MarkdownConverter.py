'''
Created on Jan 31, 2017

@author: tobias-vogel-seerene
'''

import collections
import json
import mimetypes
import os.path
import sys
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import markdown
import requests


WELCOME = """
------------------------
Markdown Confluence Sync
------------------------

Markdown file:    '{}'
Space Key:    '{}'
Title:        '{}'
"""

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
pageInfo = collections.namedtuple('PageInfo', ['id', 'version', 'link'])


class MyClass(object):
    '''
    classdocs
    '''
    # TODO: create classdocs

    def __init__(self, args):
        self.args = args
        self.sourceFolder = os.path.dirname(
            os.path.abspath(self.args.markdownFile))

        # Get base URL for confluence
        schema = 'http' if self.args.nossl else 'https'
        # TODO: this is not (yet) the wiki URL and should not be called like
        # that
        self.wikiUrl = '{}://{}.atlassian.net/'.format(
            schema,
            self.args.orgname
        )
        # a base URL that is used to setup authentication headers
        self.authUrl = self.wikiUrl + '/wiki'

        with open(self.args.markdownFile, 'r') as inp:
            html = markdown.markdown(inp.read(), extensions=MD_EXTENSIONS)
            self.soup = BeautifulSoup(html, "html.parser")

        self.init_session()

        # Extract the document title
        self.title = self.soup.find('h1').extract()

        welcome_msg = WELCOME.format(
            self.args.markdownFile, self.args.spacekey, self.title.text)
        print(welcome_msg)

        # Add a TOC
        self.addContents()

        page = self.getPage()

        if self.args.delete:
            if page:
                self.deletePage(page)
            # TODO: print an error message (will count as exit code 1)
            sys.exit(1)

        if self.args.ancestor:
            parentPage = self.getPage(self.args.ancestor)
            if parentPage:
                self.ancestors = [{'type': 'page', 'id': parentPage.id}]
            else:
                print(
                    '* Error: Parent page does not exist: {}'.format(self.args.ancestor))
                # TODO: print an error message (will count as exit code 1)
                sys.exit(1)
        else:
            self.ancestors = []

        if page:
            self.updatePage(page)
        else:
            self.createPage()

    def init_session(self):
        self.session = requests.Session()
        self.session.auth = (self.args.username, self.args.password)
        # do a request to the auth URL to set up authentication headers (This
        # step might not be required in all setups but it does not hurt,
        # either.)
        self.session.get(self.authUrl)

    # Add contents page
    def addContents(self):
        if self.args.contents:
            toc = self.soup.new_tag(
                'ac:structured-macro', **{'ac:name': 'toc'})

            for key, val in TOC_PARAMS.iteritems():
                param = self.soup.new_tag('ac:parameter', **{'ac:name': key})
                param.string = val
                toc.append(param)

            self.soup.body.insert(0, toc)

    # Retrieve page details by title
    def getPage(self):
        print('* Checking if page exists...')
        print(" - Retrieving page information: '{}'".format(self.title.text))
        url = urljoin(self.wikiUrl, '/wiki/rest/api/content')

        self.session.get(url, params={
            'title': self.title.text,
            'spaceKey': self.args.spacekey,
            'expand': 'version,ancestors',
        })

        r = self.session.get(url, params={
            'title': self.title.text,
            'spaceKey': self.args.spacekey,
            'expand': 'version,ancestors',
        })

        # Check for errors
        if r.status_code == 404:
            print('* Error: Page not found. Check the following are correct:')
            print(" - Space Key : '{}'".format(self.args.spacekey))
            print(" - Organisation Name: '{}'".format(self.args.orgname))
            sys.exit(1)

        data = r.json()

        if len(data['results']) >= 1:
            pageId = data['results'][0]['id']
            versionNum = data['results'][0]['version']['number']
            rel_path = os.path.join(
                '/wiki', data['results'][0]['_links']['webui'].lstrip('/'))
            link = urljoin(self.wikiUrl, rel_path)

            return pageInfo(pageId, versionNum, link)

    # Create a new page
    def createPage(self):
        print('* Creating page...')

        url = urljoin(self.wikiUrl, '/wiki/rest/api/content/')

        newPage = {'type': 'page',
                   'title': self.title.text,
                   'space': {'key': self.args.spacekey},
                   'body': {
                       'storage': {
                           'value': self.soup.prettify(),
                           'representation': 'storage',
                       },
                   },
                   'ancestors': self.ancestors,
                   }

        r = self.session.post(
            url, data=json.dumps(newPage),
            headers={'Content-Type': 'application/json'},
        )
        r.raise_for_status()

        if r.status_code == 200:
            data = r.json()
            spaceName = data['space']['name']
            rel_path = os.path.join('/wiki', data['_links']['webui'])
            page = pageInfo(
                data['id'],
                data['version']['number'],
                urljoin(self.wikiUrl, rel_path),
            )

            print(
                '* Page created in {} with ID: {}.'.format(spaceName, page.id))
            print(" - URL: '{}'".format(page.link))

            imgCheck = self.soup.find_all('img')
            if imgCheck or self.args.attachments:
                print('* Attachments found, update procedure called.')
                self.updatePage(page)
        else:
            print('* Could not create page.')
            sys.exit(1)

    # Update a page
    def updatePage(self, page):
        print('* Updating page...')

        # Add images and attachments
        self.addImages(page)
        # self.addAttachments(page)

        url = urljoin(
            self.wikiUrl, '/wiki/rest/api/content/{}'.format(page.id))

        payload = {
            "type": "page",
            "title": self.title.text,
            "body": {
                    "storage": {
                        "value": self.soup.prettify(),
                        "representation": "storage",
                    },
            },
            "version": {
                "number": page.version + 1
            },
            "ancestors": self.ancestors,
        }

        r = self.session.put(
            url,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
        )
        r.raise_for_status()

        if r.status_code == 200:
            data = r.json()
            rel_path = os.path.join(
                '/wiki', data['_links']['webui'].lstrip('/'))
            link = urljoin(self.wikiUrl, rel_path)

            print(" - Success: '{}'".format(link))
        else:
            print(" - Page could not be updated.")

    # Delete a page
    def deletePage(self, page):
        print('* Deleting page...')
        url = urljoin(
            self.wikiUrl, '/wiki/rest/api/content/{}'.format(page.id))

        r = self.session.delete(
            url, headers={'Content-Type': 'application/json'})
        r.raise_for_status()

        if r.status_code == 204:
            print(' - Page {} deleted successfully.'.format(page.id))
        else:
            print(' - Page {} could not be deleted.'.format(page.id))

    # Scan for images and upload as attachments if found
    def addImages(self, page):
        for img in self.soup.find_all('img'):
            img['src'] = self.uploadAttachment(page, img['src'], img['alt'])

    # Add attachments for an array of files
    def addAttachments(self, page):
        for path in self.args.attachments:
            self.uploadAttachment(page, path, '')

    def getAttachment(self, page, filename):
        url = urljoin(
            self.wikiUrl,
            '/wiki/rest/api/content/{}/child/attachment'.format(page.id))

        r = self.session.get(url, params={
            'filename': filename,
        })
        r.raise_for_status()

        data = r.json()
        if data['results']:
            return '/wiki/rest/api/content/{}/child/attachment/{}/data'.format(
                page.id, data['results'][0]['id'])

        return '/wiki/rest/api/content/{}/child/attachment/'.format(page.id)

    # Upload an attachment
    def uploadAttachment(self, page, rel_path, comment):
        if urlparse(rel_path).scheme:
            return rel_path
        basename = os.path.basename(rel_path)
        print(' - Uploading attachment {}...'.format(basename))

        attachment = self.getAttachment(page, basename)
        url = urljoin(self.wikiUrl, attachment)

        full_path = os.path.join(self.sourceFolder, rel_path)
        contentType = mimetypes.guess_type(full_path)[0]
        payload = {
            'comment': comment,
            'file': (basename, open(full_path, 'rb'), contentType, {'Expires': '0'})
        }

        r = self.session.post(
            url,
            files=payload,
            headers={'X-Atlassian-Token': 'no-check'},
        )
        r.raise_for_status()

        return '/wiki/download/attachments/{}/{}'.format(page.id, basename)
