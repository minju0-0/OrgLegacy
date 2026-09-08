from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from authentication.models import Profile


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_login_page_renders(self):
        response = self.client.get(reverse('authentication:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/login.html')

    def test_register_page_renders(self):
        response = self.client.get(reverse('authentication:register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/register.html')

    def test_registration_redirects_to_login_and_does_not_autologin(self):
        post_data = {
            'username': 'newuser',
            'email': 'newuser@orglegacy.edu',
            'password1': 'StrongPassword123!',
            'password2': 'StrongPassword123!',
        }
        response = self.client.post(reverse('authentication:register'), post_data, follow=True)

        # 1. Verify redirect to login page
        self.assertRedirects(response, reverse('authentication:login'))

        # 2. Verify User and Profile were created in DB with default member role
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@orglegacy.edu')
        self.assertEqual(user.profile.role, Profile.ROLE_MEMBER)
        self.assertEqual(user.profile.organization_name, '')
        self.assertEqual(user.profile.student_status, '')

        # 3. Verify user is NOT auto-logged in
        self.assertFalse(response.context['user'].is_authenticated)

        # 4. Verify success message appears on login page
        messages = list(response.context['messages'])
        self.assertTrue(any("created" in str(m).lower() for m in messages))

    def test_login_and_logout_flow(self):
        User.objects.create_user(username='loginuser', password='Password123!')
        login_response = self.client.post(reverse('authentication:login'), {
            'username': 'loginuser',
            'password': 'Password123!',
        })
        # After login, should redirect to home
        self.assertRedirects(login_response, reverse('home:home'))

        # Test POST logout redirects to login
        logout_response = self.client.post(reverse('authentication:logout'))
        self.assertRedirects(logout_response, reverse('authentication:login'))

    def test_logout_via_get_succeeds(self):
        User.objects.create_user(username='getuser', password='Password123!')
        self.client.post(reverse('authentication:login'), {
            'username': 'getuser',
            'password': 'Password123!',
        })
        # GET on logout should succeed without 405 Method Not Allowed
        response = self.client.get(reverse('authentication:logout'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/login.html')
        self.assertFalse(response.context['user'].is_authenticated)

    def test_root_url_redirects_to_login(self):
        response = self.client.get('/')
        self.assertRedirects(response, reverse('authentication:login'))

    def test_static_css_file_is_available(self):
        from django.contrib.staticfiles import finders
        result = finders.find('css/style.css')
        self.assertIsNotNone(result)

    def test_static_image_file_is_available(self):
        from django.contrib.staticfiles import finders
        result = finders.find('img/handover-table.jpg')
        self.assertIsNotNone(result)

    def test_login_invalid_credentials_shows_error(self):
        response = self.client.post(reverse('authentication:login'), {
            'username': 'nonexistent',
            'password': 'WrongPassword123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/login.html')
        self.assertTrue(response.context['form'].errors)

    def test_register_invalid_data_shows_field_errors(self):
        response = self.client.post(reverse('authentication:register'), {
            'username': '',
            'email': 'not-an-email',
            'password1': 'short',
            'password2': 'mismatch',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authentication/register.html')
        self.assertTrue(response.context['form'].errors)


