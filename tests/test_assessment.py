import json

from dlkit_edx.primordium import Id, Type

from nose.tools import *

from paste.fixture import AppError

from records.registry import ITEM_GENUS_TYPES, ITEM_RECORD_TYPES,\
    ANSWER_RECORD_TYPES, QUESTION_RECORD_TYPES, ANSWER_GENUS_TYPES,\
    ASSESSMENT_OFFERED_RECORD_TYPES, ASSESSMENT_TAKEN_RECORD_TYPES

from testing_utilities import BaseTestCase, get_managers, create_test_bank
from urllib import unquote, quote

import utilities

EDX_ITEM_RECORD_TYPE = Type(**ITEM_RECORD_TYPES['edx_item'])
NUMERIC_RESPONSE_ITEM_GENUS_TYPE = Type(**ITEM_GENUS_TYPES['numeric-response-edx'])
NUMERIC_RESPONSE_ANSWER_RECORD_TYPE = Type(**ANSWER_RECORD_TYPES['numeric-response-edx'])
NUMERIC_RESPONSE_QUESTION_RECORD_TYPE = Type(**QUESTION_RECORD_TYPES['numeric-response-edx'])

REVIEWABLE_OFFERED = Type(**ASSESSMENT_OFFERED_RECORD_TYPES['review-options'])
REVIEWABLE_TAKEN = Type(**ASSESSMENT_TAKEN_RECORD_TYPES['review-options'])


class BaseAssessmentTestCase(BaseTestCase):
    def create_assessment_offered_for_item(self, bank_id, item_id):
        if isinstance(bank_id, basestring):
            bank_id = utilities.clean_id(bank_id)
        if isinstance(item_id, basestring):
            item_id = utilities.clean_id(item_id)

        bank = get_managers()['am'].get_bank(bank_id)
        form = bank.get_assessment_form_for_create([])
        form.display_name = 'a test assessment'
        form.description = 'for testing with'
        new_assessment = bank.create_assessment(form)

        bank.add_item(new_assessment.ident, item_id)

        form = bank.get_assessment_offered_form_for_create(new_assessment.ident,
                                                           [REVIEWABLE_OFFERED])
        new_offered = bank.create_assessment_offered(form)

        return new_offered

    def create_item(self, bank_id):
        if isinstance(bank_id, basestring):
            bank_id = utilities.clean_id(bank_id)

        bank = get_managers()['am'].get_bank(bank_id)
        form = bank.get_item_form_for_create([EDX_ITEM_RECORD_TYPE])
        form.display_name = 'a test item!'
        form.description = 'for testing with'
        form.set_genus_type(NUMERIC_RESPONSE_ITEM_GENUS_TYPE)
        new_item = bank.create_item(form)

        form = bank.get_question_form_for_create(item_id=new_item.ident,
                                                 question_record_types=[NUMERIC_RESPONSE_QUESTION_RECORD_TYPE])
        form.set_text('foo?')
        bank.create_question(form)

        self.right_answer = float(2.04)
        self.tolerance = float(0.71)
        form = bank.get_answer_form_for_create(item_id=new_item.ident,
                                               answer_record_types=[NUMERIC_RESPONSE_ANSWER_RECORD_TYPE])
        form.set_decimal_value(self.right_answer)
        form.set_tolerance_value(self.tolerance)

        bank.create_answer(form)

        return bank.get_item(new_item.ident)

    def create_taken_for_item(self, bank_id, item_id):
        if isinstance(bank_id, basestring):
            bank_id = utilities.clean_id(bank_id)
        if isinstance(item_id, basestring):
            item_id = utilities.clean_id(item_id)

        bank = get_managers()['am'].get_bank(bank_id)

        new_offered = self.create_assessment_offered_for_item(bank_id, item_id)

        form = bank.get_assessment_taken_form_for_create(new_offered.ident,
                                                         [REVIEWABLE_TAKEN])
        taken = bank.create_assessment_taken(form)
        return taken, new_offered

    def extract_answers(self, item):
        """
        Extract the answer part of an item
        """
        if 'answers' in item:
            return item['answers']
        else:
            return item[0]['answers']

    def extract_question(self, item):
        """
        Extract the question part of an item
        """
        if 'question' in item:
            return item['question']
        else:
            return item[0]['question']

    def setUp(self):
        super(BaseAssessmentTestCase, self).setUp()
        self.url = '/api/v1/assessment'
        self._bank = create_test_bank()

    def tearDown(self):
        super(BaseAssessmentTestCase, self).tearDown()

    def verify_no_data(self, _req):
        """
        Verify that the data object in _req is empty
        """
        data = json.loads(_req.body)
        self.assertEqual(
            data,
            []
        )

    def verify_offerings(self, _req, _type, _data):
        """
        Check that the offerings match...
        _type may not be used here; assume AssessmentOffered always?
        _data objects need to have an offering ID in them
        """
        def check_expected_against_one_item(expected, item):
            for key, value in expected.iteritems():
                if isinstance(value, basestring):
                    if key == 'name':
                        self.assertEqual(
                            item['displayName']['text'],
                            value
                        )
                    elif key == 'description':
                        self.assertEqual(
                            item['description']['text'],
                            value
                        )
                    else:
                        self.assertEqual(
                            item[key],
                            value
                        )
                elif isinstance(value, dict):
                    for inner_key, inner_value in value.iteritems():
                        self.assertEqual(
                            item[key][inner_key],
                            inner_value
                        )

        data = json.loads(_req.body)
        if 'data' in data:
            data = data['data']['results']
        elif 'results' in data:
            data = data['results']

        if isinstance(_data, list):
            for expected in _data:
                if isinstance(data, list):
                    for item in data:
                        if item['id'] == expected['id']:
                            check_expected_against_one_item(expected, item)
                            break
                else:
                    check_expected_against_one_item(expected, data)
        elif isinstance(_data, dict):
            if isinstance(data, list):
                for item in data:
                    if item['id'] == _data['id']:
                        check_expected_against_one_item(_data, item)
                        break
            else:
                check_expected_against_one_item(_data, data)

    def verify_question(self, _data, _q_str, _q_type):
        """
        verify just the question part of an item. Should allow you to pass
        in either a request response or a json object...load if needed
        """
        try:
            try:
                data = json.loads(_data.body)
            except:
                data = json.loads(_data)
        except:
            data = _data
        if 'question' in data:
            question = data['question']
        elif isinstance(data, list):
            try:
                question = data[0]['question']
            except:
                question = data[0]
        else:
            question = data

        self.assertEqual(
            question['text']['text'],
            _q_str
        )
        self.assertIn(
            _q_type,
            question['recordTypeIds']
        )

    def verify_submission(self, _req, _expected_result, _has_next=None):
        data = json.loads(_req.body)
        self.assertEqual(
            data['correct'],
            _expected_result
        )
        if _has_next:
            self.assertEqual(
                data['hasNext'],
                _has_next
            )

    def verify_text(self, _req, _type, _name, _desc, _id=None, _genus=None):
        """
        helper method to verify the text in a returned object
        takes care of all the language stuff
        """
        req = json.loads(_req.body)
        if _id:
            data = None
            if isinstance(req, list):
                for item in req:
                    if (item['id'] == _id or
                        item['id'] == quote(_id)):
                        data = item
            elif isinstance(req, dict):
                if (req['id'] == _id or
                        req['id'] == quote(_id)):
                    data = req
            if not data:
                raise LookupError('Item with id: ' + _id + ' not found.')
        else:
            data = req
        self.assertEqual(
            data['displayName']['text'],
            _name
        )
        self.assertEqual(
            data['description']['text'],
            _desc
        )
        self.assertEqual(
            data['type'],
            _type
        )

        if _genus:
            self.assertEqual(
                data['genusTypeId'],
                _genus
            )


