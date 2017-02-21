# -*- coding: utf-8 -*-
import json
import os

from bs4 import BeautifulSoup

from dlkit_runtime.configs import FILESYSTEM_ASSET_CONTENT_TYPE
from dlkit_runtime.errors import NotFound
from dlkit_runtime.primordium import DataInputStream, Type, Id, DisplayText

from testing_utilities import BaseTestCase, get_fixture_repository, get_managers
from urllib import unquote, quote

from records.registry import ASSESSMENT_RECORD_TYPES, ASSET_CONTENT_RECORD_TYPES

import utilities

PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
ABS_PATH = os.path.abspath(os.path.join(PROJECT_PATH, os.pardir))

SIMPLE_SEQUENCE_RECORD = Type(**ASSESSMENT_RECORD_TYPES['simple-child-sequencing'])
MULTI_LANGUAGE_ASSET_CONTENTS = Type(**ASSET_CONTENT_RECORD_TYPES['multi-language'])


class BaseRepositoryTestCase(BaseTestCase):
    def _create_asset(self):
        form = self._repo.get_asset_form_for_create([])
        form.display_name = 'Test asset'
        asset = self._repo.create_asset(form)

        asset_records = [MULTI_LANGUAGE_ASSET_CONTENTS]
        try:
            config = asset._runtime.get_configuration()
            parameter_id = utilities.clean_id('parameter:assetContentRecordTypeForFiles@mongo')
            asset_records.append(config.get_value_by_parameter(parameter_id).get_type_value())
        except (AttributeError, KeyError, NotFound):
            pass

        content_form = self._repo.get_asset_content_form_for_create(asset.ident, asset_records)
        content_form.add_display_name(DisplayText(text='test asset content',
                                                  language_type='639-2%3AENG%40ISO',
                                                  format_type='TextFormats%3APLAIN%40okapia.net',
                                                  script_type='15924%3ALATN%40ISO'))
        content_form.add_description(DisplayText(text='foo',
                                                 language_type='639-2%3AENG%40ISO',
                                                 format_type='TextFormats%3APLAIN%40okapia.net',
                                                 script_type='15924%3ALATN%40ISO'))
        content_form.set_data(DataInputStream(self.test_file))
        ac = self._repo.create_asset_content(content_form)

        # need to get the IDs to match, so update it like in the system
        self.test_file.seek(0)
        form = self._repo.get_asset_content_form_for_update(ac.ident)
        form.set_data(DataInputStream(self.test_file))
        self._repo.update_asset_content(form)

        return self._repo.get_asset(asset.ident)

    def num_assets(self, val):
        self.assertEqual(
            self._repo.get_assets().available(),
            int(val)
        )

    def setUp(self):
        super(BaseRepositoryTestCase, self).setUp()
        self.url = '/api/v1/repository'
        self._repo = get_fixture_repository()
        test_file = '{0}/tests/files/sample_movie.MOV'.format(ABS_PATH)

        self.test_file = open(test_file, 'r')

    def tearDown(self):
        super(BaseRepositoryTestCase, self).tearDown()
        self.test_file.close()


