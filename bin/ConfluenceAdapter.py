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

    def __init__(self, nossl, organisation, username, password, spacekey):
        self.organisation = organisation
        self.spacekey = spacekey or username
        self.setUpUrls(nossl)
        self.auth = (username, password)
        self.init_session()

    def setUpUrls(self, nossl):
        schema = 'http' if nossl else 'https'

        self.baseUrl = '{}://{}.atlassian.net/'.format(
            schema,
            self.organisation
        )
        # the URL that HTTP requests are issued against
        self.apiEndpointUrl = urljoin(self.baseUrl, '/wiki/rest/api/content/')

        # a URL that is used to setup authentication headers
        self.authUrl = urljoin(self.baseUrl, 'wiki')

    def init_session(self):
        # do a request to the auth URL to set up authentication headers (This
        # step might not be required in all setups but it does not hurt,
        # either.)

        self.session = requests.Session()
        self.session.auth = self.auth
        response = self.session.get(self.authUrl)
        if response.status_code != 200:
            errorMessage = 'Authentification against Confluence failed returning the status code {}. '.format(
                response.status_code)
            errorMessage += {
                401: 'The credentials are unknown to the organisation "{}".'.format(self.organisation),
                502: 'The organisation name "{}" is unknown to Atlassian.'.format(self.organisation),
            }.get(response.status_code, 'An unknown error occurred.')
            raise Exception(errorMessage)