class AnswerTypeTests(BaseAssessmentTestCase):
    def item_payload(self):
        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_body = 'can you manipulate this?'
        question_choices = [
            'yes',
            'no',
            'maybe'
        ]
        question_type = 'question-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        answer = 2
        answer_type = 'answer-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'

        return {
            "name"                  : item_name,
            "description"           : item_desc,
            "question"              : {
                "type"           : question_type,
                "questionString" : question_body,
                "choices"        : question_choices
            },
            "answers"               : [{
                "type"      : answer_type,
                "choiceId"  : answer
            }],
        }

    def setUp(self):
        super(AnswerTypeTests, self).setUp()
        self.url += '/banks/' + unquote(str(self._bank.ident)) + '/items'

    def tearDown(self):
        """
        Remove the test user from all groups in Membership
        Start from the smallest groupId because need to
        remove "parental" roles like for DepartmentAdmin / DepartmentOfficer
        """
        super(AnswerTypeTests, self).tearDown()

    def test_can_explicitly_set_right_answer(self):
        payload = self.item_payload()
        payload['answers'][0].update({
            'genus': str(Type(**ANSWER_GENUS_TYPES['right-answer']))
        })

        req = self.app.post(self.url,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        item = self.json(req)
        self.assertEqual(
            item['answers'][0]['genusTypeId'],
            str(Type(**ANSWER_GENUS_TYPES['right-answer']))
        )

    def test_default_answer_genus_is_right_answer_when_not_specified(self):
        payload = self.item_payload()

        req = self.app.post(self.url,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        item = self.json(req)
        self.assertEqual(
            item['answers'][0]['genusTypeId'],
            str(Type(**ANSWER_GENUS_TYPES['right-answer']))
        )

    def test_can_set_wrong_answers_when_creating_answer(self):
        payload = self.item_payload()
        payload['answers'][0].update({
            'genus': str(Type(**ANSWER_GENUS_TYPES['wrong-answer']))
        })

        req = self.app.post(self.url,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        item = self.json(req)
        self.assertEqual(
            item['answers'][0]['genusTypeId'],
            str(Type(**ANSWER_GENUS_TYPES['wrong-answer']))
        )

    def test_can_change_answer_genus_from_wrong_to_right(self):
        payload = self.item_payload()
        payload['answers'][0].update({
            'genus': str(Type(**ANSWER_GENUS_TYPES['wrong-answer']))
        })

        req = self.app.post(self.url,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        item = self.json(req)

        self.assertEqual(
            item['answers'][0]['genusTypeId'],
            payload['answers'][0]['genus']
        )

        item_id = unquote(item['id'])
        answer_id = unquote(item['answers'][0]['id'])
        item_details_endpoint = '{0}/{1}'.format(self.url,
                                                 item_id)
        updated_payload = {
            'answers': [{
                'genus': str(Type(**ANSWER_GENUS_TYPES['right-answer'])),
                'id': answer_id,
                'type': payload['answers'][0]['type']
            }]
        }
        req = self.app.put(item_details_endpoint,
                           params=json.dumps(updated_payload),
                           headers={'content-type': 'application/json'})
        self.ok(req)
        updated_answer = self.json(req)['answers'][0]
        self.assertEqual(
            updated_answer['genusTypeId'],
            updated_payload['answers'][0]['genus']
        )

    def test_can_change_answer_genus_from_right_to_wrong(self):
        payload = self.item_payload()

        req = self.app.post(self.url,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        item = self.json(req)

        self.assertEqual(
            item['answers'][0]['genusTypeId'],
            str(Type(**ANSWER_GENUS_TYPES['right-answer']))
        )

        item_id = unquote(item['id'])
        answer_id = unquote(item['answers'][0]['id'])
        item_details_endpoint = '{0}/{1}'.format(self.url,
                                                 item_id)
        updated_payload = {
            'answers': [{
                'genus': str(Type(**ANSWER_GENUS_TYPES['wrong-answer'])),
                'id': answer_id,
                'feedback': 'bazz',
                'type': payload['answers'][0]['type']
            }]
        }

        req = self.app.put(item_details_endpoint,
                           params=json.dumps(updated_payload),
                           headers={'content-type': 'application/json'})
        self.ok(req)
        updated_answer = self.json(req)['answers'][0]
        self.assertEqual(
            updated_answer['genusTypeId'],
            updated_payload['answers'][0]['genus']
        )
        self.assertEqual(
            updated_answer['texts']['feedback'],
            updated_payload['answers'][0]['feedback']
        )

    def test_can_edit_feedback_for_wrong_answers(self):
        payload = self.item_payload()
        payload['answers'][0].update({
            'genus': str(Type(**ANSWER_GENUS_TYPES['wrong-answer']))
        })

        req = self.app.post(self.url,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        item = self.json(req)

        self.assertEqual(
            item['answers'][0]['genusTypeId'],
            payload['answers'][0]['genus']
        )

        self.assertNotIn(
            'feedback',
            item['answers'][0]['texts']
        )

        item_id = unquote(item['id'])
        answer_id = unquote(item['answers'][0]['id'])
        item_details_endpoint = '{0}/{1}'.format(self.url,
                                                 item_id)
        updated_payload = {
            'answers': [{
                'genus': str(Type(**ANSWER_GENUS_TYPES['wrong-answer'])),
                'id': answer_id,
                'feedback': 'bazz',
                'type': payload['answers'][0]['type']
            }]
        }

        req = self.app.put(item_details_endpoint,
                           params=json.dumps(updated_payload),
                           headers={'content-type': 'application/json'})
        self.ok(req)
        updated_answer = self.json(req)['answers'][0]

        self.assertEqual(
            updated_answer['genusTypeId'],
            updated_payload['answers'][0]['genus']
        )
        self.assertEqual(
            updated_answer['texts']['feedback'],
            updated_payload['answers'][0]['feedback']
        )

    def test_can_add_wrong_answers_when_updating_item(self):
        payload = self.item_payload()

        req = self.app.post(self.url,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        item_id = self.json(req)['id']

        new_answer_payload = {
            'answers': [{
                'genus': str(Type(**ANSWER_GENUS_TYPES['wrong-answer'])),
                'type': payload['answers'][0]['type'],
                'choiceId': 1
            }]
        }

        item_details_endpoint = self.url + '/' + unquote(item_id)
        req = self.app.put(item_details_endpoint,
                           params=json.dumps(new_answer_payload),
                           headers={'content-type': 'application/json'})
        self.ok(req)
        updated_item = self.json(req)
        self.assertEqual(
            len(updated_item['answers']),
            2
        )

        new_answer = [a for a in updated_item['answers']
                      if a['genusTypeId'] == new_answer_payload['answers'][0]['genus']][0]
        self.assertEqual(
            new_answer['choiceIds'][0],
            updated_item['question']['choices'][0]['id']
        )

    def test_can_set_feedback_text_on_wrong_answer_on_item_create(self):
        payload = self.item_payload()
        payload['answers'][0].update({
            'genus': str(Type(**ANSWER_GENUS_TYPES['wrong-answer'])),
            'feedback': 'foobar'
        })

        req = self.app.post(self.url,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        item = self.json(req)
        self.assertEqual(
            item['answers'][0]['genusTypeId'],
            str(Type(**ANSWER_GENUS_TYPES['wrong-answer']))
        )
        self.assertEqual(
            item['answers'][0]['texts']['feedback'],
            payload['answers'][0]['feedback']
        )

    def test_feedback_returned_when_student_submits_wrong_answer(self):
        payload = self.item_payload()
        payload['answers'][0].update({
            'genus': str(Type(**ANSWER_GENUS_TYPES['wrong-answer'])),
            'feedback': 'what a novel idea'
        })

        req = self.app.post(self.url,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        item = self.json(req)

        self.assertEqual(
            item['answers'][0]['texts']['feedback'],
            payload['answers'][0]['feedback']
        )

        item_id = item['id']
        wrong_choice_id = item['question']['choices'][1]['id']

        taken, offered = self.create_taken_for_item(self._bank.ident, item_id)

        url = '/api/v1/assessment/banks/{0}/assessmentstaken/{1}/questions/{2}/submit'.format(unquote(str(self._bank.ident)),
                                                                                              unquote(str(taken.ident)),
                                                                                              unquote(item_id))
        wrong_answer_payload = {
            'choiceIds': [wrong_choice_id]
        }

        req = self.app.post(url,
                            params=json.dumps(wrong_answer_payload),
                            headers={'content-type': 'application/json'})

        self.ok(req)
        data = self.json(req)
        self.assertFalse(data['correct'])
        self.assertEqual(
            data['feedback'],
            payload['answers'][0]['feedback']
        )

    def test_solution_returned_when_student_submits_right_answer(self):
        payload = self.item_payload()
        payload['solution'] = 'basket weaving'

        req = self.app.post(self.url,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        item = self.json(req)

        self.assertEqual(
            item['texts']['solution'],
            payload['solution']
        )

        item_id = item['id']
        right_choice_id = item['question']['choices'][1]['id']

        taken, offered = self.create_taken_for_item(self._bank.ident, item_id)

        url = '/api/v1/assessment/banks/{0}/assessmentstaken/{1}/questions/{2}/submit'.format(unquote(str(self._bank.ident)),
                                                                                              unquote(str(taken.ident)),
                                                                                              unquote(item_id))
        right_answer_payload = {
            'choiceIds': [right_choice_id]
        }

        req = self.app.post(url,
                            params=json.dumps(right_answer_payload),
                            headers={'content-type': 'application/json'})

        self.ok(req)
        data = self.json(req)
        self.assertTrue(data['correct'])
        self.assertEqual(
            data['feedback'],
            payload['solution']
        )

    def test_can_add_confused_learning_objectives_to_wrong_answer(self):
        payload = self.item_payload()
        payload['answers'][0].update({
            'genus': str(Type(**ANSWER_GENUS_TYPES['wrong-answer'])),
            'feedback': 'foobar',
            'confusedLearningObjectiveIds': ['foo%3A1%40MIT', 'baz%3A2%40ODL']
        })

        req = self.app.post(self.url,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        item = self.json(req)
        self.assertEqual(
            item['answers'][0]['genusTypeId'],
            str(Type(**ANSWER_GENUS_TYPES['wrong-answer']))
        )
        self.assertEqual(
            item['answers'][0]['confusedLearningObjectiveIds'],
            payload['answers'][0]['confusedLearningObjectiveIds']
        )

    def test_wrong_answer_submission_returns_confused_los(self):
        payload = self.item_payload()
        payload['answers'][0].update({
            'genus': str(Type(**ANSWER_GENUS_TYPES['wrong-answer'])),
            'feedback': 'what a novel idea',
            'confusedLearningObjectiveIds': ['foo%3A1%40MIT', 'baz%3A2%40ODL']
        })

        req = self.app.post(self.url,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        item = self.json(req)

        self.assertEqual(
            item['answers'][0]['confusedLearningObjectiveIds'],
            payload['answers'][0]['confusedLearningObjectiveIds']
        )

        item_id = item['id']
        wrong_choice_id = item['question']['choices'][1]['id']

        taken, offered = self.create_taken_for_item(self._bank.ident, item_id)

        url = '/api/v1/assessment/banks/{0}/assessmentstaken/{1}/questions/{2}/submit'.format(unquote(str(self._bank.ident)),
                                                                                              unquote(str(taken.ident)),
                                                                                              unquote(item_id))
        wrong_answer_payload = {
            'choiceIds': [wrong_choice_id]
        }

        req = self.app.post(url,
                            params=json.dumps(wrong_answer_payload),
                            headers={'content-type': 'application/json'})

        self.ok(req)
        data = self.json(req)
        self.assertFalse(data['correct'])
        self.assertEqual(
            data['confusedLearningObjectiveIds'],
            payload['answers'][0]['confusedLearningObjectiveIds']
        )


class AssessmentCrUDTests(BaseAssessmentTestCase):
    def item_payload(self):
        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_body = 'can you manipulate this?'
        question_choices = [
            'yes',
            'no',
            'maybe'
        ]
        question_type = 'question-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        answer = 2
        answer_type = 'answer-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'

        return {
            "name"                  : item_name,
            "description"           : item_desc,
            "question"              : {
                "type"           : question_type,
                "questionString" : question_body,
                "choices"        : question_choices
            },
            "answers"               : [{
                "type"      : answer_type,
                "choiceId"  : answer
            }],
        }

    def setUp(self):
        super(AssessmentCrUDTests, self).setUp()
        self.url += '/banks/' + unquote(str(self._bank.ident))

    def tearDown(self):
        """
        Remove the test user from all groups in Membership
        Start from the smallest groupId because need to
        remove "parental" roles like for DepartmentAdmin / DepartmentOfficer
        """
        super(AssessmentCrUDTests, self).tearDown()

    def test_assessment_offered_crud(self):
        """
        Instructors should be able to add assessment offered.
        Cannot create offered unless an assessment has items

        """
        # Use POST to create an assessment
        assessment_name = 'a really hard assessment'
        assessment_desc = 'meant to differentiate students'
        payload = {
            "name": assessment_name,
            "description": assessment_desc
        }
        req = self.app.post(self.url + '/assessments',
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        assessment_id = unquote(json.loads(req.body)['id'])
        assessment_detail_endpoint = self.url + '/assessments/' + assessment_id
        self.verify_text(req,
                         'Assessment',
                         assessment_name,
                         assessment_desc)

        assessment_offering_endpoint = assessment_detail_endpoint + '/assessmentsoffered'
        # PUT and DELETE should not work on this endpoint
        self.assertRaises(AppError,
                          self.app.put,
                          assessment_offering_endpoint)
        self.assertRaises(AppError,
                          self.app.delete,
                          assessment_offering_endpoint)

        # GET should return an empty list
        req = self.app.get(assessment_offering_endpoint)
        self.ok(req)

        # Use POST to create an offering
        # Inputting something other than a list or dict object should result in an error
        bad_payload = 'this is a bad input format'
        self.assertRaises(AppError,
                          self.app.post,
                          assessment_offering_endpoint,
                          params=bad_payload,
                          headers={'content-type': 'application/json'})

        payload = {
            "startTime" : {
                "day"   : 1,
                "month" : 1,
                "year"  : 2015
            },
            "duration"  : {
                "days"  : 2
            }
        }
        # POST at this point should throw an exception -- no items in the assessment
        self.assertRaises(AppError,
                          self.app.post,
                          assessment_offering_endpoint,
                          params=payload,
                          headers={'content-type': 'application/json'})

        items_endpoint = '{0}/items'.format(self.url)

        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        payload = {
            "name": item_name,
            "description": item_desc
        }

        req = self.app.post(items_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        item_id = unquote(json.loads(req.body)['id'])

        assessment_items_endpoint = assessment_detail_endpoint + '/items'

        # POST should also work and create the linkage
        payload = {
            'itemIds' : [item_id]
        }
        req = self.app.post(assessment_items_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)

        # Now POST to offerings should work
        payload = {
            "startTime" : {
                "day"   : 1,
                "month" : 1,
                "year"  : 2015
            },
            "duration"  : {
                "days"  : 2
            }
        }
        req = self.app.post(assessment_offering_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        offering = json.loads(req.body)
        offering_id = unquote(offering['id'])
        quote_safe_offering_id = offering['id']
        payload.update({
            'id'    : quote_safe_offering_id
        })
        self.verify_offerings(req,
                              'AssessmentOffering',
                              [payload])

        assessment_offering_detail_endpoint = '{0}/assessmentsoffered/{1}'.format(self.url,
                                                                                  offering_id)

        req = self.app.get(assessment_offering_endpoint)
        self.ok(req)
        self.verify_offerings(req,
                             'AssessmentOffering',
                             [payload])

        # For the offering detail endpoint, GET, PUT, DELETE should work
        # Check that POST returns error code 405--we don't support this
        self.assertRaises(AppError,
                          self.app.post,
                          assessment_offering_detail_endpoint)
        req = self.app.get(assessment_offering_detail_endpoint)
        self.ok(req)
        self.verify_offerings(req, 'AssessmentOffering', [payload])

        # PUT to the offering URL should modify the start time or duration
        new_start_time = {
            "startTime" : {
                "day"   : 1,
                "month" : 2,
                "year"  : 2015
            }
        }
        expected_payload = new_start_time
        expected_payload.update({
            "duration"  : {
                "days"  : 2
            },
            "id"        : quote_safe_offering_id
        })

        req = self.app.put(assessment_offering_detail_endpoint,
                           params=json.dumps(new_start_time),
                           headers={'content-type': 'application/json'})
        self.ok(req)
        self.verify_offerings(req, 'AssessmentOffered', [expected_payload])

        # PUT with a list of length 1 should also work
        new_duration = [{
            "duration"  : {
                "days"      : 5,
                "minutes"   : 120
            }
        }]
        expected_payload = new_duration
        expected_payload[0].update(new_start_time)
        expected_payload[0].update({
            "id"    : quote_safe_offering_id
        })
        req = self.app.put(assessment_offering_detail_endpoint,
                           params=json.dumps(new_duration),
                           headers={'content-type': 'application/json'})
        self.ok(req)
        self.verify_offerings(req, 'AssessmentOffered', expected_payload)

        funny_payload = {
            "duration"  : {
                "hours" :   2
            }
        }
        expected_converted_payload = funny_payload
        expected_converted_payload.update(new_start_time)
        expected_converted_payload.update({
            "id"    : quote_safe_offering_id
        })
        req = self.app.put(assessment_offering_detail_endpoint,
                           params=json.dumps(funny_payload),
                           headers={'content-type': 'application/json'})
        self.ok(req)
        self.verify_offerings(req, 'AssessmentOffering', expected_converted_payload)

        # check that the attributes changed in GET
        req = self.app.get(assessment_offering_detail_endpoint)
        self.ok(req)
        self.verify_offerings(req, 'AssessmentOffered', expected_converted_payload)

        # Delete the offering now
        req = self.app.delete(assessment_offering_detail_endpoint)
        self.deleted(req)

        req = self.app.get(assessment_offering_endpoint)
        self.ok(req)
        self.verify_no_data(req)

        # test that you can POST / create multiple offerings with a list
        bad_payload = 'this is a bad input format'
        self.assertRaises(AppError,
                          self.app.post,
                          assessment_offering_endpoint,
                          params=bad_payload,
                          headers={'content-type': 'application/json'})

        payload = [{
            "startTime" : {
                "day"   : 1,
                "month" : 1,
                "year"  : 2015
            },
            "duration"  : {
                "days"  : 2
            }
                   },{
            "startTime" : {
                "day"   : 9,
                "month" : 1,
                "year"  : 2015
            },
            "duration"  : {
                "days"  : 20
            }
        }]
        req = self.app.post(assessment_offering_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)

        offering = json.loads(req.body)
        offering1_id = unquote(offering[0]['id'])
        offering2_id = unquote(offering[1]['id'])

        payload[0].update({
            'id'    : offering1_id
        })
        payload[1].update({
            'id'    : offering2_id
        })

        req = self.app.get(assessment_offering_endpoint)
        self.ok(req)
        self.verify_offerings(req,
                              'AssessmentOffering',
                              payload)

    def test_assessment_taking(self):
        """
        POSTing to takens should create a new one.
        Should only be able to POST from the /assessmentsoffered/ endpoint
        But can GET from the /assessments/ endpoint, too.

        Without submitting a response, POSTing again should
        return the same one.

         -- Check that for Ortho3D types, a taken has files.

        Submitting and then POSTing should return a new
        taken.

        This should work for both instructors and learners

        NOTE: this tests the obfuscated way of taking assessments (no list of questions)
        """
        items_endpoint = self.url + '/items'

        # Use POST to create an item
        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_string = 'can you manipulate this?'
        question_type = 'question-record-type%3Alabel-ortho-faces%40ODL.MIT.EDU'
        answer_string = 'yes!'
        answer_type = 'answer-record-type%3Alabel-ortho-faces%40ODL.MIT.EDU'
        payload = {
            "name": item_name,
            "description": item_desc,
            "question": {
                "type": question_type,
                "questionString": question_string
            },
            "answers": [{
                "type": answer_type,
                "integerValues": {
                    "frontFaceValue": 1,
                    "sideFaceValue" : 2,
                    "topFaceValue"  : 3
                }
            }],
        }
        req = self.app.post(items_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)

        item = json.loads(req.body)
        item_id = unquote(item['id'])

        item_detail_endpoint = items_endpoint + '/' + item_id
        req = self.app.get(item_detail_endpoint)
        self.ok(req)

        req = self.app.get(items_endpoint)
        self.ok(req)
        self.assertEqual(
            len(self.json(req)),
            1
        )

        # Now create an assessment, link the item to it,
        # and create an offering.
        # Use the offering_id to create the taken
        assessments_endpoint = self.url + '/assessments'
        assessment_name = 'a really hard assessment'
        assessment_desc = 'meant to differentiate students'
        payload = {
            "name": assessment_name,
            "description": assessment_desc
        }
        req = self.app.post(assessments_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        assessment_id = unquote(json.loads(req.body)['id'])

        assessment_detail_endpoint = assessments_endpoint + '/' + assessment_id
        assessment_offering_endpoint = assessment_detail_endpoint + '/assessmentsoffered'
        assessment_items_endpoint = assessment_detail_endpoint + '/items'

        # POST should create the linkage
        payload = {
            'itemIds' : [item_id]
        }
        req = self.app.post(assessment_items_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)

        # Use POST to create an offering
        payload = {
            "startTime" : {
                "day"   : 1,
                "month" : 1,
                "year"  : 2015
            },
            "duration"  : {
                "days"  : 2
            }
        }

        req = self.app.post(assessment_offering_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        offering = json.loads(req.body)
        offering_id = unquote(offering['id'])
        quote_safe_offering_id = offering['id']

        assessments_offered_endpoint = self.url + '/assessmentsoffered'
        assessment_offering_detail_endpoint = assessments_offered_endpoint + '/' + offering_id

        # Can GET and POST. PUT and DELETE not supported
        assessment_takens_endpoint = assessment_offering_detail_endpoint + '/assessmentstaken'
        req = self.app.get(assessment_takens_endpoint)
        self.ok(req)

        # Check that DELETE returns error code 405--we don't support this
        self.assertRaises(AppError,
                          self.app.delete,
                          assessment_takens_endpoint)

        # PUT to this root url also returns a 405
        self.assertRaises(AppError,
                          self.app.put,
                          assessment_takens_endpoint)

        req = self.app.post(assessment_takens_endpoint)
        self.ok(req)
        taken = json.loads(req.body)
        taken_id = unquote(taken['id'])

        # Instructor can GET the taken details (learner cannot).
        # POST, PUT, DELETE not supported
        taken_endpoint = self.url + '/assessmentstaken/' + taken_id
        req = self.app.get(taken_endpoint)
        self.ok(req)

        # PUT to this root url also returns a 405
        self.assertRaises(AppError,
                          self.app.put,
                          taken_endpoint)

        # POST to this root url also returns a 405
        self.assertRaises(AppError,
                          self.app.post,
                          taken_endpoint)

        # POSTing to assessment_offering_takens_endpoint
        # returns the same taken
        req = self.app.post(assessment_takens_endpoint)
        self.ok(req)
        taken_copy = json.loads(req.body)
        taken_copy_id = unquote(taken_copy['id'])
        self.assertEqual(taken_id, taken_copy_id)

        # Can submit a wrong response
        submit_endpoint = taken_endpoint + '/questions/{0}/submit'.format(item_id)
        wrong_response = {
            "integerValues": {
                "frontFaceValue" : 0,
                "sideFaceValue"  : 1,
                "topFaceValue"   : 2
            }
        }

        # Check that DELETE returns error code 405--we don't support this
        self.assertRaises(AppError,
                          self.app.delete,
                          submit_endpoint)

        # PUT to this root url also returns a 405
        self.assertRaises(AppError,
                          self.app.put,
                          submit_endpoint)

        # GET to this root url also returns a 405
        self.assertRaises(AppError,
                          self.app.get,
                          submit_endpoint)

        req = self.app.post(submit_endpoint,
                            params=json.dumps(wrong_response),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        self.verify_submission(req, _expected_result=False, _has_next=False)

        # to submit again, have to get a new taken
        # Now getting another taken will return a new one
        # POSTing to assessment_offering_takens_endpoint
        # returns the same taken
        req = self.app.post(assessment_takens_endpoint)
        self.ok(req)
        new_taken = json.loads(req.body)
        quoted_new_taken_id = new_taken['id']
        new_taken_id = unquote(quoted_new_taken_id)
        self.assertNotEqual(taken_id, quoted_new_taken_id)

        new_taken_endpoint = self.url + '/assessmentstaken/' + new_taken_id
        new_submit_endpoint = new_taken_endpoint + '/questions/{0}/submit'.format(item_id)
        right_response = {
            "integerValues": {
                "frontFaceValue" : 1,
                "sideFaceValue"  : 2,
                "topFaceValue"   : 3
            }
        }
        req = self.app.post(new_submit_endpoint,
                            params=json.dumps(right_response),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        self.verify_submission(req, _expected_result=True, _has_next=False)

    def test_assessments_crud(self):
        """
        Create a test bank and test all things associated with assessments
        and a single assessment
        DELETE on root assessments/ does nothing. Error code 405.
        GET on root assessments/ gets you a list
        POST on root assessments/ creates a new assessment
        PUT on root assessments/ does nothing. Error code 405.

        For a single assessment detail:
        DELETE will delete that assessment
        GET brings up the assessment details with offerings and taken
        POST does nothing. Error code 405.
        PUT lets user update the name or description
        """
        assessment_endpoint = self.url + '/assessments'

        # Check that DELETE returns error code 405--we don't support this
        self.assertRaises(AppError,
                          self.app.delete,
                          assessment_endpoint)

        # PUT to this root url also returns a 405
        self.assertRaises(AppError,
                          self.app.put,
                          assessment_endpoint)

        # GET should return 0 results
        req = self.app.get(assessment_endpoint)
        self.verify_no_data(req)

        # Use POST to create an assessment
        assessment_name = 'a really hard assessment'
        assessment_desc = 'meant to differentiate students'
        payload = {
            "name": assessment_name,
            "description": assessment_desc
        }
        req = self.app.post(assessment_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        assessment_id = unquote(json.loads(req.body)['id'])

        assessment_details_endpoint = '{0}/{1}'.format(assessment_endpoint,
                                                       assessment_id)
        self.verify_text(req,
                         'Assessment',
                         assessment_name,
                         assessment_desc)

        req = self.app.get(assessment_details_endpoint)
        self.ok(req)
        self.verify_text(req,
                         'Assessment',
                         assessment_name,
                         assessment_desc,
                         assessment_id)

        # Now test PUT / GET / POST / DELETE on the new assessment item
        # POST does nothing
        assessment_detail_endpoint = assessment_endpoint + '/' + assessment_id
        self.assertRaises(AppError,
                          self.app.post,
                          assessment_detail_endpoint)

        # GET displays it, with self link. Allowed for Instructor
        req = self.app.get(assessment_detail_endpoint)
        self.ok(req)
        self.verify_text(req,
                         'Assessment',
                         assessment_name,
                         assessment_desc)

        new_assessment_name = 'a new assessment name'
        new_assessment_desc = 'to trick students'
        payload = {
            "name": new_assessment_name
        }
        req = self.app.put(assessment_detail_endpoint,
                           params=json.dumps(payload),
                           headers={'content-type': 'application/json'})
        self.ok(req)
        self.verify_text(req,
                         'Assessment',
                         new_assessment_name,
                         assessment_desc)

        req = self.app.get(assessment_detail_endpoint)
        self.ok(req)
        self.verify_text(req,
                         'Assessment',
                         new_assessment_name,
                         assessment_desc)

        payload = {
            "description": new_assessment_desc
        }
        req = self.app.put(assessment_detail_endpoint,
                           params=json.dumps(payload),
                           headers={'content-type': 'application/json'})
        self.ok(req)
        self.verify_text(req,
                         'Assessment',
                         new_assessment_name,
                         new_assessment_desc)

        req = self.app.get(assessment_detail_endpoint)
        self.ok(req)
        self.verify_text(req,
                         'Assessment',
                         new_assessment_name,
                         new_assessment_desc)

        # trying to delete the bank with assessments should throw an error
        self.assertRaises(AppError,
                          self.app.delete,
                          self.url)

    def test_banks_get(self):
        """
        Should give you a list of banks and links.
        """
        req = self.app.get('/api/v1/assessment/banks')
        self.ok(req)
        self.assertIn(
            '"displayName": ',
            req.body
        )  # this only really tests that at least one bank exists...not great.

    def test_bank_post_and_crud(self):
        """
        User can create a new assessment bank. Need to do self-cleanup,
        because the Mongo backend is not part of the test database...that
        means Django will not wipe it clean after every test!
        Once a bank is created, user can GET it, PUT to update it, and
        DELETE it. POST should return an error code 405.
        Do these bank detail tests here, because we have a known
        bank ID
        """
        # verify that the bank now appears in the bank_details call
        req = self.app.get(self.url)
        self.ok(req)
        self.verify_text(req,
                         'Bank',
                         self._bank.display_name.text,
                         self._bank.description.text)

        new_name = 'a new bank name'
        payload = {
            "name": new_name
        }
        # DepartmentAdmin should be able to edit the bank
        req = self.app.put(self.url,
                           params=json.dumps(payload),
                           headers={'content-type': 'application/json'})
        self.ok(req)
        self.verify_text(req, 'Bank', new_name, self._bank.description.text)

        req = self.app.get(self.url)
        self.ok(req)
        self.verify_text(req, 'Bank', new_name, self._bank.description.text)

        new_desc = 'a new bank description'
        payload = {
            "description": new_desc
        }
        req = self.app.put(self.url,
                           params=json.dumps(payload),
                           headers={'content-type': 'application/json'})
        self.ok(req)
        self.verify_text(req, 'Bank', new_name, new_desc)

        req = self.app.get(self.url)
        self.ok(req)
        self.verify_text(req, 'Bank', new_name, new_desc)

    def test_can_set_item_genus_type_and_file_names(self):
        """
        When creating a new item, can define a specific genus type
        """
        items_endpoint = self.url + '/items'

        # Use POST to create an item--right now user is Instructor,
        # so this should show up in GET
        item_genus = 'item-genus-type%3Aedx-multi-choice-problem-type%40ODL.MIT.EDU'
        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_string = 'can you manipulate this?'
        question_type = 'question-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        manip_name = 'A bracket'
        answer_string = 'yes!'
        answer_type = 'answer-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        payload = {
            "name"          : item_name,
            "description"   : item_desc,
            "genus"         : item_genus,
            "question"      : {
                "choices"   : [
                    'yes',
                    'no',
                    'maybe'
                ],
                "genus"         : item_genus,
                "promptName"    : manip_name,
                "type"          : question_type,
                "questionString": question_string
            },
            "answers": [{
                "genus"     : item_genus,
                "type"      : answer_type,
                "choiceId"  : 1
            }],
        }
        req = self.app.post(items_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        item_id = unquote(json.loads(req.body)['id'])
        item = json.loads(req.body)
        question = self.extract_question(item)
        answer = self.extract_answers(item)[0]
        self.assertEqual(
            question['genusTypeId'],
            item_genus
        )
        self.assertEqual(
            answer['genusTypeId'],
            item_genus
        )
        self.verify_text(req,
                         'Item',
                         item_name,
                         item_desc,
                         _genus=item_genus)

        req = self.app.get(items_endpoint)
        self.ok(req)
        self.verify_text(req,
                         'Item',
                         item_name,
                         item_desc,
                         _id=item_id,
                         _genus=item_genus)
        item = json.loads(req.body)
        question = self.extract_question(item)
        answer = self.extract_answers(item)[0]
        self.assertEqual(
            question['genusTypeId'],
            item_genus
        )
        self.assertEqual(
            answer['genusTypeId'],
            item_genus
        )

    def test_link_items_to_assessment(self):
        """
        Test link, view, delete of items to assessments
        """
        assessments_endpoint = self.url + '/assessments'
        items_endpoint = self.url + '/items'

        # Use POST to create an assessment
        assessment_name = 'a really hard assessment'
        assessment_desc = 'meant to differentiate students'
        payload = {
            "name": assessment_name,
            "description": assessment_desc
        }
        req = self.app.post(assessments_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        assessment_id = unquote(json.loads(req.body)['id'])
        assessment_detail_endpoint = assessments_endpoint + '/' + assessment_id
        self.verify_text(req,
                         'Assessment',
                         assessment_name,
                         assessment_desc)

        req = self.app.get(assessments_endpoint)
        self.ok(req)
        self.verify_text(req,
                         'Assessment',
                         assessment_name,
                         assessment_desc,
                         assessment_id)

        # Use POST to create an item
        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_string = 'what is pi?'
        question_type = 'question-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        # answer_string = 'dessert'
        # answer_type = 'answer-record-type%3Alabel-ortho-faces%40ODL.MIT.EDU'
        payload = {
            "name": item_name,
            "description": item_desc,
            "question": {
                "type": question_type,
                "questionString": question_string,
                "choices": ['1', '2']
            }
        }
        req = self.app.post(items_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        item = json.loads(req.body)
        item_id = unquote(item['id'])
        item_detail_endpoint = items_endpoint + '/' + item_id
        question_id = self.extract_question(item)['id']
        self.verify_text(req,
                         'Item',
                         item_name,
                         item_desc)
        self.verify_question(req,
                             question_string,
                             question_type)

        req = self.app.get(items_endpoint)
        self.ok(req)
        self.verify_text(req,
                         'Item',
                         item_name,
                         item_desc,
                         item_id)
        self.verify_question(req,
                             question_string,
                             question_type)

        # Now start working on the assessment/items endpoint, to test
        # GET, POST for the items/ endpoint (others should throw error)
        # GET, DELETE for the items/<id> endpoint (others should throw error)
        assessment_items_endpoint = assessment_detail_endpoint + '/items'

        # Check that DELETE returns error code 405--we don't support this
        self.assertRaises(AppError,
                          self.app.delete,
                          assessment_items_endpoint)

        req = self.app.get(assessment_items_endpoint)
        self.ok(req)
        self.verify_no_data(req)

        # POST should also work and create the linkage
        payload = {
            'itemIds' : [item_id]
        }
        req = self.app.post(assessment_items_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        self.verify_text(req,
                         'Item',
                         item_name,
                         item_desc,
                         item_id)
        self.verify_question(req,
                             question_string,
                             question_type)

        # should now appear in the Assessment Items List
        req = self.app.get(assessment_items_endpoint)
        self.ok(req)
        self.verify_text(req,
                         'Item',
                         item_name,
                         item_desc,
                         item_id)
        self.verify_question(req,
                             question_string,
                             question_type)

        # Trying to delete the item now
        # should raise an error--cannot delete an item that is
        # assigned to an assignment!
        self.assertRaises(AppError,
                          self.app.delete,
                          item_detail_endpoint)

        assessment_item_details_endpoint = assessment_items_endpoint + '/' + item_id
        req = self.app.delete(assessment_item_details_endpoint)
        self.deleted(req)

        req = self.app.get(assessment_items_endpoint)
        self.ok(req)
        self.verify_no_data(req)


class AssessmentOfferedTests(BaseAssessmentTestCase):
    def create_assessment(self):
        # Now create an assessment, link the item to it,
        # and create an offering.
        # Use the offering_id to create the taken
        assessments_endpoint = self.url + '/assessments'
        assessment_name = 'a really hard assessment'
        assessment_desc = 'meant to differentiate students'
        payload = {
            "name": assessment_name,
            "description": assessment_desc
        }
        req = self.app.post(assessments_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        return self.json(req)

    def create_item(self):
        items_endpoint = self.url + '/items'

        # Use POST to create an item
        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_string = 'can you manipulate this?'
        question_type = 'question-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        answer_string = 'yes!'
        answer_type = 'answer-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        payload = {
            "name": item_name,
            "description": item_desc,
            "question": {
                "type": question_type,
                "questionString": question_string,
                "choices": ['1', '2', '3']
            },
            "answers": [{
                "type": answer_type,
                "choiceId": 1
            }],
        }
        req = self.app.post(items_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)

        item = json.loads(req.body)
        return item

    def item_payload(self):
        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_body = 'can you manipulate this?'
        question_choices = [
            'yes',
            'no',
            'maybe'
        ]
        question_type = 'question-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        answer = 2
        answer_type = 'answer-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'

        return {
            "name"                  : item_name,
            "description"           : item_desc,
            "question"              : {
                "type"           : question_type,
                "questionString" : question_body,
                "choices"        : question_choices
            },
            "answers"               : [{
                "type"      : answer_type,
                "choiceId"  : answer
            }],
        }

    def link_item_to_assessment(self, item, assessment):
        assessment_items_endpoint = '{0}/assessments/{1}/items'.format(self.url,
                                                                       unquote(assessment['id']))

        # POST should create the linkage
        payload = {
            'itemIds': [unquote(item['id'])]
        }
        req = self.app.post(assessment_items_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)

    def setUp(self):
        super(AssessmentOfferedTests, self).setUp()
        self.url += '/banks/' + unquote(str(self._bank.ident))

    def tearDown(self):
        """
        Remove the test user from all groups in Membership
        Start from the smallest groupId because need to
        remove "parental" roles like for DepartmentAdmin / DepartmentOfficer
        """
        super(AssessmentOfferedTests, self).tearDown()

    def test_can_set_max_attempts_on_assessment_offered(self):
        items_endpoint = self.url + '/items'

        item = self.create_item()

        req = self.app.get(items_endpoint)
        self.ok(req)

        # Now create an assessment, link the item to it,
        # and create an offering.
        # Use the offering_id to create the taken
        assessments_endpoint = self.url + '/assessments'

        assessment = self.create_assessment()
        assessment_id = unquote(assessment['id'])

        assessment_detail_endpoint = assessments_endpoint + '/' + assessment_id
        assessment_offering_endpoint = assessment_detail_endpoint + '/assessmentsoffered'
        self.link_item_to_assessment(item, assessment)

        # Use POST to create an offering
        payload = {
            "startTime" : {
                "day"   : 1,
                "month" : 1,
                "year"  : 2015
            },
            "duration"  : {
                "days"  : 2
            }
        }
        req = self.app.post(assessment_offering_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        offering = json.loads(req.body)
        offering_id = unquote(offering['id'])

        # verify that the offering has defaulted to maxAttempts = None
        self.assertIsNone(offering['maxAttempts'])

        assessment_offering_detail_endpoint = self.url + '/assessmentsoffered/' + offering_id
        self.app.delete(assessment_offering_detail_endpoint)

        # try again, but set maxAttempts on create
        payload = {
            "startTime"     : {
                "day"   : 1,
                "month" : 1,
                "year"  : 2015
            },
            "duration"      : {
                "days"  : 2
            },
            "maxAttempts" : 2
        }
        req = self.app.post(assessment_offering_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        offering = json.loads(req.body)
        offering_id = unquote(offering['id'])

        # verify that the offering has maxAttempts == 2
        self.assertEqual(offering['maxAttempts'],
                         2)

    def test_can_update_max_attempts_on_assessment_offered(self):
        items_endpoint = self.url + '/items'

        item = self.create_item()

        req = self.app.get(items_endpoint)
        self.ok(req)

        # Now create an assessment, link the item to it,
        # and create an offering.
        # Use the offering_id to create the taken
        assessments_endpoint = self.url + '/assessments'

        assessment = self.create_assessment()
        assessment_id = unquote(assessment['id'])

        assessment_detail_endpoint = assessments_endpoint + '/' + assessment_id
        assessment_offering_endpoint = assessment_detail_endpoint + '/assessmentsoffered'
        self.link_item_to_assessment(item, assessment)

        # Use POST to create an offering
        payload = {
            "startTime" : {
                "day"   : 1,
                "month" : 1,
                "year"  : 2015
            },
            "duration"  : {
                "days"  : 2
            }
        }

        req = self.app.post(assessment_offering_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        offering = json.loads(req.body)
        offering_id = unquote(offering['id'])

        # verify that the offering has defaulted to maxAttempts = None
        self.assertIsNone(offering['maxAttempts'])

        assessment_offering_detail_endpoint = self.url + '/assessmentsoffered/' + offering_id

        # try again, but set maxAttempts on update
        payload = {
            "maxAttempts" : 2
        }
        req = self.app.put(assessment_offering_detail_endpoint,
                           params=json.dumps(payload),
                           headers={'content-type': 'application/json'})
        self.ok(req)
        offering = json.loads(req.body)

        # verify that the offering has maxAttempts == 2
        self.assertEqual(offering['maxAttempts'],
                         2)

    def test_default_max_attempts_allows_infinite_attempts(self):
        # ok, don't really test to infinity, but test several
        item = self.create_item()
        assessment = self.create_assessment()
        assessment_id = unquote(assessment['id'])

        assessment_detail_endpoint = '{0}/assessments/{1}'.format(self.url,
                                                                  assessment_id)
        assessment_offering_endpoint = assessment_detail_endpoint + '/assessmentsoffered'

        # POST should create the linkage
        self.link_item_to_assessment(item, assessment)

        # Use POST to create an offering
        payload = {
            "startTime" : {
                "day"   : 1,
                "month" : 1,
                "year"  : 2015
            },
            "duration"  : {
                "days"  : 2
            }
        }

        req = self.app.post(assessment_offering_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        offering = json.loads(req.body)
        offering_id = unquote(offering['id'])

        # verify that the offering has defaulted to maxAttempts = None
        self.assertIsNone(offering['maxAttempts'])

        assessment_offering_detail_endpoint = self.url + '/assessmentsoffered/' + offering_id

        num_attempts = 25
        # for deleting
        taken_endpoints = []
        assessment_offering_takens_endpoint = assessment_offering_detail_endpoint + '/assessmentstaken'

        for attempt in range(0, num_attempts):
            # Can POST to create a new taken
            req = self.app.post(assessment_offering_takens_endpoint)
            self.ok(req)
            taken = json.loads(req.body)
            taken_id = unquote(taken['id'])

            taken_endpoint = self.url + '/assessmentstaken/' + taken_id
            taken_endpoints.append(taken_endpoint)
            taken_finish_endpoint = taken_endpoint + '/finish'
            req = self.app.post(taken_finish_endpoint)
            self.ok(req)
            # finish the assessment taken, so next time we create one, it should
            # create a new one

    def test_max_attempts_throws_exception_if_taker_tries_to_exceed(self):
        item = self.create_item()
        item_1_id = unquote(item['id'])

        assessment = self.create_assessment()
        assessment_id = unquote(assessment['id'])

        assessment_detail_endpoint = '{0}/assessments/{1}'.format(self.url,
                                                                  assessment_id)
        assessment_offering_endpoint = assessment_detail_endpoint + '/assessmentsoffered'
        self.link_item_to_assessment(item, assessment)

        # Use POST to create an offering
        payload = {
            "startTime" : {
                "day"   : 1,
                "month" : 1,
                "year"  : 2015
            },
            "duration"  : {
                "days"  : 2
            },
            "maxAttempts" : 2
        }
        req = self.app.post(assessment_offering_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        offering = json.loads(req.body)
        offering_id = unquote(offering['id'])

        # verify that the offering has defaulted to maxAttempts == 2
        self.assertEquals(offering['maxAttempts'], 2)

        assessment_offering_detail_endpoint = self.url + '/assessmentsoffered/' + offering_id

        num_attempts = 5
        # for deleting
        taken_endpoints = []
        assessment_offering_takens_endpoint = assessment_offering_detail_endpoint + '/assessmentstaken'

        for attempt in range(0, num_attempts):
            # Can POST to create a new taken
            if attempt >= payload['maxAttempts']:
                self.assertRaises(AppError,
                                  self.app.post,
                                  assessment_offering_takens_endpoint)
            else:
                req = self.app.post(assessment_offering_takens_endpoint)

                self.ok(req)
                taken = json.loads(req.body)
                taken_id = unquote(taken['id'])

                taken_endpoint = self.url + '/assessmentstaken/' + taken_id
                taken_endpoints.append(taken_endpoint)
                taken_finish_endpoint = taken_endpoint + '/finish'
                req = self.app.post(taken_finish_endpoint)
                self.ok(req)
                # finish the assessment taken, so next time we create one, it should
                # create a new one

    def test_can_update_review_options_flag(self):
        """
        For the Reviewable offered and taken records, can  change the reviewOptions
        flag on a created item
        :return:
        """
        item = self.create_item()
        item_1_id = unquote(item['id'])

        assessment = self.create_assessment()
        assessment_id = unquote(assessment['id'])

        assessment_detail_endpoint = '{0}/assessments/{1}'.format(self.url,
                                                                  assessment_id)
        assessment_offering_endpoint = assessment_detail_endpoint + '/assessmentsoffered'
        self.link_item_to_assessment(item, assessment)

        # Use POST to create an offering
        payload = {
            "startTime" : {
                "day"   : 1,
                "month" : 1,
                "year"  : 2015
            },
            "duration"  : {
                "days"  : 2
            }
        }

        req = self.app.post(assessment_offering_endpoint,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        offering = json.loads(req.body)
        offering_id = unquote(offering['id'])

        # verify that the offering has defaulted to reviewOptions all true
        review_options = ['afterAttempt','afterDeadline','beforeDeadline','duringAttempt']
        for opt in review_options:
            self.assertTrue(offering['reviewOptions']['whetherCorrect'][opt])

        payload = {
            "reviewOptions" : {
                "whetherCorrect" : {
                    "duringAttempt" : False
                }
            }
        }
        assessment_offering_detail_endpoint = self.url + '/assessmentsoffered/' + offering_id

        req = self.app.put(assessment_offering_detail_endpoint,
                           params=json.dumps(payload),
                           headers={'content-type': 'application/json'})

        self.ok(req)
        offering = json.loads(req.body)

        # verify that the offering has duringAttempt = False
        review_options = ['afterAttempt','afterDeadline','beforeDeadline','duringAttempt']
        for opt in review_options:
            if opt == 'duringAttempt':
                self.assertFalse(offering['reviewOptions']['whetherCorrect'][opt])
            else:
                self.assertTrue(offering['reviewOptions']['whetherCorrect'][opt])

    def test_review_options_flag_works_for_during_and_after_attempt(self):
        """
        For the Reviewable offered and taken records
        :return:
        """
        auth = HTTPSignatureAuth(key_id=self.public_key,
                                 secret=self.private_key,
                                 algorithm='hmac-sha256',
                                 headers=self.signature_headers)
        name = 'atestbank'
        desc = 'for testing purposes only'
        bank_id = self.create_test_bank(auth, name, desc)

        bank_endpoint = self.endpoint + 'assessment/banks/' + bank_id + '/'
        items_endpoint = bank_endpoint + 'items/'

        get_sig = calculate_signature(auth, self.headers, 'GET', items_endpoint)

        # Use POST to create an item
        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_string = 'can you manipulate this?'
        question_type = 'question-record-type%3Alabel-ortho-faces%40ODL.MIT.EDU'
        answer_string = 'yes!'
        answer_type = 'answer-record-type%3Alabel-ortho-faces%40ODL.MIT.EDU'
        payload = {
            "name": item_name,
            "description": item_desc,
            "question": {
                "type": question_type,
                "questionString": question_string
            },
            "answers": [{
                "type": answer_type,
                "integerValues": {
                    "frontFaceValue": 1,
                    "sideFaceValue" : 2,
                    "topFaceValue"  : 3
                }
            }],
        }
        stringified_payload = deepcopy(payload)
        stringified_payload['manip'] = self.manip
        stringified_payload['frontView'] = self.front
        stringified_payload['sideView'] = self.side
        stringified_payload['topView'] = self.top
        stringified_payload['question'] = json.dumps(payload['question'])
        stringified_payload['answers'] = json.dumps(payload['answers'])

        post_sig = calculate_signature(auth, self.headers, 'POST', items_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(items_endpoint, stringified_payload)
        self.ok(req)

        item = json.loads(req.body)
        item_1_id = unquote(item['id'])
        question_1_id = unquote(self.extract_question(item)['id'])

        get_sig = calculate_signature(auth, self.headers, 'GET', items_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(items_endpoint)
        self.ok(req)

        # Now create an assessment, link the item to it,
        # and create an offering.
        # Use the offering_id to create the taken
        assessments_endpoint = bank_endpoint + 'assessments/'
        assessment_name = 'a really hard assessment'
        assessment_desc = 'meant to differentiate students'
        payload = {
            "name": assessment_name,
            "description": assessment_desc
        }
        post_sig = calculate_signature(auth, self.headers, 'POST', assessments_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(assessments_endpoint, payload, format='json')
        self.ok(req)
        assessment_id = unquote(json.loads(req.body)['id'])

        assessment_detail_endpoint = assessments_endpoint + assessment_id + '/'
        assessment_offering_endpoint = assessment_detail_endpoint + 'assessmentsoffered/'
        assessment_items_endpoint = assessment_detail_endpoint + 'items/'

        # POST should create the linkage
        payload = {
            'itemIds' : [item_1_id]
        }
        link_post_sig = calculate_signature(auth, self.headers, 'POST', assessment_items_endpoint)
        self.sign_client(link_post_sig)
        req = self.client.post(assessment_items_endpoint, payload, format='json')
        self.ok(req)


        # Use POST to create an offering
        offering_post_sig = calculate_signature(auth, self.headers, 'POST', assessment_offering_endpoint)
        self.sign_client(offering_post_sig)

        payload = {
            "startTime" : {
                "day"   : 1,
                "month" : 1,
                "year"  : 2015
            },
            "duration"  : {
                "days"  : 2
            }
        }

        self.sign_client(offering_post_sig)
        req = self.client.post(assessment_offering_endpoint, payload, format='json')
        self.ok(req)
        offering = json.loads(req.body)
        offering_id = unquote(offering['id'])

        # verify that the offering has defaulted to reviewOptions all true
        review_options = ['afterAttempt','afterDeadline','beforeDeadline','duringAttempt']
        for opt in review_options:
            self.assertTrue(offering['reviewOptions']['whetherCorrect'][opt])

        assessment_offering_detail_endpoint = bank_endpoint + 'assessmentsoffered/' + offering_id + '/'

        # Convert to a learner to test the rest of this
        self.convert_user_to_bank_learner(bank_id)
        # Can POST to create a new taken
        assessment_offering_takens_endpoint = assessment_offering_detail_endpoint + 'assessmentstaken/'
        post_sig = calculate_signature(auth, self.headers, 'POST', assessment_offering_takens_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(assessment_offering_takens_endpoint)
        self.ok(req)
        taken = json.loads(req.body)
        taken_id = unquote(taken['id'])

        # verify the "reviewWhetherCorrect" is True
        self.assertTrue(taken['reviewWhetherCorrect'])

        taken_endpoint = bank_endpoint + 'assessmentstaken/' + taken_id + '/'

        self.convert_user_to_bank_instructor(bank_id)

        self.delete_item(auth, taken_endpoint)
        self.delete_item(auth, assessment_offering_detail_endpoint)

        # try again, but set to only view correct after attempt
        offering_post_sig = calculate_signature(auth, self.headers, 'POST', assessment_offering_endpoint)
        self.sign_client(offering_post_sig)

        payload = {
            "startTime"     : {
                "day"   : 1,
                "month" : 1,
                "year"  : 2015
            },
            "duration"      : {
                "days"  : 2
            },
            "reviewOptions" : {
                "whetherCorrect" : {
                    "duringAttempt" : False
                }
            }
        }

        self.sign_client(offering_post_sig)
        req = self.client.post(assessment_offering_endpoint, payload, format='json')
        self.ok(req)
        offering = json.loads(req.body)
        offering_id = unquote(offering['id'])

        # verify that the offering has duringAttempt = False
        review_options = ['afterAttempt','afterDeadline','beforeDeadline','duringAttempt']
        for opt in review_options:
            if opt == 'duringAttempt':
                self.assertFalse(offering['reviewOptions']['whetherCorrect'][opt])
            else:
                self.assertTrue(offering['reviewOptions']['whetherCorrect'][opt])

        assessment_offering_detail_endpoint = bank_endpoint + 'assessmentsoffered/' + offering_id + '/'

        # Can POST to create a new taken
        self.convert_user_to_bank_learner(bank_id)

        assessment_offering_takens_endpoint = assessment_offering_detail_endpoint + 'assessmentstaken/'
        post_sig = calculate_signature(auth, self.headers, 'POST', assessment_offering_takens_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(assessment_offering_takens_endpoint)
        self.ok(req)
        taken = json.loads(req.body)
        taken_id = unquote(taken['id'])
        taken_endpoint = bank_endpoint + 'assessmentstaken/' + taken_id + '/'

        # verify the "reviewWhetherCorrect" is False
        self.assertFalse(taken['reviewWhetherCorrect'])

        # now submitting an answer should let reviewWhetherCorrect be True
        right_response = {
            "integerValues": {
                "frontFaceValue" : 1,
                "sideFaceValue"  : 2,
                "topFaceValue"   : 3
            }
        }

        finish_taken_endpoint = taken_endpoint + 'finish/'
        taken_questions_endpoint = taken_endpoint + 'questions/'
        question_1_endpoint = taken_questions_endpoint + question_1_id + '/'
        question_1_submit_endpoint = question_1_endpoint + 'submit/'

        post_sig = calculate_signature(auth, self.headers, 'POST', question_1_submit_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(question_1_submit_endpoint, right_response, format='json')
        self.ok(req)

        post_sig = calculate_signature(auth, self.headers, 'POST', finish_taken_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(finish_taken_endpoint)
        self.ok(req)

        get_sig = calculate_signature(auth, self.headers, 'GET', taken_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(taken_endpoint)
        self.ok(req)
        taken = json.loads(req.body)

        self.assertTrue(taken['reviewWhetherCorrect'])

        self.convert_user_to_bank_instructor(bank_id)

        self.delete_item(auth, taken_endpoint)
        self.delete_item(auth, assessment_offering_detail_endpoint)

        self.delete_item(auth, assessment_detail_endpoint)

        item_1_endpoint = items_endpoint + item_1_id + '/'
        self.delete_item(auth, item_1_endpoint)
        self.delete_item(auth, bank_endpoint)


class AssessmentTakingTests(BaseAssessmentTestCase):
    def item_payload(self):
        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_body = 'can you manipulate this?'
        question_choices = [
            'yes',
            'no',
            'maybe'
        ]
        question_type = 'question-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        answer = 2
        answer_type = 'answer-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'

        return {
            "name"                  : item_name,
            "description"           : item_desc,
            "question"              : {
                "type"           : question_type,
                "questionString" : question_body,
                "choices"        : question_choices
            },
            "answers"               : [{
                "type"      : answer_type,
                "choiceId"  : answer
            }],
        }

    def setUp(self):
        super(AssessmentTakingTests, self).setUp()
        self.url += '/banks/' + unquote(str(self._bank.ident)) + '/items'

    def tearDown(self):
        """
        Remove the test user from all groups in Membership
        Start from the smallest groupId because need to
        remove "parental" roles like for DepartmentAdmin / DepartmentOfficer
        """
        super(AssessmentTakingTests, self).tearDown()

    def test_multi_question_taking(self):
        """
        Creating an assessment with multiple questions
        allows consumer to pick and choose which one is taken

        NOTE: this tests the simple, question-dump (client in control)
        for taking assessments
        :return:
        """
        auth = HTTPSignatureAuth(key_id=self.public_key,
                                 secret=self.private_key,
                                 algorithm='hmac-sha256',
                                 headers=self.signature_headers)
        name = 'atestbank'
        desc = 'for testing purposes only'
        bank_id = self.create_test_bank(auth, name, desc)

        bank_endpoint = self.endpoint + 'assessment/banks/' + bank_id + '/'
        items_endpoint = bank_endpoint + 'items/'

        get_sig = calculate_signature(auth, self.headers, 'GET', items_endpoint)

        # Use POST to create an item
        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_string = 'can you manipulate this?'
        question_type = 'question-record-type%3Alabel-ortho-faces%40ODL.MIT.EDU'
        answer_string = 'yes!'
        answer_type = 'answer-record-type%3Alabel-ortho-faces%40ODL.MIT.EDU'
        payload = {
            "name": item_name,
            "description": item_desc,
            "question": {
                "type": question_type,
                "questionString": question_string
            },
            "answers": [{
                "type": answer_type,
                "integerValues": {
                    "frontFaceValue": 1,
                    "sideFaceValue" : 2,
                    "topFaceValue"  : 3
                }
            }],
        }
        stringified_payload = deepcopy(payload)
        stringified_payload['manip'] = self.manip
        stringified_payload['frontView'] = self.front
        stringified_payload['sideView'] = self.side
        stringified_payload['topView'] = self.top
        stringified_payload['question'] = json.dumps(payload['question'])
        stringified_payload['answers'] = json.dumps(payload['answers'])

        post_sig = calculate_signature(auth, self.headers, 'POST', items_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(items_endpoint, stringified_payload)
        self.ok(req)

        item = json.loads(req.body)
        item_1_id = unquote(item['id'])
        question_1_id = unquote(self.extract_question(item)['id'])
        # expected_files_1 = self.extract_question(item)['files']

        # for this test, create a second item
        item_name_2 = 'a really complicated item'
        item_desc_2 = 'meant to differentiate students'
        question_string_2 = 'can you manipulate this second thing?'
        question_type = 'question-record-type%3Alabel-ortho-faces%40ODL.MIT.EDU'
        answer_type = 'answer-record-type%3Alabel-ortho-faces%40ODL.MIT.EDU'
        payload = {
            "name": item_name_2,
            "description": item_desc_2,
            "question": {
                "type": question_type,
                "questionString": question_string_2
            },
            "answers": [{
                "type": answer_type,
                "integerValues": {
                    "frontFaceValue": 4,
                    "sideFaceValue" : 5,
                    "topFaceValue"  : 0
                }
            }],
        }
        self.manip.seek(0)
        self.front.seek(0)
        self.side.seek(0)
        self.top.seek(0)
        stringified_payload = deepcopy(payload)
        stringified_payload['manip'] = self.manip
        stringified_payload['frontView'] = self.front
        stringified_payload['sideView'] = self.side
        stringified_payload['topView'] = self.top
        stringified_payload['question'] = json.dumps(payload['question'])
        stringified_payload['answers'] = json.dumps(payload['answers'])

        post_sig = calculate_signature(auth, self.headers, 'POST', items_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(items_endpoint, stringified_payload)
        self.ok(req)

        item = json.loads(req.body)
        item_2_id = unquote(item['id'])
        question_2_id = unquote(self.extract_question(item)['id'])
        # expected_files_2 = self.extract_question(item)['files']


        items_with_files = items_endpoint + '?files'
        get_sig = calculate_signature(auth, self.headers, 'GET', items_with_files)
        self.sign_client(get_sig)
        req = self.client.get(items_with_files)
        self.ok(req)
        expected_files_1 = json.loads(req.body)['data']['results'][0]['question']['files']
        expected_files_2 = json.loads(req.body)['data']['results'][1]['question']['files']

        # Now create an assessment, link the item2 to it,
        # and create an offering.
        # Use the offering_id to create the taken
        assessments_endpoint = bank_endpoint + 'assessments/'
        assessment_name = 'a really hard assessment'
        assessment_desc = 'meant to differentiate students'
        payload = {
            "name": assessment_name,
            "description": assessment_desc
        }
        post_sig = calculate_signature(auth, self.headers, 'POST', assessments_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(assessments_endpoint, payload, format='json')
        self.ok(req)
        assessment_id = unquote(json.loads(req.body)['id'])

        assessment_detail_endpoint = assessments_endpoint + assessment_id + '/'
        assessment_offering_endpoint = assessment_detail_endpoint + 'assessmentsoffered/'
        assessment_items_endpoint = assessment_detail_endpoint + 'items/'

        # POST should create the linkage
        payload = {
            'itemIds' : [item_1_id, item_2_id]
        }
        link_post_sig = calculate_signature(auth, self.headers, 'POST', assessment_items_endpoint)
        self.sign_client(link_post_sig)
        req = self.client.post(assessment_items_endpoint, payload, format='json')
        self.ok(req)


        # Use POST to create an offering
        offering_post_sig = calculate_signature(auth, self.headers, 'POST', assessment_offering_endpoint)
        self.sign_client(offering_post_sig)

        payload = {
            "startTime" : {
                "day"   : 1,
                "month" : 1,
                "year"  : 2015
            },
            "duration"  : {
                "days"  : 2
            }
        }


        self.sign_client(offering_post_sig)
        req = self.client.post(assessment_offering_endpoint, payload, format='json')
        self.ok(req)
        offering = json.loads(req.body)
        offering_id = unquote(offering['id'])

        assessment_offering_detail_endpoint = bank_endpoint + 'assessmentsoffered/' + offering_id + '/'

        # Can POST to create a new taken
        assessment_offering_takens_endpoint = assessment_offering_detail_endpoint + 'assessmentstaken/'
        post_sig = calculate_signature(auth, self.headers, 'POST', assessment_offering_takens_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(assessment_offering_takens_endpoint)
        self.ok(req)
        taken = json.loads(req.body)
        taken_id = unquote(taken['id'])

        # Instructor can now take the assessment
        taken_endpoint = bank_endpoint + 'assessmentstaken/' + taken_id + '/'

        # Only GET of this endpoint is supported
        taken_questions_endpoint = taken_endpoint + 'questions/'

        # Check that DELETE returns error code 405--we don't support this
        del_sig = calculate_signature(auth, self.headers, 'DELETE', taken_questions_endpoint)
        self.sign_client(del_sig)
        req = self.client.delete(taken_questions_endpoint)
        self.not_allowed(req, 'DELETE')

        # PUT to this root url also returns a 405
        put_sig = calculate_signature(auth, self.headers, 'PUT', taken_questions_endpoint)
        self.sign_client(put_sig)
        req = self.client.put(taken_questions_endpoint)
        self.not_allowed(req, 'PUT')

        # POST to this root url also returns a 405
        post_sig = calculate_signature(auth, self.headers, 'POST', taken_questions_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(taken_questions_endpoint)
        self.not_allowed(req, 'POST')

        taken_with_files = taken_questions_endpoint + '?files'
        get_sig = calculate_signature(auth, self.headers, 'GET', taken_with_files)
        self.sign_client(get_sig)
        req = self.client.get(taken_with_files)
        self.ok(req)
        questions = json.loads(req.body)
        question_1 = questions['data']['results'][0]
        question_2 = questions['data']['results'][1]
        self.verify_links(req, 'TakenQuestions')

        self.verify_question(question_1,
                             question_string,
                             question_type)
        self.verify_ortho_files(question_1, expected_files_1)

        self.verify_question(question_2,
                             question_string_2,
                             question_type)
        self.verify_ortho_files(question_2, expected_files_2)


        # Because this is an ortho3D problem, we expect
        # that the files endpoint also works
        question_1_endpoint = taken_questions_endpoint + question_1_id + '/'
        question_1_files_endpoint = question_1_endpoint + 'files/'
        question_1_status_endpoint = question_1_endpoint + 'status/'
        question_1_submit_endpoint = question_1_endpoint + 'submit/'
        question_2_endpoint = taken_questions_endpoint + question_2_id + '/'
        question_2_files_endpoint = question_2_endpoint + 'files/'
        question_2_status_endpoint = question_2_endpoint + 'status/'
        question_2_submit_endpoint = question_2_endpoint + 'submit/'

        # Check that DELETE returns error code 405--we don't support this
        del_sig = calculate_signature(auth, self.headers, 'DELETE', question_1_files_endpoint)
        self.sign_client(del_sig)
        req = self.client.delete(question_1_files_endpoint)
        self.not_allowed(req, 'DELETE')

        # PUT to this root url also returns a 405
        put_sig = calculate_signature(auth, self.headers, 'PUT', question_1_files_endpoint)
        self.sign_client(put_sig)
        req = self.client.put(question_1_files_endpoint)
        self.not_allowed(req, 'PUT')

        # POST to this root url also returns a 405
        post_sig = calculate_signature(auth, self.headers, 'POST', question_1_files_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(question_1_files_endpoint)
        self.not_allowed(req, 'POST')

        # POST, PUT, DELETE should not work on the status URLs
        # Check that DELETE returns error code 405--we don't support this
        del_sig = calculate_signature(auth, self.headers, 'DELETE', question_1_status_endpoint)
        self.sign_client(del_sig)
        req = self.client.delete(question_1_status_endpoint)
        self.not_allowed(req, 'DELETE')

        # PUT to this root url also returns a 405
        put_sig = calculate_signature(auth, self.headers, 'PUT', question_1_status_endpoint)
        self.sign_client(put_sig)
        req = self.client.put(question_1_status_endpoint)
        self.not_allowed(req, 'PUT')

        # POST to this root url also returns a 405
        post_sig = calculate_signature(auth, self.headers, 'POST', question_1_status_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(question_1_status_endpoint)
        self.not_allowed(req, 'POST')


        get_sig = calculate_signature(auth, self.headers, 'GET', question_1_files_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(question_1_files_endpoint)
        self.ok(req)
        self.verify_taking_files(req)

        get_sig = calculate_signature(auth, self.headers, 'GET', question_2_files_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(question_2_files_endpoint)
        self.ok(req)
        self.verify_taking_files(req)

        # checking on the question status now should return a not-responded
        get_sig = calculate_signature(auth, self.headers, 'GET', question_1_status_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(question_1_status_endpoint)
        self.not_responded(req)

        # Can submit a wrong response
        wrong_response = {
            "integerValues": {
                "frontFaceValue" : 0,
                "sideFaceValue"  : 1,
                "topFaceValue"   : 2
            }
        }

        # Check that DELETE returns error code 405--we don't support this
        del_sig = calculate_signature(auth, self.headers, 'DELETE', question_1_submit_endpoint)
        self.sign_client(del_sig)
        req = self.client.delete(question_1_submit_endpoint)
        self.not_allowed(req, 'DELETE')

        # PUT to this root url also returns a 405
        put_sig = calculate_signature(auth, self.headers, 'PUT', question_1_submit_endpoint)
        self.sign_client(put_sig)
        req = self.client.put(question_1_submit_endpoint)
        self.not_allowed(req, 'PUT')

        # GET to this root url also returns a 405
        get_sig = calculate_signature(auth, self.headers, 'GET', question_1_submit_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(question_1_submit_endpoint)
        self.not_allowed(req, 'GET')

        post_sig = calculate_signature(auth, self.headers, 'POST', question_1_submit_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(question_1_submit_endpoint, wrong_response, format='json')
        self.ok(req)
        self.verify_submission(req, _expected_result=False)

        # checking on the question status now should return a responded but wrong
        get_sig = calculate_signature(auth, self.headers, 'GET', question_1_status_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(question_1_status_endpoint)
        self.responded(req, False)

        # can resubmit using the specific ID
        right_response = {
            "integerValues": {
                "frontFaceValue" : 1,
                "sideFaceValue"  : 2,
                "topFaceValue"   : 3
            }
        }
        post_sig = calculate_signature(auth, self.headers, 'POST', question_1_submit_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(question_1_submit_endpoint, right_response, format='json')
        self.ok(req)
        self.verify_submission(req, _expected_result=True)

        # checking on the question status now should return a responsded, right
        get_sig = calculate_signature(auth, self.headers, 'GET', question_1_status_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(question_1_status_endpoint)
        self.responded(req, True)

        # checking on the second question status now should return a not-responded
        get_sig = calculate_signature(auth, self.headers, 'GET', question_2_status_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(question_2_status_endpoint)
        self.not_responded(req)

        # can submit to the second question in the assessment
        right_response = {
            "integerValues": {
                "frontFaceValue" : 4,
                "sideFaceValue"  : 5,
                "topFaceValue"   : 0
            }
        }
        post_sig = calculate_signature(auth, self.headers, 'POST', question_2_submit_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(question_2_submit_endpoint, right_response, format='json')
        self.ok(req)
        self.verify_submission(req, _expected_result=True)

        self.delete_item(auth, taken_endpoint)
        self.delete_item(auth, assessment_offering_detail_endpoint)
        self.delete_item(auth, assessment_detail_endpoint)

        item_1_endpoint = items_endpoint + item_1_id + '/'
        item_2_endpoint = items_endpoint + item_2_id + '/'
        self.delete_item(auth, item_1_endpoint)
        self.delete_item(auth, item_2_endpoint)
        self.delete_item(auth, bank_endpoint)

class BasicServiceTests(BaseAssessmentTestCase):
    """Test the views for getting the basic service calls

    """
    def setUp(self):
        super(BasicServiceTests, self).setUp()

    def tearDown(self):
        super(BasicServiceTests, self).tearDown()

    def test_users_can_get_list_of_banks(self):
        url = self.url + '/banks'
        req = self.app.get(url)
        self.ok(req)
        self.message(req, '[]')


class DragAndDropTests(BaseAssessmentTestCase):
    def setUp(self):
        super(DragAndDropTests, self).setUp()

        self._item = self.create_item(self._bank.ident)
        self._taken, self._offered = self.create_taken_for_item(self._bank.ident, self._item.ident)

        self.url += '/banks/' + unquote(str(self._bank.ident)) + '/items'

    def tearDown(self):
        super(DragAndDropTests, self).tearDown()


class MultipleChoiceTests(BaseAssessmentTestCase):
    def create_assessment_offered_for_item(self, bank_id, item_id):
        if isinstance(bank_id, basestring):
            bank_id = utilities.clean_id(bank_id)
        if isinstance(item_id, basestring):
            item_id = utilities.clean_id(item_id)

        bank = get_managers()['am'].get_bank(bank_id)
        form = bank.get_assessment_form_for_create([])
        form.display_name = 'a test assessment'
        form.description = 'for testing with'
        new_assessment = bank.create_assessment(form)

        bank.add_item(new_assessment.ident, item_id)

        form = bank.get_assessment_offered_form_for_create(new_assessment.ident, [])
        new_offered = bank.create_assessment_offered(form)

        return new_offered

    def create_item(self, bank_id):
        if isinstance(bank_id, basestring):
            bank_id = utilities.clean_id(bank_id)

        bank = get_managers()['am'].get_bank(bank_id)
        form = bank.get_item_form_for_create([EDX_ITEM_RECORD_TYPE])
        form.display_name = 'a test item!'
        form.description = 'for testing with'
        form.set_genus_type(NUMERIC_RESPONSE_ITEM_GENUS_TYPE)
        new_item = bank.create_item(form)

        form = bank.get_question_form_for_create(item_id=new_item.ident,
                                                 question_record_types=[NUMERIC_RESPONSE_QUESTION_RECORD_TYPE])
        form.set_text('foo?')
        bank.create_question(form)

        self.right_answer = float(2.04)
        self.tolerance = float(0.71)
        form = bank.get_answer_form_for_create(item_id=new_item.ident,
                                               answer_record_types=[NUMERIC_RESPONSE_ANSWER_RECORD_TYPE])
        form.set_decimal_value(self.right_answer)
        form.set_tolerance_value(self.tolerance)

        bank.create_answer(form)

        return bank.get_item(new_item.ident)

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
        super(MultipleChoiceTests, self).setUp()

        self._item = self.create_item(self._bank.ident)
        self._taken, self._offered = self.create_taken_for_item(self._bank.ident, self._item.ident)

        self.url += '/banks/' + unquote(str(self._bank.ident))

    def tearDown(self):
        super(MultipleChoiceTests, self).tearDown()

    def test_multiple_choice_questions_are_randomized_if_flag_set(self):
        edx_mc_q = Type(**QUESTION_RECORD_TYPES['multi-choice-edx'])
        edx_mc_a = Type(**ANSWER_RECORD_TYPES['multi-choice-edx'])

        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_body = 'can you manipulate this?'
        question_choices = [
            'yes',
            'no',
            'maybe'
        ]
        question_type = str(edx_mc_q)
        answer = 2
        answer_type = str(edx_mc_a)
        payload = {
            "name"          : item_name,
            "description"   : item_desc,
            "question"      : {
                "type"           : question_type,
                "rerandomize"    : "always",
                "questionString" : question_body,
                "choices"        : question_choices
            },
            "answers"       : [{
                "type"      : answer_type,
                "choiceId"  : answer
            }],
        }
        req = self.app.post(self.url + '/items',
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})

        self.ok(req)
        item = self.json(req)
        taken, offered = self.create_taken_for_item(self._bank.ident, item['id'])
        taken_url = '{0}/assessmentstaken/{2}/questions'.format(self.url,
                                                                unquote(str(self._bank.ident)),
                                                                unquote(str(taken.ident)))
        req = self.app.get(taken_url)
        self.ok(req)
        data = self.json(req)
        order_1 = data[0]['choices']

        req2 = self.app.get(taken_url)
        self.ok(req)
        data2 = self.json(req2)
        order_2 = data2[0]['choices']

        try:
            self.assertNotEqual(
                order_1,
                order_2
            )
        except AssertionError:
            # try again...it's random, so there is a slight chance it matches.
            # assume the probability of two matches in a row is slight.
            req3 = self.app.get(taken_url)
            self.ok(req)
            data3 = self.json(req3)
            order_3 = data3[0]['choices']
            self.assertNotEqual(
                order_1,
                order_3
            )

    def test_edx_multi_choice_answer_index_too_high(self):
        auth = HTTPSignatureAuth(key_id=self.public_key,
                                 secret=self.private_key,
                                 algorithm='hmac-sha256',
                                 headers=self.signature_headers)
        name = 'atestbank'
        desc = 'for testing purposes only'
        bank_id = self.create_test_bank(auth, name, desc)

        bank_endpoint = self.endpoint + 'assessment/banks/' + bank_id + '/'
        items_endpoint = bank_endpoint + 'items/'

        # Use POST to create an item--right now user is Learner,
        # so this should throw unauthorized
        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_body = 'can you answer this?'
        question_choices = [
            'yes',
            'no',
            'maybe'
        ]
        question_type = 'question-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        answer = 4
        answer_type = 'answer-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        post_sig = calculate_signature(auth, self.headers, 'POST', items_endpoint)
        self.sign_client(post_sig)
        payload = {
            "name"          : item_name,
            "description"   : item_desc,
            "question"      : {
                "type"           : question_type,
                "questionString" : question_body,
                "choices"        : question_choices
            },
            "answers"       : [{
                "type"      : answer_type,
                "choiceId"  : answer
            }],
        }

        req = self.client.post(items_endpoint,
                               payload,
                               format='json')
        self.code(req, 500)
        self.message(req,
                     'Correct answer 4 is not valid. Not that many choices!',
                     True)
        self.delete_item(auth, bank_endpoint)

    def test_edx_multi_choice_answer_index_too_low(self):
        auth = HTTPSignatureAuth(key_id=self.public_key,
                                 secret=self.private_key,
                                 algorithm='hmac-sha256',
                                 headers=self.signature_headers)
        name = 'atestbank'
        desc = 'for testing purposes only'
        bank_id = self.create_test_bank(auth, name, desc)

        bank_endpoint = self.endpoint + 'assessment/banks/' + bank_id + '/'
        items_endpoint = bank_endpoint + 'items/'

        # Use POST to create an item--right now user is Learner,
        # so this should throw unauthorized
        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_body = 'can you answer this?'
        question_choices = [
            'yes',
            'no',
            'maybe'
        ]
        question_type = 'question-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        answer = 0
        answer_type = 'answer-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        post_sig = calculate_signature(auth, self.headers, 'POST', items_endpoint)
        self.sign_client(post_sig)
        payload = {
            "name"          : item_name,
            "description"   : item_desc,
            "question"      : {
                "type"           : question_type,
                "questionString" : question_body,
                "choices"        : question_choices
            },
            "answers"       : [{
                "type"      : answer_type,
                "choiceId"  : answer
            }],
        }

        req = self.client.post(items_endpoint,
                               payload,
                               format='json')

        self.code(req, 500)
        self.message(req,
                     'Correct answer 0 is not valid. Must be between 1 and # of choices.',
                     True)
        self.delete_item(auth, bank_endpoint)

    def test_edx_multi_choice_answer_not_enough_choices(self):
        auth = HTTPSignatureAuth(key_id=self.public_key,
                                 secret=self.private_key,
                                 algorithm='hmac-sha256',
                                 headers=self.signature_headers)
        name = 'atestbank'
        desc = 'for testing purposes only'
        bank_id = self.create_test_bank(auth, name, desc)

        bank_endpoint = self.endpoint + 'assessment/banks/' + bank_id + '/'
        items_endpoint = bank_endpoint + 'items/'

        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_body = 'can you answer this?'
        question_choices = [
            'yes'
        ]
        question_type = 'question-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        answer = 1
        answer_type = 'answer-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        post_sig = calculate_signature(auth, self.headers, 'POST', items_endpoint)
        self.sign_client(post_sig)
        payload = {
            "name"          : item_name,
            "description"   : item_desc,
            "question"      : {
                "type"           : question_type,
                "questionString" : question_body,
                "choices"        : question_choices
            },
            "answers"       : [{
                "type"      : answer_type,
                "choiceId"  : answer
            }],
        }

        req = self.client.post(items_endpoint,
                               payload,
                               format='json')
        self.code(req, 500)
        self.message(req,
                     '"choices" is shorter than 2.',
                     True)
        self.delete_item(auth, bank_endpoint)

    def test_edx_multi_choice_crud(self):
        """
        Test an instructor can create and respond to an edX multiple choice
        type question.
        """
        auth = HTTPSignatureAuth(key_id=self.public_key,
                                 secret=self.private_key,
                                 algorithm='hmac-sha256',
                                 headers=self.signature_headers)
        name = 'atestbank'
        desc = 'for testing purposes only'
        bank_id = self.create_test_bank(auth, name, desc)

        bank_endpoint = self.endpoint + 'assessment/banks/' + bank_id + '/'
        items_endpoint = bank_endpoint + 'items/'

        # Use POST to create an item--right now user is Learner,
        # so this should throw unauthorized
        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_body = 'can you manipulate this?'
        question_choices = [
            'yes',
            'no',
            'maybe'
        ]
        question_type = 'question-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        answer = 2
        answer_type = 'answer-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        post_sig = calculate_signature(auth, self.headers, 'POST', items_endpoint)
        self.sign_client(post_sig)
        payload = {
            "name"          : item_name,
            "description"   : item_desc,
            "question"      : {
                "type"           : question_type,
                "questionString" : question_body,
                "choices"        : question_choices
            },
            "answers"       : [{
                "type"      : answer_type,
                "choiceId"  : answer
            }],
        }
        req = self.client.post(items_endpoint,
                               payload,
                               format='json')
        self.ok(req)
        item = self.load(req)
        item_id = unquote(item['id'])
        item_details_endpoint = bank_endpoint + 'items/' + item_id + '/'

        expected_answers = item['answers'][0]['choiceIds']

        # attach to an assessment -> offering -> taken
        # The user can now respond to the question and submit a response
        # first attach the item to an assessment
        # and create an offering.
        # Use the offering_id to create the taken
        assessments_endpoint = bank_endpoint + 'assessments/'
        assessment_name = 'a really hard assessment'
        assessment_desc = 'meant to differentiate students'
        payload = {
            "name": assessment_name,
            "description": assessment_desc
        }
        post_sig = calculate_signature(auth, self.headers, 'POST', assessments_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(assessments_endpoint, payload, format='json')
        self.ok(req)
        assessment_id = unquote(json.loads(req.body)['id'])

        assessment_detail_endpoint = assessments_endpoint + assessment_id + '/'
        assessment_offering_endpoint = assessment_detail_endpoint + 'assessmentsoffered/'
        assessment_items_endpoint = assessment_detail_endpoint + 'items/'

        # POST should create the linkage
        payload = {
            'itemIds' : [item_id]
        }
        link_post_sig = calculate_signature(auth, self.headers, 'POST', assessment_items_endpoint)
        self.sign_client(link_post_sig)
        req = self.client.post(assessment_items_endpoint, payload, format='json')
        self.ok(req)

        # Use POST to create an offering
        offering_post_sig = calculate_signature(auth, self.headers, 'POST', assessment_offering_endpoint)
        self.sign_client(offering_post_sig)

        payload = {
            "startTime" : {
                "day"   : 1,
                "month" : 1,
                "year"  : 2015
            },
            "duration"  : {
                "days"  : 2
            }
        }

        self.sign_client(offering_post_sig)
        req = self.client.post(assessment_offering_endpoint, payload, format='json')
        self.ok(req)
        offering = json.loads(req.body)
        offering_id = unquote(offering['id'])

        assessment_offering_detail_endpoint = bank_endpoint + 'assessmentsoffered/' + offering_id + '/'

        # Can POST to create a new taken
        assessment_offering_takens_endpoint = assessment_offering_detail_endpoint + 'assessmentstaken/'
        post_sig = calculate_signature(auth, self.headers, 'POST', assessment_offering_takens_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(assessment_offering_takens_endpoint)
        self.ok(req)
        taken = json.loads(req.body)
        taken_id = unquote(taken['id'])

        # Instructor can now take the assessment
        taken_endpoint = bank_endpoint + 'assessmentstaken/' + taken_id + '/'

        # Only GET of this endpoint is supported
        taken_questions_endpoint = taken_endpoint + 'questions/'
        # Submitting a non-list response is okay, if it is right, because
        # service will listify it
        bad_response = {
            'choiceIds': expected_answers[0]
        }
        taken_question_details_endpoint = taken_questions_endpoint + item_id + '/'
        taken_submit_endpoint = taken_question_details_endpoint + 'submit/'
        post_sig = calculate_signature(auth, self.headers, 'POST', taken_submit_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(taken_submit_endpoint, bad_response)
        self.ok(req)
        self.verify_submission(req, _expected_result=True)

        # Now can submit a list response to this endpoint
        response = {
            'choiceIds': expected_answers
        }
        req = self.client.post(taken_submit_endpoint, response, format='json')
        self.ok(req)
        self.verify_submission(req, _expected_result=True)

        self.delete_item(auth, taken_endpoint)
        self.delete_item(auth, assessment_offering_detail_endpoint)
        self.delete_item(auth, assessment_detail_endpoint)
        self.delete_item(auth, item_details_endpoint)
        self.delete_item(auth, bank_endpoint)

    def test_edx_multi_choice_missing_parameters(self):
        auth = HTTPSignatureAuth(key_id=self.public_key,
                                 secret=self.private_key,
                                 algorithm='hmac-sha256',
                                 headers=self.signature_headers)
        name = 'atestbank'
        desc = 'for testing purposes only'
        bank_id = self.create_test_bank(auth, name, desc)

        bank_endpoint = self.endpoint + 'assessment/banks/' + bank_id + '/'
        items_endpoint = bank_endpoint + 'items/'

        # Use POST to create an item--right now user is Learner,
        # so this should throw unauthorized
        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_body = 'can you answer this?'
        question_choices = [
            'yes',
            'no',
            'maybe'
        ]
        question_type = 'question-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        answer = 2
        answer_type = 'answer-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        post_sig = calculate_signature(auth, self.headers, 'POST', items_endpoint)
        self.sign_client(post_sig)
        payload = {
            "name"          : item_name,
            "description"   : item_desc,
            "question"      : {
                "type"           : question_type,
                "questionString" : question_body,
                "choices"        : question_choices
            },
            "answers"       : [{
                "type"      : answer_type,
                "choiceId"  : answer
            }],
        }

        params = ['questionString','choices','choiceId']
        for param in params:
            test_payload = deepcopy(payload)
            if param == 'choiceId':
                del test_payload['answers'][0][param]
            else:
                del test_payload['question'][param]
            req = self.client.post(items_endpoint,
                                   test_payload,
                                   format='json')
            self.code(req, 500)
            self.message(req,
                         '"' + param + '" required in input parameters but not provided.',
                         True)
        self.delete_item(auth, bank_endpoint)

    def test_edx_multi_choice_with_named_choices(self):
        """
        Test an instructor can create named choices with a dict
        """
        auth = HTTPSignatureAuth(key_id=self.public_key,
                                 secret=self.private_key,
                                 algorithm='hmac-sha256',
                                 headers=self.signature_headers)
        name = 'atestbank'
        desc = 'for testing purposes only'
        bank_id = self.create_test_bank(auth, name, desc)

        bank_endpoint = self.endpoint + 'assessment/banks/' + bank_id + '/'
        items_endpoint = bank_endpoint + 'items/'

        # Use POST to create an item--right now user is Learner,
        # so this should throw unauthorized
        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_body = 'can you manipulate this?'
        question_choices = [
            {'text' : 'I hope so.',
             'name' : 'yes'},
            {'text' : 'I don\'t think I can.',
             'name' : 'no'},
            {'text' : 'Maybe tomorrow.',
             'name' : 'maybe'}
        ]
        question_type = 'question-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        answer = 2
        answer_type = 'answer-record-type%3Amulti-choice-edx%40ODL.MIT.EDU'
        post_sig = calculate_signature(auth, self.headers, 'POST', items_endpoint)
        self.sign_client(post_sig)
        payload = {
            "name"          : item_name,
            "description"   : item_desc,
            "question"      : {
                "type"           : question_type,
                "questionString" : question_body,
                "choices"        : question_choices
            },
            "answers"       : [{
                "type"      : answer_type,
                "choiceId"  : answer
            }],
        }
        req = self.client.post(items_endpoint,
                               payload,
                               format='json')
        self.ok(req)

        item = self.load(req)
        item_details_endpoint = items_endpoint + unquote(item['id']) + '/'

        self.delete_item(auth, item_details_endpoint)
        self.delete_item(auth, bank_endpoint)

    def test_items_crud(self):
        """
        Create a test bank and test all things associated with items
        and a single item
        DELETE on root items/ does nothing. Error code 405.
        GET on root items/ gets you a list
        POST on root items/ creates a new item
        PUT on root items/ does nothing. Error code 405.

        For a single item detail:
        DELETE will delete that item
        GET brings up the item details with offerings and taken
        POST does nothing. Error code 405.
        PUT lets user update the name or description
        """
        auth = HTTPSignatureAuth(key_id=self.public_key,
                                 secret=self.private_key,
                                 algorithm='hmac-sha256',
                                 headers=self.signature_headers)
        name = 'atestbank'
        desc = 'for testing purposes only'
        bank_id = self.create_test_bank(auth, name, desc)

        bank_endpoint = self.endpoint + 'assessment/banks/' + bank_id + '/'
        items_endpoint = bank_endpoint + 'items/'

        # Check that DELETE returns error code 405--we don't support this
        del_sig = calculate_signature(auth, self.headers, 'DELETE', items_endpoint)
        self.sign_client(del_sig)
        req = self.client.delete(items_endpoint)
        self.not_allowed(req, 'DELETE')

        # PUT to this root url also returns a 405
        put_sig = calculate_signature(auth, self.headers, 'PUT', items_endpoint)
        self.sign_client(put_sig)
        req = self.client.put(items_endpoint)
        self.not_allowed(req, 'PUT')

        # GET for a Learner is unauthorized, should get 0 results back.
        self.convert_user_to_bank_learner(bank_id)
        get_sig = calculate_signature(auth, self.headers, 'GET', items_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(items_endpoint)
        self.no_results(req)

        # Use POST to create an item--right now user is Learner,
        # so this should throw unauthorized
        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        post_sig = calculate_signature(auth, self.headers, 'POST', items_endpoint)
        self.sign_client(post_sig)
        payload = {
            "name": item_name,
            "description": item_desc
        }
        req = self.client.post(items_endpoint, payload, format='json')
        self.unauthorized(req)

        # Use POST to create an item--right now user is Instructor,
        # so this should show up in GET
        self.convert_user_to_bank_instructor(bank_id)
        post_sig = calculate_signature(auth, self.headers, 'POST', items_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(items_endpoint, payload, format='json')
        self.ok(req)
        item_id = unquote(json.loads(req.body)['id'])
        self.verify_text(req,
                         'Item',
                         item_name,
                         item_desc)

        get_sig = calculate_signature(auth, self.headers, 'GET', items_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(items_endpoint)
        self.ok(req)
        self.verify_text(req,
                         'Item',
                         item_name,
                         item_desc,
                         item_id)
        self.verify_links(req, 'Item')

        # Now test PUT / GET / POST / DELETE on the new item
        # POST does nothing
        item_detail_endpoint = items_endpoint + item_id + '/'
        post_sig = calculate_signature(auth, self.headers, 'POST', item_detail_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(item_detail_endpoint)
        self.not_allowed(req, 'POST')

        # GET displays it, with self link
        get_sig = calculate_signature(auth, self.headers, 'GET', item_detail_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(item_detail_endpoint)

        self.ok(req)
        self.verify_text(req,
                         'Item',
                         item_name,
                         item_desc)
        self.verify_links(req, 'ItemDetails')

        # GET should still not work for Learner
        self.convert_user_to_bank_learner(bank_id)
        get_sig = calculate_signature(auth, self.headers, 'GET', item_detail_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(item_detail_endpoint)
        self.code(req, 500)

        # PUT should not work for a Learner, throw unauthorized
        put_sig = calculate_signature(auth, self.headers, 'PUT', item_detail_endpoint)
        self.sign_client(put_sig)
        new_item_name = 'a new item name'
        new_item_desc = 'to trick students'
        payload = {
            "name": new_item_name
        }
        req = self.client.put(item_detail_endpoint, payload, format='json')
        self.unauthorized(req)

        # PUT should work now. Modifies the item, with the changes reflected in GET
        self.convert_user_to_bank_instructor(bank_id)
        put_sig = calculate_signature(auth, self.headers, 'PUT', item_detail_endpoint)
        self.sign_client(put_sig)
        req = self.client.put(item_detail_endpoint, payload, format='json')
        self.ok(req)
        self.verify_text(req,
                         'Item',
                         new_item_name,
                         item_desc)

        get_sig = calculate_signature(auth, self.headers, 'GET', item_detail_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(item_detail_endpoint)
        self.ok(req)
        self.verify_text(req,
                         'Item',
                         new_item_name,
                         item_desc)
        self.verify_links(req, 'ItemDetails')

        self.sign_client(put_sig)
        payload = {
            "description": new_item_desc
        }
        req = self.client.put(item_detail_endpoint, payload, format='json')
        self.ok(req)
        self.verify_text(req,
                         'Item',
                         new_item_name,
                         new_item_desc)

        self.sign_client(get_sig)
        req = self.client.get(item_detail_endpoint)
        self.ok(req)
        self.verify_text(req,
                         'Item',
                         new_item_name,
                         new_item_desc)
        self.verify_links(req, 'ItemDetails')

        # trying to delete the bank as a DepartmentOfficer should
        # throw an exception
        self.convert_user_to_learner()
        del_sig = calculate_signature(auth, self.headers, 'DELETE', bank_endpoint)
        self.sign_client(del_sig)
        req = self.client.delete(bank_endpoint)
        self.unauthorized(req)
        self.convert_user_to_instructor()

        # trying to delete the bank with items should throw an error
        del_sig = calculate_signature(auth, self.headers, 'DELETE', bank_endpoint)
        self.sign_client(del_sig)
        req = self.client.delete(bank_endpoint)
        self.not_empty(req)

        self.delete_item(auth, item_detail_endpoint)
        self.delete_item(auth, bank_endpoint)

    def test_question_string_item_crud(self):
        """
        Test ability for user to POST a new question string and
        response string item
        """
        auth = HTTPSignatureAuth(key_id=self.public_key,
                                 secret=self.private_key,
                                 algorithm='hmac-sha256',
                                 headers=self.signature_headers)
        name = 'atestbank'
        desc = 'for testing purposes only'
        bank_id = self.create_test_bank(auth, name, desc)
        self.convert_user_to_bank_learner(bank_id)
        bank_endpoint = self.endpoint + 'assessment/banks/' + bank_id + '/'
        items_endpoint = bank_endpoint + 'items/'

        get_sig = calculate_signature(auth, self.headers, 'GET', items_endpoint)

        # Use POST to create an item--right now user is Learner,
        # so this should throw unauthorized
        item_name = 'a really complicated item'
        item_desc = 'meant to differentiate students'
        question_string = 'what is pi?'
        question_type = 'question-record-type%3Ashort-text-answer%40ODL.MIT.EDU'
        answer_string = 'dessert'
        answer_type = 'answer-record-type%3Ashort-text-answer%40ODL.MIT.EDU'
        post_sig = calculate_signature(auth, self.headers, 'POST', items_endpoint)
        self.sign_client(post_sig)
        payload = {
            "name": item_name,
            "description": item_desc,
            "question": {
                "type": question_type,
                "questionString": question_string
            },
            "answers": [{
                "type": answer_type,
                "responseString": answer_string
            }]
        }
        req = self.client.post(items_endpoint, payload, format='json')
        self.unauthorized(req)

        # Learners cannot GET?
        self.sign_client(get_sig)
        req = self.client.get(items_endpoint)
        self.no_results(req)

        # Use POST to create an item--right now user is Instructor,
        # so this should show up in GET
        self.convert_user_to_bank_instructor(bank_id)
        post_sig = calculate_signature(auth, self.headers, 'POST', items_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(items_endpoint, payload, format='json')
        self.ok(req)
        item = json.loads(req.body)
        item_id = unquote(item['id'])
        question_id = self.extract_question(item)['id']
        answer_id = self.extract_answers(item)[0]['id']
        self.verify_text(req,
                         'Item',
                         item_name,
                         item_desc)
        self.verify_questions_answers(req,
                                     question_string,
                                     question_type,
                                     [answer_string],
                                     [answer_type])

        get_sig = calculate_signature(auth, self.headers, 'GET', items_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(items_endpoint)
        self.ok(req)
        self.verify_text(req,
                         'Item',
                         item_name,
                         item_desc,
                         item_id)
        self.verify_questions_answers(req,
                                      question_string,
                                      question_type,
                                      [answer_string],
                                      [answer_type],
                                      item_id)
        self.verify_links(req, 'Item')

        # Now test PUT / GET / POST / DELETE on the new item
        # POST does nothing
        item_detail_endpoint = items_endpoint + item_id + '/'
        post_sig = calculate_signature(auth, self.headers, 'POST', item_detail_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(item_detail_endpoint)
        self.not_allowed(req, 'POST')

        # GET displays it, with self link
        get_sig = calculate_signature(auth, self.headers, 'GET', item_detail_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(item_detail_endpoint)
        self.ok(req)
        self.verify_text(req,
                         'Item',
                         item_name,
                         item_desc)
        self.verify_questions_answers(req,
                                      question_string,
                                      question_type,
                                      [answer_string],
                                      [answer_type])
        self.verify_links(req, 'ItemDetails')

        # GET of an item should not work for Learner
        self.convert_user_to_bank_learner(bank_id)
        get_sig = calculate_signature(auth, self.headers, 'GET', item_detail_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(item_detail_endpoint)
        self.code(req, 500)

        # PUT should work for Instructor.
        # Can modify the question and answers, reflected in GET
        new_question_string = 'what day is it?'
        new_answer_string = 'Saturday'

        payload = {
            'question': {
                'id' : question_id,
                'questionString': new_question_string,
                'type': question_type
            }
        }
        self.convert_user_to_bank_instructor(bank_id)

        put_sig = calculate_signature(auth, self.headers, 'PUT', item_detail_endpoint)
        self.sign_client(put_sig)
        req = self.client.put(item_detail_endpoint, payload, format='json')
        self.ok(req)
        self.verify_questions_answers(req,
                                      new_question_string,
                                      question_type,
                                      [answer_string],
                                      [answer_type])
        get_sig = calculate_signature(auth, self.headers, 'GET', item_detail_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(item_detail_endpoint)
        self.ok(req)
        self.verify_questions_answers(req,
                                      new_question_string,
                                      question_type,
                                      [answer_string],
                                      [answer_type])
        self.verify_links(req, 'ItemDetails')

        self.sign_client(put_sig)
        payload = {
            'answers': [{
                'id' : answer_id,
                'responseString': new_answer_string,
                'type': answer_type
            }]
        }
        req = self.client.put(item_detail_endpoint, payload, format='json')
        self.ok(req)
        self.verify_questions_answers(req,
                                      new_question_string,
                                      question_type,
                                      [new_answer_string],
                                      [answer_type])

        self.sign_client(get_sig)
        req = self.client.get(item_detail_endpoint)
        self.ok(req)
        self.verify_questions_answers(req,
                                      new_question_string,
                                      question_type,
                                      [new_answer_string],
                                      [answer_type])
        self.verify_links(req, 'ItemDetails')

        # Verify that GET, PUT to question/ endpoint works
        item_question_endpoint = item_detail_endpoint + 'question/'
        # Check that DELETE returns error code 405--we don't support this
        del_sig = calculate_signature(auth, self.headers, 'DELETE', item_question_endpoint)
        self.sign_client(del_sig)
        req = self.client.delete(item_question_endpoint)
        self.not_allowed(req, 'DELETE')

        # POST to this root url also returns a 405
        post_sig = calculate_signature(auth, self.headers, 'POST', item_question_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(item_question_endpoint)
        self.not_allowed(req, 'POST')

        get_sig = calculate_signature(auth, self.headers, 'GET', item_question_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(item_question_endpoint)
        self.ok(req)
        self.verify_question(req, new_question_string, question_type)

        newer_question_string = 'yet another new question?'
        put_sig = calculate_signature(auth, self.headers, 'PUT', item_question_endpoint)
        self.sign_client(put_sig)
        payload = {
            "id"             : question_id,
            "questionString" : newer_question_string,
            "type"           : question_type
        }
        req = self.client.put(item_question_endpoint, payload, format='json')

        self.sign_client(get_sig)
        req = self.client.get(item_question_endpoint)
        self.ok(req)
        self.verify_question(req, newer_question_string, question_type)

        # Verify that GET, POST (answers/) and
        # GET, DELETE, PUT to answers/<id> endpoint work
        # Verify that invalid answer_id returns "Answer not found."
        item_answers_endpoint = item_detail_endpoint + 'answers/'

        # Check that DELETE returns error code 405--we don't support this
        del_sig = calculate_signature(auth, self.headers, 'DELETE', item_answers_endpoint)
        self.sign_client(del_sig)
        req = self.client.delete(item_answers_endpoint)
        self.not_allowed(req, 'DELETE')

        # PUT to this root url also returns a 405
        put_sig = calculate_signature(auth, self.headers, 'PUT', item_answers_endpoint)
        self.sign_client(put_sig)
        req = self.client.put(item_answers_endpoint)
        self.not_allowed(req, 'PUT')

        get_sig = calculate_signature(auth, self.headers, 'GET', item_answers_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(item_answers_endpoint)
        self.ok(req)
        self.verify_answers(req, [new_answer_string], [answer_type])

        second_answer_string = "a second answer"
        payload = [{
            "responseString"    : second_answer_string,
            "type"              : answer_type
        }]
        post_sig = calculate_signature(auth, self.headers, 'POST', item_answers_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(item_answers_endpoint, payload, format='json')
        self.ok(req)
        self.verify_answers(req,
                            [new_answer_string, second_answer_string],
                            [answer_type, answer_type])

        self.sign_client(get_sig)
        req = self.client.get(item_answers_endpoint)
        self.ok(req)
        self.verify_answers(req,
                            [new_answer_string, second_answer_string],
                            [answer_type, answer_type])

        fake_item_answer_detail_endpont = item_answers_endpoint + 'fakeid/'
        get_sig = calculate_signature(auth, self.headers, 'GET', fake_item_answer_detail_endpont)
        self.sign_client(get_sig)
        req = self.client.get(fake_item_answer_detail_endpont)
        self.answer_not_found(req)

        item_answer_detail_endpoint = item_answers_endpoint + unquote(answer_id) + '/'
        # Check that POST returns error code 405--we don't support this
        post_sig = calculate_signature(auth, self.headers, 'POST', item_answer_detail_endpoint)
        self.sign_client(post_sig)
        req = self.client.post(item_answer_detail_endpoint)
        self.not_allowed(req, 'POST')

        get_sig = calculate_signature(auth, self.headers, 'GET', item_answer_detail_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(item_answer_detail_endpoint)
        self.ok(req)
        self.verify_answers(req, [new_answer_string], [answer_type])

        put_sig = calculate_signature(auth, self.headers, 'PUT', item_answer_detail_endpoint)
        self.sign_client(put_sig)
        newer_answer_string = 'yes, another one'
        payload = {
            "responseString"    : newer_answer_string,
            "type"              : answer_type
        }
        req = self.client.put(item_answer_detail_endpoint, payload, format='json')
        self.ok(req)
        self.verify_answers(req, [newer_answer_string], [answer_type])

        self.sign_client(get_sig)
        req = self.client.get(item_answer_detail_endpoint)
        self.ok(req)
        self.verify_answers(req, [newer_answer_string], [answer_type])

        del_sig = calculate_signature(auth, self.headers, 'DELETE', item_answer_detail_endpoint)
        self.sign_client(del_sig)
        req = self.client.delete(item_answer_detail_endpoint)
        self.ok(req)

        get_sig = calculate_signature(auth, self.headers, 'GET', item_answers_endpoint)
        self.sign_client(get_sig)
        req = self.client.get(item_answers_endpoint)
        self.ok(req)
        self.verify_answers(req,
                            [second_answer_string],
                            [answer_type])
        # self.verify_data_length(req, 1)
        self.assertEqual(
            self.load(req)['data']['count'],
            1
        )


        # trying to delete the bank as a DepartmentOfficer should
        # throw an exception
        self.convert_user_to_learner()
        del_sig = calculate_signature(auth, self.headers, 'DELETE', bank_endpoint)
        self.sign_client(del_sig)
        req = self.client.delete(bank_endpoint)
        self.unauthorized(req)
        self.convert_user_to_instructor()

        # trying to delete the bank with items should throw an error
        del_sig = calculate_signature(auth, self.headers, 'DELETE', bank_endpoint)
        self.sign_client(del_sig)
        req = self.client.delete(bank_endpoint)
        self.not_empty(req)

        self.delete_item(auth, item_detail_endpoint)
        self.delete_item(auth, bank_endpoint)



class NumericAnswerTests(BaseAssessmentTestCase):
    def create_assessment_offered_for_item(self, bank_id, item_id):
        if isinstance(bank_id, basestring):
            bank_id = utilities.clean_id(bank_id)
        if isinstance(item_id, basestring):
            item_id = utilities.clean_id(item_id)

        bank = get_managers()['am'].get_bank(bank_id)
        form = bank.get_assessment_form_for_create([])
        form.display_name = 'a test assessment'
        form.description = 'for testing with'
        new_assessment = bank.create_assessment(form)

        bank.add_item(new_assessment.ident, item_id)

        form = bank.get_assessment_offered_form_for_create(new_assessment.ident, [])
        new_offered = bank.create_assessment_offered(form)

        return new_offered

    def create_item(self, bank_id):
        if isinstance(bank_id, basestring):
            bank_id = utilities.clean_id(bank_id)

        bank = get_managers()['am'].get_bank(bank_id)
        form = bank.get_item_form_for_create([EDX_ITEM_RECORD_TYPE])
        form.display_name = 'a test item!'
        form.description = 'for testing with'
        form.set_genus_type(NUMERIC_RESPONSE_ITEM_GENUS_TYPE)
        new_item = bank.create_item(form)

        form = bank.get_question_form_for_create(item_id=new_item.ident,
                                                 question_record_types=[NUMERIC_RESPONSE_QUESTION_RECORD_TYPE])
        form.set_text('foo?')
        bank.create_question(form)

        self.right_answer = float(2.04)
        self.tolerance = float(0.71)
        form = bank.get_answer_form_for_create(item_id=new_item.ident,
                                               answer_record_types=[NUMERIC_RESPONSE_ANSWER_RECORD_TYPE])
        form.set_decimal_value(self.right_answer)
        form.set_tolerance_value(self.tolerance)

        bank.create_answer(form)

        return bank.get_item(new_item.ident)

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
        super(NumericAnswerTests, self).setUp()

        self._item = self.create_item(self._bank.ident)
        self._taken, self._offered = self.create_taken_for_item(self._bank.ident, self._item.ident)

        self.url += '/banks/' + unquote(str(self._bank.ident)) + '/'

    def tearDown(self):
        super(NumericAnswerTests, self).tearDown()

    def test_can_create_item(self):
        self.assertEqual(
            str(self._item.ident),
            str(self._item.ident)
        )

    def test_can_create_item_via_rest(self):
        payload = {
            'name': 'a clix testing question',
            'description': 'for testing clix items',
            'question': {
                'type': 'question-record-type%3Anumeric-response-edx%40ODL.MIT.EDU',
                'questionString': 'give me a number'
            },
            'answers': [{
                'decimalValue': -10.01,
                'tolerance': 0.1,
                'type': 'answer-record-type%3Anumeric-response-edx%40ODL.MIT.EDU'
            }]
        }
        req = self.app.post(self.url + 'items',
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            data['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            data['question']['text']['text'],
            payload['question']['questionString']
        )

        self.assertEqual(
            data['answers'][0]['decimalValue'],
            payload['answers'][0]['decimalValue']
        )

        self.assertEqual(
            data['answers'][0]['decimalValues']['tolerance'],
            payload['answers'][0]['tolerance']
        )

    def test_can_update_item_via_rest(self):
        url = '{0}items/{1}'.format(self.url,
                                    unquote(str(self._item.ident)))
        payload = {
            'answers': [{
                'id': str(self._item.get_answers().next().ident),
                'decimalValue': -10.01,
                'tolerance': 0.1,
                'type': 'answer-record-type%3Anumeric-response-edx%40ODL.MIT.EDU'
            }]
        }

        req = self.app.put(url,
                           params=json.dumps(payload),
                           headers={'content-type': 'application/json'})
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            data['id'],
            str(self._item.ident)
        )

        self.assertEqual(
            data['answers'][0]['decimalValue'],
            payload['answers'][0]['decimalValue']
        )

        self.assertEqual(
            data['answers'][0]['decimalValues']['tolerance'],
            payload['answers'][0]['tolerance']
        )

    def test_valid_response_returns_correct(self):
        url = '{0}assessmentstaken/{1}/questions/{2}/submit'.format(self.url,
                                                                    unquote(str(self._taken.ident)),
                                                                    unquote(str(self._item.ident)))
        payload = {
            'decimalValue': 1.5,
            'type': 'answer-record-type%3Anumeric-response-edx%40ODL.MIT.EDU'
        }

        req = self.app.post(url,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        data = self.json(req)
        self.assertTrue(data['correct'])
        self.assertEqual(
            data['feedback'],
            'No feedback available.'
        )

    def test_invalid_response_returns_incorrect(self):
        url = '{0}assessmentstaken/{1}/questions/{2}/submit'.format(self.url,
                                                                    unquote(str(self._taken.ident)),
                                                                    unquote(str(self._item.ident)))
        payload = {
            'decimalValue': 1.2,
            'type': 'answer-record-type%3Anumeric-response-edx%40ODL.MIT.EDU'
        }

        req = self.app.post(url,
                            params=json.dumps(payload),
                            headers={'content-type': 'application/json'})
        self.ok(req)
        data = self.json(req)
        self.assertFalse(data['correct'])
        self.assertEqual(
            data['feedback'],
            'No feedback available.'
        )
