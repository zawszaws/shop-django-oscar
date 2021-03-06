import re

from django.core import mail
from django.core.urlresolvers import reverse
from django_webtest import WebTest

from oscar.test.testcases import WebTestCase
from oscar.core.compat import get_user_model


User = get_user_model()


class TestAUserWhoseForgottenHerPassword(WebTest):

    def test_can_reset_her_password(self):
        username, email, password = 'lucy', 'lucy@example.com', 'password'
        User.objects.create_user(username, email, password)

        # Fill in password reset form
        page = self.app.get(reverse('password-reset'))
        form = page.forms['password_reset_form']
        form['email'] = email
        response = form.submit()

        # Response should be a redirect and an email should have been sent
        self.assertEqual(302, response.status_code)
        self.assertEqual(1, len(mail.outbox))

        # Extract URL from email
        email_body = mail.outbox[0].body
        urlfinder = re.compile(r"http://example.com(?P<path>[-A-Za-z0-9\/\._]+)")
        matches = urlfinder.search(email_body, re.MULTILINE)
        self.assertTrue('path' in matches.groupdict())
        path = matches.groupdict()['path']

        # Reset password and check we get redirect
        reset_page = self.app.get(path)
        form = reset_page.forms['password_reset_form']
        form['new_password1'] = 'monkey'
        form['new_password2'] = 'monkey'
        response = form.submit()
        self.assertEqual(302, response.status_code)

        # Now attempt to login with new password
        url = reverse('customer:login')
        form = self.app.get(url).forms['login_form']
        form['login-username'] = email
        form['login-password'] = 'monkey'
        response = form.submit('login_submit')
        self.assertEqual(302, response.status_code)


class TestAnAuthenticatedUser(WebTestCase):
    is_anonymous = False

    def test_receives_an_email_when_their_password_is_changed(self):
        page = self.get(reverse('customer:change-password'))
        form = page.forms['change_password_form']
        form['old_password'] = self.password
        form['new_password1'] = u'anotherfancypassword'
        form['new_password2'] = u'anotherfancypassword'
        page = form.submit()

        self.assertEquals(len(mail.outbox), 1)
        self.assertIn("your password has been changed", mail.outbox[0].body)

    def test_cannot_access_reset_password_page(self):
        response = self.get(reverse('password-reset'), status=403)
        self.assertEqual(403, response.status_code)

    def test_does_not_receive_an_email_when_their_profile_is_updated_but_email_address_not_changed(self):
        page = self.get(reverse('customer:profile-update'))
        form = page.forms['profile_form']
        form['first_name'] = "Terry"
        form.submit()
        self.assertEquals(len(mail.outbox), 0)

    def test_receives_an_email_when_their_email_address_is_changed(self):
        page = self.get(reverse('customer:profile-update'))
        form = page.forms['profile_form']

        new_email = 'a.new.email@user.com'
        form['email'] = new_email
        page = form.submit()

        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals(mail.outbox[0].to[0], self.email)
        self.assertEquals(User.objects.get(id=self.user.id).email, new_email)
        self.assertIn("your email address has been changed",
                      mail.outbox[0].body)


class TestAnAnonymousUser(WebTestCase):

    def assertCanLogin(self, email, password):
        url = reverse('customer:login')
        form = self.app.get(url).forms['login_form']
        form['login-username'] = email
        form['login-password'] = password
        response = form.submit('login_submit')
        self.assertRedirectsTo(response, 'customer:summary')

    def test_can_login(self):
        email, password = 'd@d.com', 'mypassword'
        User.objects.create_user('_', email, password)
        self.assertCanLogin(email, password)

    def test_can_login_with_email_containing_capitals_in_local_part(self):
        email, password = 'Andrew.Smith@test.com', 'mypassword'
        User.objects.create_user('_', email, password)
        self.assertCanLogin(email, password)

    def test_can_login_with_email_containing_capitals_in_host(self):
        email, password = 'Andrew.Smith@teSt.com', 'mypassword'
        User.objects.create_user('_', email, password)
        self.assertCanLogin(email, password)

    def test_can_register(self):
        url = reverse('customer:register')
        form = self.app.get(url).forms['register_form']
        form['registration-email'] = 'terry@boom.com'
        form['registration-password1'] = 'hedgehog'
        form['registration-password2'] = 'hedgehog'
        response = form.submit()
        self.assertRedirectsTo(response, 'customer:summary')
