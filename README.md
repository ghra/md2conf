Markdown to Confluence Converter
===

A script to import a named markdown document into Confluence. It handles inline images as well as code blocks and attachments. Also there is support for some custom markdown tags for use with commonly used Confluence macros.

The file will be converted into HTML and then to Confluence storage markup. Then a page will be created in the space or if it already exists, the page will be updated. (Updating does not work, currently.)

## Configuration

[Download](https://github.com/nicr9/md2conf)

### Python
Python 3 should be installed with the following required modules (most of them are installed by default):

* argparse
* bs4
* collections
* json
* markdown
* mimetypes
* os
* requests
* sys
* urllib

Instructions on installing Python and modules can be found [here](https://rittmanmead.atlassian.net/wiki/display/TECH/Python).

### Environment Variables

To use it, you will need your Confluence username, password and organisation name. If you use Google Apps to sign in to Confluence, you can still have a username & password for your Confluence account. Just logout and follow the "Unable to access your account?" link from the sign in page, which lets you set a new password. Note that your username should not be your email address. Though it seems to work for some requests, not the whole process can be run with an email address as username. Some requests have to be issued twice (GET, POST), other requests (DELETE) do not work at all. Use your real username instead. You can find it out by mentioning your user (using the `@` in Confluence or JIRA) or open the “People” page in Confluence. There you will be able to see the usernames when you hover over or click on a user.

You will also need the organisation name that is used in the subdomain. For example the URL: `https://fawltytowers.atlassian.net/wiki/` would indicate an organsiation name of **fawltytowers**.

These can be specified at runtime or set as Confluence environment variables (e.g., add to your ~/.profile or ~/.bash_profile on Mac OS): 

``` bash
export CONFLUENCE_USERNAME='basil'
export CONFLUENCE_PASSWORD='abc123'
export CONFLUENCE_ORGNAME='fawltytowers'
```

On Windows, this can be set via system properties.

## Use

### Basic

The minimum accepted parameters are the markdown file to upload as well as the Confluence space key you wish to upload to. For the following examples assume 'Test Space' with key: `TST`.

```
python md2conf.py readme.md TST
```
Mandatory Confluence parameters can also be set here if not already set as environment variables:

* **-u** **--username**: Confluence User
* **-p** **--password**: Confluence Password
* **-o** **--orgname**:	 Confluence Organisation

```
python md2conf.py readme.md TST -u basil -p abc123 -o fawltytowers
```
Use **-h** to view a list of all available options.

### Other Uses

Use **-a** or **--ancestor** to designate the name of a page which the page should be created under. This has to be the name, not the ID of the parent page.

```
python md2conf.py readme.md TST -a "Parent Page Name"
```

Use **-d** or **--delete** to delete the page instead of create it. Obviously this won't work if it doesn't already exist. The markdown file is then used only to find out the name of the page to delete.

Use **-n** or **--nossl** to specify a non-SSL url, i.e., **http://** instead of **https://**.

Attachments are uploaded automatically. For historical reasons there is a command line argument for attachments.

## Markdown

The original markdown to HTML conversion is performed by the Python **markdown** library. Additionally, the page name is taken from the first <h1> of the markdown file (after converting it to HTML), usually assumed to be the title.

Standard markdown syntax for images and code blocks will be automatically converted. The images are uploaded as attachments and the references updated in the HTML. The code blocks will be converted to the Confluence Code Block macro and also support syntax highlighting.

### Information, Note and Warning Macros

> **Warning:** Any blockquotes used will implement an information macro. This could potentially harm your formatting.

Block quotes in Markdown are rendered as information macros. 

	> This is an info

![macros](images/infoMacro.png)

	> Note: This is a note

![macros](images/noteMacro.png)

	> Warning: This is a warning
	
![macros](images/warningMacro.png)


Alternatively, using a custom Markdown syntax also works:

```
~?This is an info.?~

~!This is a note.!~

~%This is a warning.%~
```
