'''
Created on Feb 2, 2017

@author: tobias-vogel-seerene
'''

import json
import mimetypes
import os.path
from urllib.parse import urljoin, urlparse

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
        self.apiEndpointUrl = urljoin(baseUrl, '/wiki/rest/api/content/')

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

        # for debugging
        #print('Response code: {}'.format(response.status_code))
        #print('Response content: {}'.format(response.content))
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
            raise Exception(
                'Error during request (404): {}'.format(response.json()))

        print('OK')
        data = response.json()

        if len(data['results']) == 0:
            return
        elif len(data['results']) == 1:
            pageId = data['results'][0]['id']
            versionNum = data['results'][0]['version']['number']
            link = urljoin(
                self.wikiUrl,
                data['results'][0]['_links']['webui'].lstrip('/'))
            return PageInfo(pageId, versionNum, link)
        else:
            raise Exception(
                'The page titled "{}" exists multiple times and therefore is ambiguous. Try renaming the page to create or choose another ancestor.'.format(title))

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
    def createPage(self, title, html, ancestorSnippet):
        prettyHtml = html.prettify()

        url = self.apiEndpointUrl
        postSession = requests.Session()
        postSession.auth = self.auth
        postSession.headers.update({'Content-Type': 'application/json'})

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
                           'value': prettyHtml,
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

        # deal with images
#        self.addImages(html)

    # Update a page
    def updatePage(self, page):
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

#   def processReferencedImages(self, referencedImages):
#       pass  # ist das hiernach vielleicht verwendbar?

    # Scan for images and upload as attachments if found
#    def addImages(self, html):
#        page = None
#        prettyHtml = None
#        imgs = html.find_all('img')
#        if len(imgs) > 0:
#            print(
#                '{} images were referenced on the created page. They are uploaded, too (if needed).'.format(
#                    len(imgs)))
#            for img in html.find_all('img'):
#                img['src'] = self.uploadAttachment(
#                    page, img['src'], img['alt'])
#
#        referencedImages = re.findall('<img(.*?)\/>', prettyHtml)
#        if len(referencedImages) > 0:  # or attachments:
#            print(
#                '{} images were referenced on the created page. They are uploaded, too (if needed).'.format(
#                    len(referencedImages)))
#            self.processReferencedImages(referencedImages)

#        # das ist viel besser als der regex, vielleicht kann man den gleich
#        # loswerden
#        for img in self.soup.find_all('img'):
#            img['src'] = self.uploadAttachment(page, img['src'], img['alt'])

    # Add attachments for an array of files
    def addAttachments(self, page):
        for path in self.args.attachments:
            self.uploadAttachment(page, path, '')

    def getAttachment(self, page, filename):
        url = urljoin(
            self.apiEndpointUrl,
            '{}/child/attachment'.format(page.id))

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
    def uploadAttachmentOld(self, page, rel_path, comment):
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
        print('Uploading attachment {} ({} bytes)… '.format(sourcePath, os.stat(sourcePath).st_size),
              end="",
              flush=True)

        contentType = mimetypes.guess_type(sourcePath)
        comment = 'Uploaded from "{}"'.format(originalPath)
        payload = {
            'comment': comment,
            'file': (normalizedPath, open(sourcePath, 'rb'), contentType, {'Expires': '0'})
        }

        url = urljoin(
            self.apiEndpointUrl,
            '{}/child/attachment/'.format(pageId))

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