class AssetContentTests(BaseRepositoryTestCase):
    @staticmethod
    def _english_headers():
        return {'content-type': 'application/json',
                'x-api-locale': 'en'}

    @staticmethod
    def _hindi_headers():
        return {'content-type': 'application/json',
                'x-api-locale': 'hi'}

    @staticmethod
    def _telugu_headers():
        return {'content-type': 'application/json',
                'x-api-locale': 'te'}

    def create_assessment_offered_for_item(self, bank_id, item_id):
        if isinstance(bank_id, basestring):
            bank_id = utilities.clean_id(bank_id)
        if isinstance(item_id, basestring):
            item_id = utilities.clean_id(item_id)

        bank = get_managers()['am'].get_bank(bank_id)
        form = bank.get_assessment_form_for_create([SIMPLE_SEQUENCE_RECORD])
        form.display_name = 'a test assessment'
        form.description = 'for testing with'
        new_assessment = bank.create_assessment(form)

        bank.add_item(new_assessment.ident, item_id)

        form = bank.get_assessment_offered_form_for_create(new_assessment.ident, [])
        new_offered = bank.create_assessment_offered(form)

        return new_offered

    def create_item_with_image(self):
        url = '{0}/items'.format(self.assessment_url)
        self._image_in_question.seek(0)
        req = self.app.post(url,
                            upload_files=[('qtiFile',
                                           self._filename(self._image_in_question),
                                           self._image_in_question.read())])
        self.ok(req)
        return self.json(req)

    def create_item_with_image_in_choices(self):
        url = '{0}/items'.format(self.assessment_url)
        self._images_in_choices.seek(0)
        req = self.app.post(url,
                            upload_files=[('qtiFile',
                                           self._filename(self._images_in_choices),
                                           self._images_in_choices.read())])
        self.ok(req)
        return self.json(req)

    def create_upload_item(self):
        url = '{0}/items'.format(self.assessment_url)
        self._generic_upload_test_file.seek(0)
        req = self.app.post(url,
                            upload_files=[('qtiFile', 'testFile', self._generic_upload_test_file.read())])
        self.ok(req)
        return self.json(req)

    def create_taken_for_item(self, bank_id, item_id):
        if isinstance(bank_id, basestring):
            bank_id = utilities.clean_id(bank_id)
        if isinstance(item_id, basestring):
            item_id = utilities.clean_id(item_id)

        bank = get_managers()['am'].get_bank(bank_id)

        new_offered = self.create_assessment_offered_for_item(bank_id, item_id)

        form = bank.get_assessment_taken_form_for_create(new_offered.ident, [])
        taken = bank.create_assessment_taken(form)
        return taken, new_offered

    def setUp(self):
        super(AssetContentTests, self).setUp()
        self.asset = self._create_asset()
        asset_content = self.asset.get_asset_contents().next()
        self.assessment_url = '/api/v1/assessment/banks/{0}'.format(unquote(str(self._repo.ident)))
        self.url = '{0}/repositories/{1}/assets/{2}/contents/{3}'.format(self.url,
                                                                         unquote(str(self._repo.ident)),
                                                                         unquote(str(self.asset.ident)),
                                                                         unquote(str(asset_content.ident)))

        self.contents_url = '/api/v1/repository/repositories/{0}/assets/{1}/contents'.format(unquote(str(self._repo.ident)),
                                                                                             unquote(str(self.asset.ident)))

        self._generic_upload_test_file = open('{0}/tests/files/generic_upload_test_file.zip'.format(ABS_PATH), 'r')
        self._logo_upload_test_file = open('{0}/tests/files/Epidemic2.sltng'.format(ABS_PATH), 'r')
        self._replacement_image_file = open('{0}/tests/files/replacement_image.png'.format(ABS_PATH), 'r')
        self._images_in_choices = open('{0}/tests/files/qti_file_with_images.zip'.format(ABS_PATH), 'r')
        self._image_in_question = open('{0}/tests/files/mw_sentence_with_audio_file.zip'.format(ABS_PATH), 'r')

        self._english_text = 'english'
        self._hindi_text = u'हिंदी'
        self._telugu_text = u'తెలుగు'

        self._english_language_type = '639-2%3AENG%40ISO'
        self._english_script_type = '15924%3ALATN%40ISO'

        self._hindi_language_type = '639-2%3AHIN%40ISO'
        self._hindi_script_type = '15924%3ADEVA%40ISO'

        self._telugu_language_type = '639-2%3ATEL%40ISO'
        self._telugu_script_type = '15924%3ATELU%40ISO'

    def tearDown(self):
        """
        Remove the test user from all groups in Membership
        Start from the smallest groupId because need to
        remove "parental" roles like for DepartmentAdmin / DepartmentOfficer
        """
        super(AssetContentTests, self).tearDown()

        self._generic_upload_test_file.close()
        self._logo_upload_test_file.close()
        self._replacement_image_file.close()
        self._images_in_choices.close()
        self._image_in_question.close()

    def test_can_get_asset_content_file(self):
        req = self.app.get(self.url + '/stream')
        self.ok(req)
        self.test_file.seek(0)
        self.assertEqual(
            req.body,
            self.test_file.read()
        )

    def test_unknown_asset_content_extensions_preserved(self):
        upload_item = self.create_upload_item()
        taken, offered = self.create_taken_for_item(self._repo.ident, Id(upload_item['id']))
        url = '{0}/assessmentstaken/{1}/questions/{2}/submit'.format(self.assessment_url,
                                                                     unquote(str(taken.ident)),
                                                                     unquote(upload_item['id']))

        self._logo_upload_test_file.seek(0)
        req = self.app.post(url,
                            upload_files=[('submission', 'Epidemic2.sltng', self._logo_upload_test_file.read())])
        self.ok(req)

        url = '/api/v1/repository/repositories/{0}/assets'.format(unquote(str(self._repo.ident)))
        req = self.app.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(len(data), 2)
        for asset in data:
            if asset['id'] != str(self.asset.ident):
                self.assertTrue('.sltng' in asset['assetContents'][0]['url'])
                self.assertEqual('asset-content-genus-type%3Asltng%40ODL.MIT.EDU',
                                 asset['assetContents'][0]['genusTypeId'])

    def test_can_update_asset_content_with_new_file(self):
        req = self.app.get(self.url)
        self.ok(req)
        asset_content = self.asset.get_asset_contents().next()
        original_genus_type = str(asset_content.genus_type)
        original_file_name = asset_content.display_name.text
        original_on_disk_name = asset_content.get_url()
        original_id = str(asset_content.ident)

        self._replacement_image_file.seek(0)
        req = self.app.put(self.url,
                           upload_files=[('inputFile',
                                          self._filename(self._replacement_image_file),
                                          self._replacement_image_file.read())])
        self.ok(req)
        data = self.json(req)
        asset_content = data['assetContents'][0]
        self.assertNotEqual(
            original_genus_type,
            asset_content['genusTypeId']
        )
        self.assertIn('png', asset_content['genusTypeId'])
        self.assertNotEqual(
            original_file_name,
            asset_content['displayName']['text']
        )
        self.assertEqual(
            original_on_disk_name.split('.')[0],
            asset_content['url'].split('.')[0]
        )
        self.assertEqual(
            original_id,
            asset_content['id']
        )
        self.assertIn(
            self._replacement_image_file.name.split('/')[-1],
            asset_content['displayName']['text']
        )

    def test_can_update_asset_content_with_new_file_and_set_genus_type(self):
        req = self.app.get(self.url)
        self.ok(req)
        asset_content = self.asset.get_asset_contents().next()
        original_genus_type = str(asset_content.genus_type)
        original_file_name = asset_content.display_name.text
        original_on_disk_name = asset_content.get_url()
        original_id = str(asset_content.ident)

        self._replacement_image_file.seek(0)
        thumbnail_genus = "asset-content-genus%3Athumbnail%40ODL.MIT.EDU"
        req = self.app.put(self.url,
                           params={"genusTypeId": thumbnail_genus},
                           upload_files=[('inputFile',
                                          self._filename(self._replacement_image_file),
                                          self._replacement_image_file.read())])
        self.ok(req)
        data = self.json(req)
        asset_content = data['assetContents'][0]
        self.assertNotEqual(
            original_genus_type,
            asset_content['genusTypeId']
        )
        self.assertNotEqual(
            original_file_name,
            asset_content['displayName']['text']
        )
        self.assertEqual(
            original_on_disk_name.split('.')[0],
            asset_content['url'].split('.')[0]
        )
        self.assertEqual(
            original_id,
            asset_content['id']
        )
        self.assertIn(
            self._replacement_image_file.name.split('/')[-1],
            asset_content['displayName']['text']
        )
        self.assertEqual(asset_content['genusTypeId'], thumbnail_genus)

    def test_can_update_asset_content_name_and_description(self):
        req = self.app.get(self.url)
        self.ok(req)
        asset_content = self.asset.get_asset_contents().next()
        original_genus_type = str(asset_content.genus_type)
        original_file_name = asset_content.display_name.text
        original_on_disk_name = asset_content.get_url()
        original_id = str(asset_content.ident)

        thumbnail_genus = "asset-content-genus%3Athumbnail%40ODL.MIT.EDU"
        new_name = "foobar"
        new_description = "a small image"
        req = self.app.put(self.url,
                           params=json.dumps({
                               "genusTypeId": thumbnail_genus,
                               "displayName": new_name,
                               "description": new_description
                           }),
                           headers={"content-type": "application/json"})
        self.ok(req)
        data = self.json(req)
        asset_content = data['assetContents'][0]
        self.assertNotEqual(
            original_genus_type,
            asset_content['genusTypeId']
        )
        self.assertNotEqual(
            original_file_name,
            asset_content['displayName']['text']
        )
        self.assertEqual(
            original_on_disk_name.split('.')[0],
            asset_content['url'].split('.')[0]
        )
        self.assertEqual(
            original_id,
            asset_content['id']
        )
        self.assertEqual(
            new_name,
            asset_content['displayName']['text']
        )
        self.assertEqual(
            new_description,
            asset_content['description']['text']
        )
        self.assertEqual(asset_content['genusTypeId'], thumbnail_genus)

    def test_updated_asset_content_in_question_shows_up_properly_in_item_qti(self):
        item = self.create_item_with_image()
        taken, offered = self.create_taken_for_item(self._repo.ident, Id(item['id']))
        url = '{0}/assessmentstaken/{1}/questions?qti'.format(self.assessment_url,
                                                              unquote(str(taken.ident)))

        req = self.app.get(url)
        self.ok(req)
        data = self.json(req)['data']
        soup = BeautifulSoup(data[0]['qti'], 'xml')
        image = soup.find('img')

        req = self.app.get(image['src'])
        self.ok(req)
        headers = req.header_dict
        self.assertIn('image/png', headers['content-type'])
        self.assertIn('.png', headers['content-disposition'])
        original_content_length = headers['content-length']

        # need to get rid of the /stream part of the path to just get the content details URL
        content_url = image['src'].replace('/stream', '')
        self._logo_upload_test_file.seek(0)
        req = self.app.put(content_url,
                           upload_files=[('inputFile',
                                          self._filename(self._logo_upload_test_file),
                                          self._logo_upload_test_file.read())])
        self.ok(req)

        req = self.app.get(url)
        self.ok(req)
        data = self.json(req)['data']
        soup = BeautifulSoup(data[0]['qti'], 'xml')
        image = soup.find('img')

        req = self.app.get(image['src'])
        self.ok(req)
        headers = req.header_dict
        self.assertNotIn('image/png', headers['content-type'])
        self.assertIn('.sltng', headers['content-disposition'])
        self.assertNotEqual(original_content_length, headers['content-length'])

    def test_updated_asset_content_in_choices_shows_up_properly_in_item_qti(self):
        item = self.create_item_with_image_in_choices()
        taken, offered = self.create_taken_for_item(self._repo.ident, Id(item['id']))
        url = '{0}/assessmentstaken/{1}/questions?qti'.format(self.assessment_url,
                                                              unquote(str(taken.ident)))

        req = self.app.get(url)
        self.ok(req)
        data = self.json(req)['data']
        soup = BeautifulSoup(data[0]['qti'], 'xml')
        image = soup.find('img')

        req = self.app.get(image['src'])
        self.ok(req)
        headers = req.header_dict
        self.assertIn('image/png', headers['content-type'])
        self.assertIn('.png', headers['content-disposition'].lower())
        original_content_length = headers['content-length']

        # need to get rid of the /stream part of the path to just get the content details URL
        content_url = image['src'].replace('/stream', '')
        self._logo_upload_test_file.seek(0)
        req = self.app.put(content_url,
                           upload_files=[('inputFile',
                                          self._filename(self._logo_upload_test_file),
                                          self._logo_upload_test_file.read())])
        self.ok(req)

        req = self.app.get(url)
        self.ok(req)
        data = self.json(req)['data']
        soup = BeautifulSoup(data[0]['qti'], 'xml')
        image = soup.find('img')

        req = self.app.get(image['src'])
        self.ok(req)
        headers = req.header_dict
        self.assertNotIn('image/png', headers['content-type'])
        self.assertIn('.sltng', headers['content-disposition'])
        self.assertNotEqual(original_content_length, headers['content-length'])

    def test_can_set_asset_content_display_name_and_description_to_foreign_language(self):
        req = self.app.get(self.url)
        self.ok(req)
        asset_content = self.asset.get_asset_contents().next()
        original_genus_type = str(asset_content.genus_type)
        original_file_name = asset_content.display_name.text
        original_on_disk_name = asset_content.get_url()
        original_id = str(asset_content.ident)

        description_genus = "asset-content-genus%3Adescription%40ODL.MIT.EDU"
        new_name = self._hindi_text
        new_description = self._hindi_text
        req = self.app.put(self.url,
                           params=json.dumps({
                               "genusTypeId": description_genus,
                               "displayName": new_name,
                               "description": new_description
                           }),
                           headers=self._hindi_headers())
        self.ok(req)
        data = self.json(req)
        asset_content = data['assetContents'][0]
        self.assertNotEqual(
            original_genus_type,
            asset_content['genusTypeId']
        )
        self.assertNotEqual(
            original_file_name,
            asset_content['displayName']['text']
        )
        self.assertEqual(
            original_on_disk_name.split('.')[0],
            asset_content['url'].split('.')[0]
        )
        self.assertEqual(
            original_id,
            asset_content['id']
        )
        self.assertEqual(
            new_name,
            asset_content['displayName']['text']
        )
        self.assertEqual(
            self._hindi_language_type,
            asset_content['displayName']['languageTypeId']
        )
        self.assertEqual(
            self._hindi_script_type,
            asset_content['displayName']['scriptTypeId']
        )
        self.assertEqual(
            new_description,
            asset_content['description']['text']
        )
        self.assertEqual(
            self._hindi_language_type,
            asset_content['description']['languageTypeId']
        )
        self.assertEqual(
            self._hindi_script_type,
            asset_content['description']['scriptTypeId']
        )
        self.assertEqual(asset_content['genusTypeId'], description_genus)

    def test_can_get_asset_content_display_name_and_description_in_foreign_language(self):
        req = self.app.get(self.url)
        self.ok(req)
        asset_content = self.asset.get_asset_contents().next()
        original_file_name = asset_content.display_name.text
        original_description = asset_content.description.text

        description_genus = "asset-content-genus%3Adescription%40ODL.MIT.EDU"
        new_name = self._hindi_text
        new_description = self._hindi_text
        req = self.app.put(self.url,
                           params=json.dumps({
                               "genusTypeId": description_genus,
                               "displayName": new_name,
                               "description": new_description
                           }),
                           headers=self._hindi_headers())
        self.ok(req)

        asset_url = '/api/v1/repository/repositories/{0}/assets/{1}'.format(unquote(str(self._repo.ident)),
                                                                            unquote(str(self.asset.ident)))

        req = self.app.get(asset_url,
                           headers=self._english_headers())
        self.ok(req)
        data = self.json(req)
        asset_content = data['assetContents'][0]

        self.assertEqual(
            asset_content['displayName']['text'],
            original_file_name
        )
        self.assertEqual(
            asset_content['displayName']['languageTypeId'],
            self._english_language_type
        )
        self.assertEqual(
            asset_content['displayName']['scriptTypeId'],
            self._english_script_type
        )
        self.assertEqual(
            asset_content['description']['text'],
            original_description
        )
        self.assertEqual(
            asset_content['description']['languageTypeId'],
            self._english_language_type
        )
        self.assertEqual(
            asset_content['description']['scriptTypeId'],
            self._english_script_type
        )

        req = self.app.get(asset_url,
                           headers=self._hindi_headers())
        self.ok(req)
        data = self.json(req)
        asset_content = data['assetContents'][0]
        self.assertEqual(
            asset_content['displayName']['text'],
            new_name
        )
        self.assertEqual(
            asset_content['displayName']['languageTypeId'],
            self._hindi_language_type
        )
        self.assertEqual(
            asset_content['displayName']['scriptTypeId'],
            self._hindi_script_type
        )
        self.assertEqual(
            asset_content['description']['text'],
            new_description
        )
        self.assertEqual(
            asset_content['description']['languageTypeId'],
            self._hindi_language_type
        )
        self.assertEqual(
            asset_content['description']['scriptTypeId'],
            self._hindi_script_type
        )

    def test_can_get_asset_contents_list(self):
        asset_content = self.asset.get_asset_contents().next()
        req = self.app.get(self.contents_url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], str(asset_content.ident))
        self.assertNotIn('/api/v1', data[0]['url'])

    def test_can_get_asset_contents_list_with_full_urls(self):
        asset_content = self.asset.get_asset_contents().next()
        req = self.app.get(self.contents_url + '?fullUrls')
        self.ok(req)
        data = self.json(req)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], str(asset_content.ident))
        self.assertIn('/api/v1', data[0]['url'])

    def test_can_add_new_asset_content_with_file(self):
        self._replacement_image_file.seek(0)
        payload = {
            "displayName": 'foo'
        }
        # Paste complains if you use unicode in the payload here,
        # so we'll test unicode language in a different test
        req = self.app.post(self.contents_url,
                            params=payload,
                            upload_files=[('inputFile',
                                           self._filename(self._replacement_image_file),
                                           self._replacement_image_file.read())],
                            headers={'x-api-locale': 'hi'})
        self.ok(req)
        data = self.json(req)
        self.assertEqual(data['assetId'], str(self.asset.ident))
        asset = self._repo.get_asset(self.asset.ident)

        self.assertEqual(asset.get_asset_contents().available(), 2)
        contents = asset.get_asset_contents()
        contents.next()
        self.assertEqual(str(contents.next().ident),
                         data['id'])
        self.assertEqual(data['displayName']['text'],
                         'foo')
        self.assertEqual(data['displayName']['languageTypeId'],
                         self._hindi_language_type)
        self.assertNotIn('/api/v1', data['url'])

    def test_can_add_new_asset_content_in_non_english_language(self):
        payload = {
            "displayName": self._hindi_text
        }
        req = self.app.post(self.contents_url,
                            params=json.dumps(payload),
                            headers=self._hindi_headers())
        self.ok(req)
        data = self.json(req)
        self.assertEqual(data['assetId'], str(self.asset.ident))
        asset = self._repo.get_asset(self.asset.ident)

        self.assertEqual(asset.get_asset_contents().available(), 2)
        contents = asset.get_asset_contents()
        contents.next()
        self.assertEqual(str(contents.next().ident),
                         data['id'])
        self.assertEqual(data['displayName']['text'],
                         self._hindi_text)
        self.assertEqual(data['displayName']['languageTypeId'],
                         self._hindi_language_type)
        self.assertNotIn('/api/v1', data['url'])
        self.assertIn('displayNames', data)

    def test_can_add_new_asset_content_with_json_only(self):
        payload = {
            "displayName": 'foo'
        }
        req = self.app.post(self.contents_url,
                            params=json.dumps(payload),
                            headers={"content-type": "application/json"})
        self.ok(req)
        data = self.json(req)
        self.assertEqual(data['assetId'], str(self.asset.ident))
        asset = self._repo.get_asset(self.asset.ident)

        self.assertEqual(asset.get_asset_contents().available(), 2)
        contents = asset.get_asset_contents()
        contents.next()
        self.assertEqual(str(contents.next().ident),
                         data['id'])
        self.assertEqual(data['displayName']['text'],
                         'foo')
        self.assertNotIn('/api/v1', data['url'])

    def test_can_add_new_asset_with_file_with_full_url(self):
        self._replacement_image_file.seek(0)
        payload = {
            "displayName": 'foo',
            "fullUrl": True
        }
        # Paste complains if you use unicode in the payload here,
        # so we'll test unicode language in a different test
        req = self.app.post(self.contents_url,
                            params=payload,
                            upload_files=[('inputFile',
                                           self._filename(self._replacement_image_file),
                                           self._replacement_image_file.read())],
                            headers={'x-api-locale': 'hi'})
        self.ok(req)
        data = self.json(req)
        self.assertEqual(data['assetId'], str(self.asset.ident))
        asset = self._repo.get_asset(self.asset.ident)

        self.assertEqual(asset.get_asset_contents().available(), 2)
        contents = asset.get_asset_contents()
        contents.next()
        self.assertEqual(str(contents.next().ident),
                         data['id'])
        self.assertEqual(data['displayName']['text'],
                         'foo')
        self.assertEqual(data['displayName']['languageTypeId'],
                         self._hindi_language_type)
        self.assertIn('/api/v1', data['url'])


