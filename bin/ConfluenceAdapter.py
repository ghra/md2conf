'''
Created on Feb 2, 2017

@author: tobais-vogel-seerene
'''

import json
import mimetypes
import os.path
import sys
from urllib.parse import urljoin, urlparse

from PageInfo import PageInfo
import requests


class ConfluenceAdapter(object):
    '''
    classdocs
    '''

    def __init__(self, nossl, organisation, username, password):
        self.organisation = organisation
        self.username = username
        self.password = password
        self.setUpUrls(nossl)
        self.init_session()

    def setUpUrls(self, nossl):
        schema = 'http' if nossl else 'https'

        baseUrl = '{}://{}.atlassian.net/'.format(
            schema,
            self.organisation
        )
        # a URL that is used to setup authentication headers
        self.authUrl = urljoin(baseUrl, '/wiki')

        # the URL that HTTP requests are issued against
        self.apiEndpointUrl = urljoin(baseUrl, '/wiki/rest/api/content')

    def init_session(self):
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        # do a request to the auth URL to set up authentication headers (This
        # step might not be required in all setups but it does not hurt,
        # either.)
        self.session.get(self.authUrl)

    # Retrieve page details by title
    def getPageInfo(self, title):
        print('* Checking if page exists...')
        print(" - Retrieving page information: '{}'".format(title))
        url = urljoin(self.baseUrl, '/wiki/rest/api/content')

        self.session.get(url, params={
            'title': self.title,
            'spaceKey': self.args.spacekey,
            'expand': 'version,ancestors',
        })

        r = self.session.get(url, params={
            'title': self.title,
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
            link = urljoin(self.baseUrl, rel_path)

            return PageInfo(pageId, versionNum, link)

    # Delete a page
    def deletePage(self, pageInfo):
        # TODO: test this
        if not pageInfo:
            # TODO: handle this properly
            sys.exit('No pageInfo provided. Error! Abort!')

        print('* Deleting page...')
        url = urljoin(
            self.baseUrl, '/wiki/rest/api/content/{}'.format(pageInfo.id))

        r = self.session.delete(
            url, headers={'Content-Type': 'application/json'})
        r.raise_for_status()

        if r.status_code == 204:
            print(' - Page {} deleted successfully.'.format(pageInfo.id))
        else:
            print(' - Page {} could not be deleted.'.format(pageInfo.id))

    def getParentPageInfo(self, parentPageTitle):
        return self.getPageInfo(parentPageTitle)

    def uploadPage(self, pageInfo, html):
        if pageInfo:
            self.updatePage(pageInfo)
        else:
            self.createPage()

    # Create a new page
    def createPage(self):
        print('* Creating page...')

        url = urljoin(self.baseUrl, '/wiki/rest/api/content/')

        newPage = {'type': 'page',
                   'title': self.title,
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
            page = PageInfo(
                data['id'],
                data['version']['number'],
                urljoin(self.baseUrl, rel_path),
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
            self.baseUrl, '/wiki/rest/api/content/{}'.format(page.id))

        payload = {
            "type": "page",
            "title": self.title,
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
            link = urljoin(self.baseUrl, rel_path)

            print(" - Success: '{}'".format(link))
        else:
            print(" - Page could not be updated.")

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
            self.baseUrl,
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
        url = urljoin(self.baseUrl, attachment)

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