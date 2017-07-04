#
# This file is part of my.gpodder.org.
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

import uuid
import unittest
from collections import Counter

from django.core.urlresolvers import reverse
from django.test.client import Client as TestClient
from django.test import TestCase
from django.test.utils import override_settings
from django.contrib.auth import get_user_model

from mygpo.test import create_auth_string, create_user
from mygpo.podcasts.models import Podcast
from mygpo.maintenance.merge import PodcastMerger
from mygpo.api.backend import get_device
from mygpo.users.models import Client, SyncGroup, UserProxy
from mygpo.subscriptions import subscribe, unsubscribe


class DeviceSyncTests(unittest.TestCase):

    def setUp(self):
        self.user = UserProxy(username='test')
        self.user.email = 'test@invalid.com'
        self.user.set_password('secret!')
        self.user.save()


    def test_group(self):
        dev1 = Client.objects.create(id=uuid.uuid1(), user=self.user, uid='d1')
        dev2 = Client.objects.create(id=uuid.uuid1(), user=self.user, uid='d2')

        group = next(self.user.get_grouped_devices())
        self.assertEqual(group.is_synced, False)
        self.assertIn(dev1, group.devices)
        self.assertIn(dev2, group.devices)


        dev3 = Client.objects.create(id=uuid.uuid1(), user=self.user, uid='d3')

        dev1.sync_with(dev3)

        groups = self.user.get_grouped_devices()

        g2 = next(groups)
        self.assertEqual(g2.is_synced, False)
        self.assertIn(dev2, g2.devices)

        g1 = next(groups)
        self.assertEqual(g1.is_synced, True)
        self.assertIn(dev1, g1.devices)
        self.assertIn(dev3, g1.devices)

        targets = dev1.get_sync_targets()
        target = next(targets)
        self.assertEqual(target, dev2)

    def tearDown(self):
        Client.objects.filter(user=self.user).delete()
        self.user.delete()


@override_settings(CACHE={})
class UnsubscribeMergeTests(TestCase):
    """ Test if merged podcasts can be properly unsubscribed """

    P2_URL = 'http://test.org/podcast/'

    def setUp(self):
        self.podcast1 = Podcast.objects.get_or_create_for_url('http://example.com/feed.rss')
        self.podcast2 = Podcast.objects.get_or_create_for_url(self.P2_URL)

        User = get_user_model()
        self.user = User(username='test-merge')
        self.user.email = 'test@example.com'
        self.user.set_password('secret!')
        self.user.save()

        self.device = get_device(self.user, 'dev', '')

    def test_merge_podcasts(self):
        subscribe(self.podcast2, self.user, self.device)

        # merge podcast2 into podcast1
        pm = PodcastMerger([self.podcast1, self.podcast2], Counter(), [])
        pm.merge()

        # get podcast for URL of podcast2 and unsubscribe from it
        p = Podcast.objects.get(urls__url=self.P2_URL)
        unsubscribe(p, self.user, self.device)

        subscriptions = Podcast.objects.filter(subscription__user=self.user)
        self.assertEqual(0, len(subscriptions))

    def tearDown(self):
        self.podcast1.delete()
        self.user.delete()


class AuthTests(TestCase):

    def setUp(self):
        self.user, pwd = create_user()
        self.client = TestClient()
        wrong_pwd = pwd + '1234'
        self.extra = {
            'HTTP_AUTHORIZATION': create_auth_string(self.user.username,
                                                     wrong_pwd)
        }

    def test_queries_failed_auth(self):
        """ Verifies the number of queries that are executed on failed auth """
        url = reverse('api-all-subscriptions',
                      args=(self.user.username, 'opml'))
        with self.assertNumQueries(1):
            resp = self.client.get(url, **self.extra)
        self.assertEqual(resp.status_code, 401, resp.content)


def load_tests(loader, tests, ignore):
    for m in [DeviceSyncTests, UnsubscribeMergeTests, AuthTests]:
        tests.addTest(unittest.TestLoader().loadTestsFromTestCase(m))
    return tests