class AssetQueryTests(BaseRepositoryTestCase):
    def setUp(self):
        super(AssetQueryTests, self).setUp()
        self.url = '{0}/repositories/{1}/assets'.format(self.url,
                                                        unquote(str(self._repo.ident)))

        self._video_upload_test_file = open('{0}/tests/files/video-js-test.mp4'.format(ABS_PATH), 'r')
        self._caption_upload_test_file = open('{0}/tests/files/video-js-test-en.vtt'.format(ABS_PATH), 'r')

    def tearDown(self):
        """
        Remove the test user from all groups in Membership
        Start from the smallest groupId because need to
        remove "parental" roles like for DepartmentAdmin / DepartmentOfficer
        """
        super(AssetQueryTests, self).tearDown()

        self._video_upload_test_file.close()
        self._caption_upload_test_file.close()

    def test_can_get_assets_with_valid_content_urls(self):
        self._video_upload_test_file.seek(0)
        req = self.app.post(self.url,
                            upload_files=[('inputFile', 'video-js-test.mp4', self._video_upload_test_file.read())])
        self.ok(req)
        data = self.json(req)

        self._caption_upload_test_file.seek(0)
        req = self.app.post(self.url,
                            upload_files=[('inputFile', 'video-js-test-en.vtt', self._caption_upload_test_file.read())])
        self.ok(req)

        url = '{0}?fullUrls'.format(self.url)
        req = self.app.get(url)
        self.ok(req)
        data = self.json(req)

        self.assertEqual(len(data), 1)
        asset = data[0]
        self.assertEqual(
            len(asset['assetContents']),
            2
        )

        for index, asset_content in enumerate(asset['assetContents']):
            if index == 0:
                self.assertEqual(
                    asset_content['genusTypeId'],
                    'asset-content-genus-type%3Amp4%40ODL.MIT.EDU'
                )
            else:
                self.assertEqual(
                    asset_content['genusTypeId'],
                    'asset-content-genus-type%3Avtt%40ODL.MIT.EDU'
                )
            self.assertNotIn(
                'datastore/repository/AssetContent/',
                asset_content['url']
            )
            self.assertEqual(
                '/api/v1/repository/repositories/{0}/assets/{1}/contents/{2}/stream'.format(asset['assignedRepositoryIds'][0],
                                                                                            asset['id'],
                                                                                            asset_content['id']),
                asset_content['url']
            )


