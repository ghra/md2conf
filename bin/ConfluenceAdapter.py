'''
Created on Feb 2, 2017

@author: tobias-vogel-seerene
'''

import json
import mimetypes
import os.path
from urllib.parse import urljoin

from PageInfo import PageInfo
import requests


class ConfluenceAdapter(object):

    def __init__(self, nossl, organisation, username, password, spacekey):
        self.organisation = organisation
        self.spacekey = spacekey or username
        self.setUpUrls(nossl)
        self.auth = (username, password)
        self.init_session()

    def setUpUrls(self, nossl):
        schema = 'http' if nossl else 'https'

        baseUrl = '{}://{}.atlassian.net/'.format(
            schema,
            self.organisation
        )
        # the URL that HTTP requests are issued against
        self.apiEndpointUrl = urljoin(baseUrl, '/wiki/rest/api/content')

        # a URL that is used to check authentication
        self.connectionTestUrl = urljoin(
            self.apiEndpointUrl, '?limit=0')

        # the URL where the human-readable wiki lives
        self.wikiUrl = urljoin(baseUrl, 'wiki/')

    def init_session(self):
        # do a request to the auth URL to set up authentication headers (This
        # step might not be required in all setups but it does not hurt,
        # either.)

        self.session = requests.Session()
        self.session.auth = self.auth
        response = self.session.get(self.connectionTestUrl)
        if response.status_code != 200:
            errorMessage = 'Authentification against Confluence failed returning the status code {}. '.format(
                response.status_code)
            errorMessage += {
                401: 'The credentials are unknown to the organisation "{}".'.format(self.organisation),
                502: 'The organisation name "{}" is unknown to Atlassian.'.format(self.organisation),
            }.get(response.status_code, 'An unknown error occurred.')
            raise Exception(errorMessage)
        elif len(response.content) == 0:
            raise Exception(
                'The response had a status code 200, but was empty. Did you specify an email address as username?')

    def doRequest(self, preparedRequest):
        preparedRequest.auth = self.auth

        response = {
            'GET': self.session.get(preparedRequest.url),
            'POST': self.session.send(preparedRequest),
            'DELETE': self.session.delete(preparedRequest.url),
        }.get(preparedRequest.method)

        return response

    # Retrieve page details by title
    def getPageInfo(self, title, relationship='target'):
        preparedRequest = requests.Request('GET', self.apiEndpointUrl, params={
            'spaceKey': self.spacekey,
            'expand': 'version,ancestors',
            'title': title,
        }).prepare()

        print('Checking, whether {} page "{}" exists (GET {})… '.format(
            relationship,
            title,
            preparedRequest.url),
            end='',
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
            raise Exception(
                'Error during request: {}'.format(response.json()))

        print('OK')

        data = response.json()

        numberOfResults = len(data['results'])
        if numberOfResults == 0:
            print('Found no pages with that name.')
            return
        elif numberOfResults == 1:
            pageId = data['results'][0]['id']
            versionNum = data['results'][0]['version']['number']
            link = urljoin(
                self.wikiUrl,
                data['results'][0]['_links']['webui'].lstrip('/'))
            print('Found a page with that name located at {}.'.format(link))
            return PageInfo(pageId, versionNum, link)
        else:
            print('Found {} pages with that name.'.format(numberOfResults))
            raise Exception(
                'The page titled "{}" exists multiple times and therefore is ambiguous. Try renaming the page to create or choose another ancestor or delete it manually.'.format(title))

    # Delete a page
    def deletePage(self, pageInfo, title):
        if not pageInfo:
            raise Exception(
                'The page "{}" was not found and therefore cannot be deleted. There is nothing to do. Aborting.'.format(title))

        url = urljoin(self.apiEndpointUrl + '/', pageInfo.id)

        print(
            'Deleting page "{}" located at {} (DELETE {})… '.format(
                title,
                pageInfo.link,
                url
            ),
            end='',
            flush=True)

        preparedRequest = requests.Request('DELETE', url).prepare()

        response = self.doRequest(preparedRequest)

        if response.status_code == 204:
            print('OK')
        else:
            print(
                'Failed with status code {}. Aborting.'.format(response.status_code))

    def uploadPage(self, pageInfo, title, html, ancestorSnippet):
        if pageInfo:
            # FIXME: update a page
            print('Disabled updating a page.')
            # self.updatePage(pageInfo)
            pass
        else:
            return self.createPage(title, html, ancestorSnippet)

    # Create a new page
    def createPage(self, title, prettyHtml, ancestorSnippet):
        #prettyHtml = html.prettify()
        #prettyHtml = '<ac:image ac:alt="alt-text"><ri:url ri:value="http://www.pixelio.de/data/media/27/bleistift.jpg" /></ac:image>'
        #prettyHtml = '<ac:image ac:alt="Deployment-dings" ac:title="This is the deployment dings"> <ri:attachment ri:filename="2015-07-13_EP-system-architecture.png"> </ri:attachment></ac:image>'
        #prettyHtml = '<ac:image ac:alt="Deployment-dings" ac:title="This is the deployment dings"> <ri:attachment ri:filename="2015-07-13_EP-system-architecture.png" /></ac:image>'

        url = self.apiEndpointUrl
        postSession = requests.Session()
        postSession.auth = self.auth
        postSession.headers.update({'Content-Type': 'application/json'})

        print('Creating the page "{}" (POST {})… '.format(
            title,
            url),
            end='',
            flush=True)
        newPage = {'type': 'page',
                   'title': title,
                   'space': {'key': self.spacekey},
                   'body': {
                       'storage': {
                           'value': prettyHtml,
                           'representation': 'storage'
                       }
                   },
                   'ancestors': ancestorSnippet
                   }

        response = postSession.post(url, data=json.dumps(newPage))
        response.raise_for_status()

        if response.status_code == 200:
            print('OK, created.')
            data = response.json()
            humanReadableUrl = urljoin(
                self.wikiUrl,
                data['_links']['webui'].lstrip('/'))
            idUrl = urljoin(
                self.wikiUrl,
                'pages/viewpage.action?pageId={}'.format(data[u'id']))
            print('The created page "{}" is located at "{}" (or {}).'.format(
                title, humanReadableUrl, idUrl))
            return data[u'id']
        else:
            raise(Exception(
                'Uploading the page "{}" failed with error code {}.'.format(title, response.status_code)))

    # Update a page
    def updatePage(self, page):
        # this method is most probably broken
        print('* Updating page...')

        # Add images and attachments
        self.addImages(page)
        # self.addAttachments(page)

        url = urljoin(self.apiEndpointUrl, format(page.id))

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
            link = urljoin(
                self.wikiUrl,
                data['_links']['webui'].lstrip('/'))

            print(" - Success: '{}'".format(link))
        else:
            print(" - Page could not be updated.")

    def uploadAttachments(self, sourceFolder, pageId, normalized2OriginalPathMapping):
        numberOfAttachmentsToUpload = len(normalized2OriginalPathMapping)
        if numberOfAttachmentsToUpload == 0:
            return
        elif numberOfAttachmentsToUpload == 1:
            print('An attachment has to be uploaded.')
        else:
            print('{} attachments have to be uploaded.'.format(
                numberOfAttachmentsToUpload))

        for normalizedPath, originalPath in normalized2OriginalPathMapping.items():
            self.uploadAttachment(
                sourceFolder, pageId, normalizedPath, originalPath)

    def uploadAttachment(self, sourceFolder, pageId, normalizedPath, originalPath):
        sourcePath = os.path.join(sourceFolder, originalPath)

        url = urljoin(
            self.apiEndpointUrl + '/',
            '{}/child/attachment/'.format(pageId))

        print('Uploading attachment {} with {} bytes (POST {})… '.format(sourcePath, os.stat(sourcePath).st_size, url),
              end='',
              flush=True)

        contentType = mimetypes.guess_type(sourcePath)
        comment = 'Uploaded from "{}"'.format(originalPath)
        payload = {
            'comment': comment,
            'file': (normalizedPath, open(sourcePath, 'rb'), contentType, {'Expires': '0'})
        }

        response = self.session.post(
            url,
            files=payload,
            headers={'X-Atlassian-Token': 'no-check'},
        )

        if response.status_code == 200:
            print('OK')
        else:
            print('Failed')
            raise Exception(response.message)
