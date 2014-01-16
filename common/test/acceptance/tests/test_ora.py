"""
Tests for ORA (Open Response Assessment) through the LMS UI.
"""

from bok_choy.web_app_test import WebAppTest
from ..edxapp_pages.studio.auto_auth import AutoAuthPage
from ..edxapp_pages.lms.course_info import CourseInfoPage
from ..edxapp_pages.lms.tab_nav import TabNavPage
from ..edxapp_pages.lms.course_nav import CourseNavPage
from ..edxapp_pages.lms.open_response import OpenResponsePage
from ..fixtures.course import XBlockFixtureDesc, CourseFixture

from .helpers import load_data_str


class OpenResponseTest(WebAppTest):
    """
    Tests that interact with ORA (Open Response Assessment) through the LMS UI.
    """

    page_object_classes = [
        AutoAuthPage, CourseInfoPage, TabNavPage,
        CourseNavPage, OpenResponsePage
    ]

    def setUp(self):
        """
        Always start in the subsection with open response problems.
        """

        # Create a unique course ID
        self.course_info = {
            'org': 'test_org',
            'number': self.unique_id,
            'run': 'test_run',
            'display_name': 'Test Course' + self.unique_id
        }

        # Ensure fixtures are installed
        super(OpenResponseTest, self).setUp()

        # Log in and navigate to the essay problems
        course_id = '{org}/{number}/{run}'.format(**self.course_info)
        self.ui.visit('studio.auto_auth', course_id=course_id)
        self.ui.visit('lms.course_info', course_id=course_id)
        self.ui['lms.tab_nav'].go_to_tab('Courseware')
        self.ui['lms.course_nav'].go_to_section(
            'Example Week 2: Get Interactive', 'Homework - Essays'
        )


    @property
    def fixtures(self):
        """
        Create a test course with open response problems.
        """
        course_fix = CourseFixture(
            self.course_info['org'], self.course_info['number'],
            self.course_info['run'], self.course_info['display_name']
        )

        course_fix.add_children(
            XBlockFixtureDesc('chapter', 'Test Section').add_children(
                XBlockFixtureDesc('sequential', 'Test Subsection').add_children(
                    XBlockFixtureDesc('combinedopenended', 'Self-Assessed', data=load_data_str('ora_self_problem.xml')),
                    XBlockFixtureDesc('combinedopenended', 'AI-Assessed', data=load_data_str('ora_ai_problem.xml'))
                )
            )
        )

        return [course_fix]

    def submit_essay(self, expected_assessment_type, expected_prompt):
        """
        Submit an essay and verify that the problem uses
        the `expected_assessment_type` ("self", "ai", or "peer") and
        shows the `expected_prompt` (a string).
        """

        # Check the assessment type and prompt
        self.assertEqual(self.ui['lms.open_response'].assessment_type, expected_assessment_type)
        self.assertIn(expected_prompt, self.ui['lms.open_response'].prompt)

        # Enter a response
        essay = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Ut vehicula."
        self.ui['lms.open_response'].set_response(essay)

        # Save the response and expect some UI feedback
        self.ui['lms.open_response'].save_response()
        self.assertEqual(
            self.ui['lms.open_response'].alert_message,
            "Answer saved, but not yet submitted."
        )

        # Submit the response
        self.ui['lms.open_response'].submit_response()


class SelfAssessmentTest(OpenResponseTest):
    """
    Test ORA self-assessment.
    """

    def test_self_assessment(self):
        """
        Given I am viewing a self-assessment problem
        When I submit an essay and complete a self-assessment rubric
        Then I see a scored rubric
        And I see my score in the progress page.
        """
        # Navigate to the self-assessment problem and submit an essay
        self.ui['lms.course_nav'].go_to_sequential('Self-Assessed')
        self.submit_essay('self', 'Censorship in the Libraries')

        # Check the rubric categories
        self.assertEqual(
            self.ui['lms.open_response'].rubric_categories,
            ["Writing Applications", "Language Conventions"]
        )

        # Fill in the self-assessment rubric
        self.ui['lms.open_response'].submit_self_assessment([0, 1])

        # Expect that we get feedback
        self.assertEqual(
            self.ui['lms.open_response'].rubric_feedback,
            ['incorrect', 'correct']
        )


class AIAssessmentTest(OpenResponseTest):
    """
    Test ORA AI-assessment.
    """

    def test_ai_assessment(self):
        """
        Given I am viewing an AI-assessment problem that has a trained ML model
        When I submit an essay and wait for a response
        Then I see a scored rubric
        And I see my score in the progress page.
        """

        # Navigate to the AI-assessment problem and submit an essay
        self.ui['lms.course_nav'].go_to_sequential('AI-Assessed')
        self.submit_essay('ai', 'Censorship in the Libraries')

        # Expect UI feedback that the response was submitted
        self.assertEqual(
            self.ui['lms.open_response'].grader_status,
            "Your response has been submitted. Please check back later for your grade."
        )

        from nose.tools import set_trace; set_trace()


class PeerAssessmentTest(OpenResponseTest):
    """
    Test ORA peer-assessment.
    """

    def test_calibration(self):
        """
        Given I am viewing a peer-assessment problem
        And the instructor has submitted enough example essays
        When I submit submit acceptable scores for enough calibration essays
        Then I am able to peer-grade other students' essays.
        """
        pass

    def test_submit_feedback(self):
        """
        Given I am viewing another student's essay in peer-grading
        When I submit rubric scores and written feedback
        Then I see that my feedback has been submitted.
        """
        pass

    def test_receive_feedback(self):
        """
        Given I have submitted an essay for peer-assessment
        And enough other students have scored my essay
        Then I can view the scores and written feedback
        And I see my score in the progress page.
        """
        pass
