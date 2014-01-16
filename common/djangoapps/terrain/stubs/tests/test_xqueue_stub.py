"""
Unit tests for stub XQueue implementation.
"""

import mock
import unittest
import json
import requests
import time
import copy
from terrain.stubs.xqueue import StubXQueueService


class StubXQueueServiceTest(unittest.TestCase):

    def setUp(self):
        self.server = StubXQueueService()
        self.url = "http://127.0.0.1:{0}/xqueue/submit".format(self.server.port)
        self.addCleanup(self.server.shutdown)

        # For testing purposes, do not delay the grading response
        self.server.set_config('response_delay', 0)

    @mock.patch('terrain.stubs.xqueue.post')
    def test_grade_request(self, post):

        # Post a submission to the stub XQueue
        callback_url = 'http://127.0.0.1:8000/test_callback'
        expected_header = self._post_submission(
            callback_url, 'test_queuekey', 'test_queue',
            json.dumps({
                'student_info': 'test',
                'grader_payload': 'test',
                'student_response': 'test'
            })
        )

        # Check the response we receive
        # (Should be the default grading response)
        expected_body = json.dumps({'correct': True, 'score': 1, 'msg': '<div></div>'})
        self._check_grade_response(post, callback_url, expected_header, expected_body)

    @mock.patch('terrain.stubs.xqueue.post')
    def test_configure_global_response(self, post):

        # Configure the default response for submissions to any queue
        response_content = {'test_response': 'test_content'}
        self.server.set_config('global_grade_response', response_content)

        # Post a submission to the stub XQueue
        callback_url = 'http://127.0.0.1:8000/test_callback'
        expected_header = self._post_submission(
            callback_url, 'test_queuekey', 'test_queue',
            json.dumps({
                'student_info': 'test',
                'grader_payload': 'test',
                'student_response': 'test'
            })
        )

        # Check the response we receive
        # (Should be the default grading response)
        self._check_grade_response(
            post, callback_url, expected_header, json.dumps(response_content)
        )

    @mock.patch('terrain.stubs.xqueue.post')
    def test_configure_queue_response(self, post):

        # Configure the XQueue stub response to any submission to the test queue
        response_content = {'test_response': 'test_content'}
        self.server.set_config('test_queue', response_content)

        # Post a submission to the XQueue stub
        callback_url = 'http://127.0.0.1:8000/test_callback'
        expected_header = self._post_submission(
            callback_url, 'test_queuekey', 'test_queue', 'test_body'
        )

        # Check that we receive the response we configured
        self._check_grade_response(
            post, callback_url, expected_header, json.dumps(response_content)
        )

    def _post_submission(self, callback_url, lms_key, queue_name, xqueue_body):
        """
        Post a submission to the stub XQueue implementation.
        `callback_url` is the URL at which we expect to receive a grade response
        `lms_key` is the authentication key sent in the header
        `queue_name` is the name of the queue in which to send put the submission
        `xqueue_body` is the content of the submission

        Returns the header (a string) we send with the submission, which can
        be used to validate the response we receive from the stub.
        """

        # Post a submission to the XQueue stub
        grade_request = {
            'xqueue_header': json.dumps({
                'lms_callback_url': callback_url,
                'lms_key': 'test_queuekey',
                'queue_name': 'test_queue'
            }),
            'xqueue_body': xqueue_body
        }

        resp = requests.post(self.url, data=grade_request)

        # Expect that the response is success
        self.assertEqual(resp.status_code, 200)

        # Return back the header, so we can authenticate the response we receive
        return grade_request['xqueue_header']

    def _check_grade_response(self, post_mock, callback_url, expected_header, expected_body):
        """
        Verify that the stub sent a POST request back to us
        with the expected data.

        `post_mock` is our mock for `requests.post`
        `callback_url` is the URL we expect the stub to POST to
        `expected_header` is the header (a string) we expect to receive with the grade.
        `expected_body` is the content (a string) we expect to receive with the grade.

        Raises an `AssertionError` if the check fails.
        """

        # Wait for the server to POST back to the callback URL
        # Time out if it takes too long
        start_time = time.time()
        while time.time() - start_time < 10:
            if post_mock.called:
                break
            time.sleep(1)

        # Check the response posted back to us
        # This is the default response
        expected_callback_dict = {
            'xqueue_header': expected_header,
            'xqueue_body': expected_body,
        }

        # Check that the POST request was made with the correct params
        post_mock.assert_called_with(callback_url, data=expected_callback_dict)