# test request
#        preparedRequest = requests.Request('GET',
#                                           self.apiEndpointUrl,
#                                           params={
#                                               'spaceKey': self.orgname,
#                                               'expand': 'version,ancestors',
#                                               'title': "Migration Overview",
#                                           }).prepare()
#        print(preparedRequest.url)
#        response = self.doRequest(preparedRequest)

    def doRequest(self, preparedRequest):
        preparedRequest.auth = self.auth

        response = {
            'GET': self.session.get(preparedRequest.url),
            'POST': self.session.post(preparedRequest.url),
            'DELETE': self.session.delete(preparedRequest.url),
        }.get(preparedRequest.method)

        # for debugging
        # print(response.status_code)
        # print(response.content)
        return response

    # Retrieve page details by title
    def getPageInfo(self, title, relationship='target'):
        preparedRequest = requests.Request('GET', self.apiEndpointUrl, params={
            'spaceKey': self.spacekey,
            'expand': 'version,ancestors',
            'title': title,
        }).prepare()

        print('Checking, whether {} page "{}" exists ({})… '.format(
            relationship,
            title,
            preparedRequest.url),
            end="",
            flush=True)

        response = self.doRequest(preparedRequest)

        # Check for errors
        if response.status_code != 200:
            print('Failed')
            if response.status_code == 404:
                print(
                    'Error: Page not found. Check the following are correct:')
                print('Space key : "{}"'.format(self.spacekey))
                print('Organisation name: "{}"'.format(self.organisation))
                # sys.exit(1)
            # TODO: format and handle exception properly
            raise Exception('error')

        print('OK')
        data = response.json()

        if len(data['results']) == 0:
            return
        elif len(data['results']) == 1:
            pageId = data['results'][0]['id']
            versionNum = data['results'][0]['version']['number']
            rel_path = os.path.join(
                '/wiki', data['results'][0]['_links']['webui'].lstrip('/'))
            link = urljoin(self.baseUrl, rel_path)
            return PageInfo(pageId, versionNum, link)
        else:
            raise Exception(
                'The page titled "{}" exists multiple times and therefore is ambiguous. Try renaming the file to create or choose another ancestor.'.format(title))

    # Delete a page
    def deletePage(self, pageInfo, title):
        # TODO: test this
        if not pageInfo:
            raise Exception(
                'The page "{}" was not found and therefore cannot be deleted. There is nothing to do. Aborting.'.format(title))

        print('Deleting page "{}" ({})… '.format(
            title,
            pageInfo.link
        ),
            end="",
            flush=True)
        url = urljoin(self.apiEndpointUrl, pageInfo.id)

        preparedRequest = requests.Request('DELETE', url).prepare()

        response = self.doRequest(preparedRequest)

        # r = self.session.delete(
        #    url, headers={'Content-Type': 'application/json'})
        # r.raise_for_status()

        if response.status_code == 204:
            print('OK')
        else:
            print(
                'Failed with status code {}. Aborting.'.format(response.status_code))

    def deletePageOldStyle(self, pageInfo):
        print('\nDeleting page...')
        url = '%s%s' % (self.apiEndpointUrl, pageInfo.id)

        s = requests.Session()
        s.auth = self.auth
        s.headers.update({'Content-Type': 'application/json'})

        s.delete(url)
        r = s.delete(url)
        r.raise_for_status()

        if r.status_code == 204:
            print('Page %s deleted successfully.' % pageInfo.id)

    def uploadPage(self, pageInfo, title, html, ancestorSnippet):
        if pageInfo:
            # self.updatePage(pageInfo)
            pass
        else:
            # TODO: do not use old style, but new style
            self.createPageOldStyle(title, html, ancestorSnippet)
            #self.createPage(title, html, ancestorSnippet)

    # Create a new page
    def createPage(self, title, html, ancestorSnippet):
        # TODO: how can this happen to not be printed?
        url = "(((((((((((noch nciht bekannt))))))))))))))"
        print('Creating the page "{}" ({})… '.format(
            title,
            url),
            end="",
            flush=True)

        newPage = {'type': 'page',
                   'title': title,
                   'space': {'key': self.spacekey},
                   'body': {
                       'storage': {
                           'value': html.prettify(),
                           'representation': 'storage',
                       },
                   },
                   'ancestors': ancestorSnippet,
                   }

        preparedRequest = requests.Request(
            'POST',
            self.apiEndpointUrl,
            data=json.dumps(newPage),
        ).prepare()

        response = self.doRequest(preparedRequest)
        response.raise_for_status()

        if response.status_code == 200:
            data = response.json()
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

    # Create a new page
    def createPageOldStyle(self, title, html, ancestorSnippet):
        url = self.apiEndpointUrl
        postSession = requests.Session()
        postSession.auth = self.auth
        postSession.headers.update({'Content-Type': 'application/json'})

        # again, do this authentification request
        postSession.get(self.authUrl)

        print('Creating the page "{}"… '.format(
            title,
            url),
            end="",
            flush=True)
        newPage = {'type': 'page',
                   'title': title,
                   'space': {'key': self.spacekey},
                   'body': {
                       'storage': {
                           'value': html.prettify(),
                           'representation': 'storage'
                       }
                   },
                   'ancestors': ancestorSnippet
                   }

        #s.post(url, data=json.dumps(newPage))
        response = postSession.post(url, data=json.dumps(newPage))
        response.raise_for_status()

        if response.status_code == 200:
            print('OK')
            data = response.json()
            #spaceName = data[u'space'][u'name']
            #pageId = data[u'id']
            #version = data[u'version'][u'number']

            humanReadableUrl = urljoin(self.baseUrl, data[u'_links'][u'webui'])
            idUrl = urljoin(self.apiEndpointUrl, data[u'id'])

            print("ignoring images or attachments for now")
#            imgCheck = re.search('<img(.*?)\/>', body)
#            if imgCheck or attachments:
#                print '\tAttachments found, update procedure called.'
#                updatePage(pageId, title, body, version, ancestors, attachments)
#            else:
#                if goToPage:
#                    webbrowser.open(link)
            print('The created page "{}" is located at "{}" (or {}).'.format(
                title, humanReadableUrl, idUrl))
        else:
            raise(Exception(
                'Uploading the page "{}" failed with error code {}.'.format(title, response.status_code)))

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
