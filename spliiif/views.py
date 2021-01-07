import bleach, json, re, sys

from flask import render_template, request
from lxml import etree
from spliiif import app

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search/<manifest>')
def search(manifest):
    # gonna get those url params, yo.
    q = bleach.clean(request.args.get('q', default=''), strip=True, tags=[])

    # quick n' dirty.
    manifest_uri = 'https://iiif-manifest.lib.uchicago.edu/{}/{}.json'.format(
        manifest.replace('-', '/'),
        manifest
    )

    # skeletal response.
    response_dict = {
        '@context': [
            'http://iiif.io/api/presentation/2/context.json',
            'http://iiif.io/api/search/1/context.json'
        ],
        '@id': '{}/search/{}?q={}'.format(request.host_url, manifest, q),
        '@type': 'sc:AnnotationList',
        'hits': [],
        'resources': [],
        'within': {
            '@type': 'sc:Layer',
            'ignored': [],
            'total': 0
        }
    }

    # use sample data for this mockup.
    xml = etree.parse('/Users/jej/NOTES/marklogic/spliiif/output.xml')
    
    page_num = 0
    hit_num = 0

    # iterate over search result snippets.
    for match in xml.xpath(
        '/'.join((
            '',
            'response',
            's:response',
            's:result',
            's:snippet',
            's:match'
        )),
        namespaces={'s': 'http://marklogic.com/appservices/search'}
    ):

        # modify the xpath so I can use it to extract the original nodes.
        xp = re.sub(
            '^fn:doc\([^)]*\)',
            '/response',
            match.get('path')
        )
        xp = re.sub(
            '\*',
            'h',
            xp
        )
        # get the exact element from the original document.
        el = xml.xpath(xp, namespaces={'h': 'http://www.w3.org/1999/xhtml'})[0]
    
        # extract coordinates, convert to integers.
        l, t, r, b = [int(s) for s in el.get('title').split(';')[0].split(' ')[1:]]
    
        # convert to x, y, width, height.
        x, y, w, h = (l, t, r - l, b - t)
    
        # build an identifier (copying from whiiif)
        hit_id = 'uun:spliiif:{}:P{}:{}'.format(manifest, page_num, hit_num)
    
        # add hit.
        response_dict['hits'].append({
            '@type': 'search:Hit',
            'annotations': [ hit_id ],
            'match': el.text
        })
    
        # add resource.
        response_dict['resources'].append({
            '@id': hit_id,
            '@type': 'oa:Annotation',
            'motivation': 'sc:painting',
            'on': '{}/canvas/P{}#xywh={},{},{},{}'.format(manifest_uri, page_num, x, y, w, h),
            'resource': {
                '@type': 'cnt:ContentAsText',
                'chars': q
            }
        })

        hit_num += 1

    # adjust hits.
    response_dict['within']['total'] = hit_num

    response = app.response_class(
        response=json.dumps(response_dict),
        mimetype='application/json',
        headers=[('Access-Control-Allow-Origin', '*')]
    )

    return response
