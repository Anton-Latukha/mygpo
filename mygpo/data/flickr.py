#
# This file is part of gpodder.net.
#
# my.gpodder.org is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# my.gpodder.org is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public
# License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with my.gpodder.org. If not, see <http://www.gnu.org/licenses/>.
#


import json
import re
import urllib.request, urllib.parse, urllib.error

from django.conf import settings

import logging
logger = logging.getLogger(__name__)


def get_photo_sizes(photo_id):
    api_key = settings.FLICKR_API_KEY
    request = 'https://api.flickr.com/services/rest/?method=flickr.photos.getSizes&api_key=%s&photo_id=%s&format=json' % (api_key, photo_id)

    try:
        resp = urllib.request.urlopen(request).read().decode('utf-8')
    except urllib.error.HTTPError as e:
        logger.warn('Retrieving Flickr photo sizes failed: %s', str(e))
        return []

    extract_re = '^jsonFlickrApi\((.*)\)$'
    m = re.match(extract_re, resp)
    if not m:
        return []

    resp_obj = json.loads(m.group(1))

    try:
        return resp_obj['sizes']['size']
    except KeyError:
        return []


def get_photo_id(url):
    photo_id_re = 'http://.*flickr.com/[^/]+/([^_]+)_.*'
    match = re.match(photo_id_re, url)
    if match:
        return match.group(1)


def is_flickr_image(url):
    if url is None:
        return False
    return re.search('flickr\.com.*\.(jpg|jpeg|png|gif)', url)

def get_display_photo(url, label='Medium'):
    photo_id = get_photo_id(url)
    sizes = get_photo_sizes(photo_id)
    for s in sizes:
        if s['label'] == label:
            return s['source']

    return url