class AssetCRUDTests(BaseRepositoryTestCase):
    def setUp(self):
        super(AssetCRUDTests, self).setUp()
        self.url = '{0}/repositories/{1}/assets'.format(self.url,
                                                        unquote(str(self._repo.ident)))

        self._video_upload_test_file = open('{0}/tests/files/video-js-test.mp4'.format(ABS_PATH), 'r')
        self._caption_upload_test_file = open('{0}/tests/files/video-js-test-en.vtt'.format(ABS_PATH), 'r')

    def tearDown(self):
        """
        Remove the test user from all groups in Membership
        Start from the smallest groupId because need to
        remove "parental" roles like for DepartmentAdmin / DepartmentOfficer
        """
        super(AssetCRUDTests, self).tearDown()

        self._video_upload_test_file.close()
        self._caption_upload_test_file.close()

    def test_can_upload_video_files_to_repository(self):
        self._video_upload_test_file.seek(0)
        req = self.app.post(self.url,
                            upload_files=[('inputFile', 'video-js-test.mp4', self._video_upload_test_file.read())])
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['assetContents']),
            1
        )
        self.assertEqual(
            data['assetContents'][0]['genusTypeId'],
            'asset-content-genus-type%3Amp4%40ODL.MIT.EDU'
        )

        # because this is hidden / stripped out
        self.assertNotIn(
            'asset_content_record_type%3Afilesystem%40odl.mit.edu',
            data['recordTypeIds']
        )
        self.assertIn(
            'datastore/repository/AssetContent/',
            data['assetContents'][0]['url']
        )
        self.assertEqual(
            'video-js-test.mp4',
            data['assetContents'][0]['displayName']['text']
        )

    def test_can_create_asset_with_flag_to_return_valid_url(self):
        self._video_upload_test_file.seek(0)
        req = self.app.post(self.url,
                            params={'returnUrl': True},
                            upload_files=[('inputFile', 'video-js-test.mp4', self._video_upload_test_file.read())])
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['assetContents']),
            1
        )
        self.assertEqual(
            data['assetContents'][0]['genusTypeId'],
            'asset-content-genus-type%3Amp4%40ODL.MIT.EDU'
        )

        # because this is hidden / stripped out
        self.assertNotIn(
            'asset_content_record_type%3Afilesystem%40odl.mit.edu',
            data['recordTypeIds']
        )
        self.assertNotIn(
            'datastore/repository/AssetContent/',
            data['assetContents'][0]['url']
        )
        self.assertEqual(
            '/api/v1/repository/repositories/{0}/assets/{1}/contents/{2}/stream'.format(data['assignedRepositoryIds'][0],
                                                                                        data['id'],
                                                                                        data['assetContents'][0]['id']),
            data['assetContents'][0]['url']
        )
        self.assertEqual(
            'video-js-test.mp4',
            data['assetContents'][0]['displayName']['text']
        )

    def test_can_upload_caption_vtt_files_to_repository(self):
        self._caption_upload_test_file.seek(0)
        req = self.app.post(self.url,
                            upload_files=[('inputFile', 'video-js-test-en.vtt', self._caption_upload_test_file.read())])
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['assetContents']),
            1
        )
        self.assertEqual(
            data['assetContents'][0]['genusTypeId'],
            'asset-content-genus-type%3Avtt%40ODL.MIT.EDU'
        )

        # because this is hidden / stripped out
        self.assertNotIn(
            'asset_content_record_type%3Afilesystem%40odl.mit.edu',
            data['recordTypeIds']
        )
        self.assertIn(
            'datastore/repository/AssetContent/',
            data['assetContents'][0]['url']
        )
        self.assertEqual(
            'video-js-test-en.vtt',
            data['assetContents'][0]['displayName']['text']
        )

    def test_caption_and_video_files_uploaded_as_asset_contents_on_same_asset(self):
        self._video_upload_test_file.seek(0)
        req = self.app.post(self.url,
                            upload_files=[('inputFile', 'video-js-test.mp4', self._video_upload_test_file.read())])
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['assetContents']),
            1
        )
        asset_id = data['id']
        self.assertEqual(
            data['displayName']['text'],
            'video_js_test'
        )

        self._caption_upload_test_file.seek(0)
        req = self.app.post(self.url,
                            upload_files=[('inputFile', 'video-js-test-en.vtt', self._caption_upload_test_file.read())])
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['assetContents']),
            2
        )
        self.assertEqual(
            asset_id,
            data['id']
        )
        self.assertEqual(
            data['displayName']['text'],
            'video_js_test'
        )

        self.assertEqual(
            data['assetContents'][0]['genusTypeId'],
            'asset-content-genus-type%3Amp4%40ODL.MIT.EDU'
        )
        self.assertIn(
            'datastore/repository/AssetContent/',
            data['assetContents'][0]['url']
        )
        self.assertEqual(
            'video-js-test.mp4',
            data['assetContents'][0]['displayName']['text']
        )

        self.assertEqual(
            data['assetContents'][1]['genusTypeId'],
            'asset-content-genus-type%3Avtt%40ODL.MIT.EDU'
        )
        self.assertIn(
            'datastore/repository/AssetContent/',
            data['assetContents'][1]['url']
        )
        self.assertEqual(
            'video-js-test-en.vtt',
            data['assetContents'][1]['displayName']['text']
        )

    def test_can_provide_license_on_upload(self):
        self._video_upload_test_file.seek(0)
        license_ = "BSD"
        req = self.app.post(self.url,
                            params={"license": license_},
                            upload_files=[('inputFile', 'video-js-test.mp4', self._video_upload_test_file.read())])
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            data['license']['text'],
            license_
        )

    def test_can_provide_copyright_on_upload(self):
        self._video_upload_test_file.seek(0)
        copyright_ = "CC BY"
        req = self.app.post(self.url,
                            params={"copyright": copyright_},
                            upload_files=[('inputFile', 'video-js-test.mp4', self._video_upload_test_file.read())])
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            data['copyright']['text'],
            copyright_
        )

    def test_can_update_asset_with_license(self):
        self._video_upload_test_file.seek(0)
        license_ = "BSD"
        req = self.app.post(self.url,
                            upload_files=[('inputFile', 'video-js-test.mp4', self._video_upload_test_file.read())])
        self.ok(req)
        data = self.json(req)
        asset_id = data['id']
        self.assertEqual(
            data['license']['text'],
            ''
        )

        payload = {
            "license": license_
        }
        url = '{0}/{1}'.format(self.url,
                               asset_id)
        req = self.app.put(url,
                           params=json.dumps(payload),
                           headers={'content-type': 'application/json'})
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            data['license']['text'],
            license_
        )

    def test_can_update_asset_with_copyright(self):
        self._video_upload_test_file.seek(0)
        copyright_ = "CC BY"
        req = self.app.post(self.url,
                            upload_files=[('inputFile', 'video-js-test.mp4', self._video_upload_test_file.read())])
        self.ok(req)
        data = self.json(req)
        asset_id = data['id']
        self.assertEqual(
            data['copyright']['text'],
            ''
        )

        payload = {
            "copyright": copyright_
        }
        url = '{0}/{1}'.format(self.url,
                               asset_id)
        req = self.app.put(url,
                           params=json.dumps(payload),
                           headers={'content-type': 'application/json'})
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            data['copyright']['text'],
            copyright_
        )

    def test_can_update_asset_name(self):
        self._video_upload_test_file.seek(0)
        req = self.app.post(self.url,
                            upload_files=[('inputFile', 'video-js-test.mp4', self._video_upload_test_file.read())])
        self.ok(req)
        data = self.json(req)
        asset_id = data['id']
        original_name = data['displayName']['text']
        new_name = "foobar"
        self.assertNotEqual(original_name, new_name)

        payload = {
            "displayName": new_name
        }
        url = '{0}/{1}'.format(self.url,
                               asset_id)
        req = self.app.put(url,
                           params=json.dumps(payload),
                           headers={'content-type': 'application/json'})
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            data['displayName']['text'],
            new_name
        )

    def test_can_update_asset_description(self):
        self._video_upload_test_file.seek(0)
        req = self.app.post(self.url,
                            upload_files=[('inputFile', 'video-js-test.mp4', self._video_upload_test_file.read())])
        self.ok(req)
        data = self.json(req)
        asset_id = data['id']
        original_description = data['displayName']['text']
        new_description = "foobar"
        self.assertNotEqual(original_description, new_description)

        payload = {
            "description": new_description
        }
        url = '{0}/{1}'.format(self.url,
                               asset_id)
        req = self.app.put(url,
                           params=json.dumps(payload),
                           headers={'content-type': 'application/json'})
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            data['description']['text'],
            new_description
        )

    def test_can_get_asset_with_content_urls(self):
        self._video_upload_test_file.seek(0)
        req = self.app.post(self.url,
                            upload_files=[('inputFile', 'video-js-test.mp4', self._video_upload_test_file.read())])
        self.ok(req)
        data = self.json(req)
        asset_id = data['id']
        url = '{0}/{1}?fullUrls'.format(self.url,
                                        asset_id)
        req = self.app.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            '/api/v1/repository/repositories/{0}/assets/{1}/contents/{2}/stream'.format(data['assignedRepositoryIds'][0],
                                                                                        data['id'],
                                                                                        data['assetContents'][0]['id']),
            data['assetContents'][0]['url']
        )
