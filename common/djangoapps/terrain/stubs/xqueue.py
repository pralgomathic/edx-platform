"""
Stub implementation of XQueue for acceptance tests.

Configuration values:
    "global_grade_response" (dict): Default response to be sent to LMS as a grade for a submission
    "<queue_name>" (dict): Grade response to return for submissions to the queue called <queue_name>

If no grade response is configured, a default response will be returned.
"""

from .http import StubHttpRequestHandler, StubHttpService
import json
import copy
from requests import post
import threading


class StubXQueueHandler(StubHttpRequestHandler):
    """
    A handler for XQueue POST requests.
    """

    DEFAULT_RESPONSE_DELAY = 2
    DEFAULT_GRADE_RESPONSE = {'correct': True, 'score': 1, 'msg': ''}

    def do_POST(self):
        """
        Handle a POST request from the client

        Sends back an immediate success/failure response.
        It then POSTS back to the client with grading results.
        """
        msg = "XQueue received POST request {0} to path {1}".format(self.post_dict, self.path)
        self.log_message(msg)

        # Respond only to grading requests
        if self._is_grade_request():
            try:
                xqueue_header = json.loads(self.post_dict['xqueue_header'])
                callback_url = xqueue_header['lms_callback_url']
                queue_name = xqueue_header['queue_name']

            except KeyError:
                # If the message doesn't have a header or body,
                # then it's malformed.  Respond with failure
                error_msg = "XQueue received invalid grade request"
                self._send_immediate_response(False, message=error_msg)

            except ValueError:
                # If we could not decode the body or header,
                # respond with failure
                error_msg = "XQueue could not decode grade request"
                self._send_immediate_response(False, message=error_msg)

            else:
                # Send an immediate response of success
                # The grade request is formed correctly
                self._send_immediate_response(True)

                # Wait a bit before POSTing back to the callback url with the
                # grade result configured by the server
                # Otherwise, the problem will not realize it's
                # queued and it will keep waiting for a response indefinitely
                delayed_grade_func = lambda: self._send_grade_response(
                    callback_url, queue_name, xqueue_header
                )

                threading.Timer(
                    self.server.config('response_delay', default=self.DEFAULT_RESPONSE_DELAY),
                    delayed_grade_func
                ).start()

        # If we get a request that's not to the grading submission
        # URL, return an error
        else:
            self._send_immediate_response(False, message="Invalid request URL")

    def _send_immediate_response(self, success, message=""):
        """
        Send an immediate success/failure message
        back to the client
        """

        # Send the response indicating success/failure
        response_str = json.dumps(
            {'return_code': 0 if success else 1, 'content': message}
        )

        if self._is_grade_request():
            self.send_response(
                200, content=response_str, headers={'Content-type': 'text/plain'}
            )
            self.log_message("XQueue: sent response {0}".format(response_str))

        else:
            self.send_response(500)

    def _send_grade_response(self, postback_url, queue_name, xqueue_header):
        """
        POST the grade response back to the client
        using the response provided by the server configuration.

        Uses the server configuration to determine what response to send:
        1) Specific response for submissions to `queue_name`
        2) Global submission configured by client
        3) Default submission

        `postback_url` is the URL the client told us to post back to
        `queue_name` is the name of the queue the submission was sent to
        `xqueue_header` is the full header the client sent us, which we will send back
        to the client so it can authenticate us.
        """
        # First check if we have a configured response for this queue
        grade_response = self.server.config(queue_name)

        # Fall back to the global grade response configured for this queue,
        # then to the default response.
        if grade_response is None:
            grade_response = self.server.config(
                'global_grade_response', default=copy.deepcopy(self.DEFAULT_GRADE_RESPONSE)
            )

        # Wrap the message in <div> tags to ensure that it is valid XML
        if isinstance(grade_response, dict) and 'msg' in grade_response:
            grade_response['msg'] = "<div>{0}</div>".format(grade_response['msg'])

        data = {
            'xqueue_header': json.dumps(xqueue_header),
            'xqueue_body': json.dumps(grade_response)
        }

        post(postback_url, data=data)
        self.log_message("XQueue: sent grading response {0} to {1}".format(data, postback_url))

    def _is_grade_request(self):
        return 'xqueue/submit' in self.path


class StubXQueueService(StubHttpService):
    """
    A stub XQueue grading server that responds to POST requests to localhost.
    """

    HANDLER_CLASS = StubXQueueHandler
