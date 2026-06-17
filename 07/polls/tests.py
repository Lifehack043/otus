"""
Тесты для приложения polls.
"""

import datetime

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from .models import Choice, Question


class QuestionModelTests(TestCase):
    """Тесты модели Question."""

    def test_str_representation(self):
        """str() возвращает question_text."""
        q = Question(question_text="What's new?")
        self.assertEqual(str(q), "What's new?")

    def test_was_published_recently_with_future_question(self):
        """was_published_recently() возвращает False для будущих вопросов."""
        time = timezone.now() + datetime.timedelta(days=30)
        future_question = Question(pub_date=time)
        self.assertIs(future_question.was_published_recently(), False)

    def test_was_published_recently_with_old_question(self):
        """was_published_recently() возвращает False для старых вопросов."""
        time = timezone.now() - datetime.timedelta(days=1, seconds=1)
        old_question = Question(pub_date=time)
        self.assertIs(old_question.was_published_recently(), False)

    def test_was_published_recently_with_recent_question(self):
        """was_published_recently() возвращает True для недавних вопросов."""
        time = timezone.now() - datetime.timedelta(hours=1)
        recent_question = Question(pub_date=time)
        self.assertIs(recent_question.was_published_recently(), True)

    def test_get_absolute_url(self):
        """get_absolute_url() возвращает правильный URL."""
        q = Question.objects.create(
            question_text="Test question",
            pub_date=timezone.now(),
        )
        self.assertEqual(q.get_absolute_url(), f"/polls/{q.pk}/")


class ChoiceModelTests(TestCase):
    """Тесты модели Choice."""

    def setUp(self):
        self.question = Question.objects.create(
            question_text="What is your favorite color?",
            pub_date=timezone.now(),
        )

    def test_str_representation(self):
        """str() возвращает choice_text."""
        choice = Choice(choice_text="Red", question=self.question)
        self.assertEqual(str(choice), "Red")

    def test_relation_to_question(self):
        """Choice связан с Question."""
        choice = Choice.objects.create(
            choice_text="Blue",
            question=self.question,
        )
        self.assertEqual(choice.question, self.question)

    def test_default_votes(self):
        """По умолчанию votes = 0."""
        choice = Choice.objects.create(
            choice_text="Green",
            question=self.question,
        )
        self.assertEqual(choice.votes, 0)


class QuestionIndexViewTests(TestCase):
    """Тесты главной страницы (index view)."""

    def test_empty_index(self):
        """При отсутствии вопросов показывается сообщение."""
        response = self.client.get(reverse("polls:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Нет доступных опросов")
        self.assertQuerySetEqual(response.context["latest_questions"], [])

    def test_recent_questions(self):
        """Недавние вопросы отображаются на главной."""
        Question.objects.create(
            question_text="Recent question",
            pub_date=timezone.now(),
        )
        response = self.client.get(reverse("polls:index"))
        self.assertContains(response, "Recent question")
        self.assertEqual(len(response.context["latest_questions"]), 1)

    def test_future_questions_not_shown(self):
        """Будущие вопросы не отображаются на главной."""
        Question.objects.create(
            question_text="Future question",
            pub_date=timezone.now() + datetime.timedelta(days=30),
        )
        response = self.client.get(reverse("polls:index"))
        self.assertContains(response, "Нет доступных опросов")

    def test_questions_ordered_by_date(self):
        """Вопросы отсортированы по дате (новые сначала)."""
        Question.objects.create(
            question_text="Old question",
            pub_date=timezone.now() - datetime.timedelta(days=5),
        )
        Question.objects.create(
            question_text="New question",
            pub_date=timezone.now(),
        )
        response = self.client.get(reverse("polls:index"))
        questions = response.context["latest_questions"]
        self.assertEqual(questions[0].question_text, "New question")

    def test_limit_5_questions(self):
        """Отображаются не более 5 вопросов."""
        for i in range(7):
            Question.objects.create(
                question_text=f"Question {i}",
                pub_date=timezone.now(),
            )
        response = self.client.get(reverse("polls:index"))
        self.assertEqual(len(response.context["latest_questions"]), 5)


class QuestionDetailViewTests(TestCase):
    """Тесты страницы вопроса (detail view)."""

    def setUp(self):
        self.question = Question.objects.create(
            question_text="What's your name?",
            pub_date=timezone.now(),
        )
        self.choice1 = Choice.objects.create(
            choice_text="Alice",
            question=self.question,
            votes=0,
        )
        self.choice2 = Choice.objects.create(
            choice_text="Bob",
            question=self.question,
            votes=0,
        )

    def test_detail_with_valid_question(self):
        """Страница вопроса отображается для существующего вопроса."""
        url = reverse("polls:detail", args=[self.question.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "your name")
        self.assertContains(response, self.choice1.choice_text)
        self.assertContains(response, self.choice2.choice_text)

    def test_detail_404_for_nonexistent_question(self):
        """Возвращает 404 для несуществующего вопроса."""
        url = reverse("polls:detail", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_detail_template_used(self):
        """Используется правильный шаблон."""
        url = reverse("polls:detail", args=[self.question.pk])
        response = self.client.get(url)
        self.assertTemplateUsed(response, "polls/detail.html")


class QuestionResultsViewTests(TestCase):
    """Тесты страницы результатов (results view)."""

    def setUp(self):
        self.question = Question.objects.create(
            question_text="Favorite language?",
            pub_date=timezone.now(),
        )
        Choice.objects.create(
            choice_text="Python",
            question=self.question,
            votes=5,
        )
        Choice.objects.create(
            choice_text="JavaScript",
            question=self.question,
            votes=3,
        )

    def test_results_display(self):
        """Страница результатов отображает голоса."""
        url = reverse("polls:results", args=[self.question.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python")
        self.assertContains(response, "JavaScript")
        self.assertContains(response, "5")
        self.assertContains(response, "3")

    def test_results_404_for_nonexistent_question(self):
        """Возвращает 404 для несуществующего вопроса."""
        url = reverse("polls:results", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_results_template_used(self):
        """Используется правильный шаблон."""
        url = reverse("polls:results", args=[self.question.pk])
        response = self.client.get(url)
        self.assertTemplateUsed(response, "polls/results.html")

    def test_total_votes_context(self):
        """В контексте есть total_votes."""
        url = reverse("polls:results", args=[self.question.pk])
        response = self.client.get(url)
        self.assertEqual(response.context["total_votes"], 8)


class QuestionVoteViewTests(TestCase):
    """Тесты голосования (vote view)."""

    def setUp(self):
        self.question = Question.objects.create(
            question_text="Test question",
            pub_date=timezone.now(),
        )
        self.choice = Choice.objects.create(
            choice_text="Test choice",
            question=self.question,
            votes=0,
        )

    def test_vote_increases_count(self):
        """Голосование увеличивает счётчик."""
        url = reverse("polls:vote", args=[self.question.pk])
        response = self.client.post(url, {"choice": self.choice.pk})
        self.choice.refresh_from_db()
        self.assertEqual(self.choice.votes, 1)

    def test_vote_redirects_to_results(self):
        """После голосования редирект на страницу результатов."""
        url = reverse("polls:vote", args=[self.question.pk])
        response = self.client.post(url, {"choice": self.choice.pk})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("polls:results", args=[self.question.pk]),
        )

    def test_vote_invalid_choice_shows_error(self):
        """Невалидный выбор показывает ошибку."""
        url = reverse("polls:vote", args=[self.question.pk])
        response = self.client.post(url, {"choice": "999"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Вы не выбрали вариант ответа")

    def test_vote_no_choice_shows_error(self):
        """Отсутствие выбора показывает ошибку."""
        url = reverse("polls:vote", args=[self.question.pk])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Вы не выбрали вариант ответа")

    def test_vote_get_method_shows_form(self):
        """GET-запрос к vote показывает форму (не ошибку)."""
        url = reverse("polls:vote", args=[self.question.pk])
        response = self.client.get(url)
        # Django по умолчанию разрешает GET к view без ограничения метода
        self.assertEqual(response.status_code, 200)


class QuestionAdminTests(TestCase):
    """Тесты админ-панели."""

    def setUp(self):
        from django.contrib.auth.models import User

        self.user = User.objects.create_superuser(
            username="admin",
            password="admin123",
            email="admin@test.com",
        )

    def test_admin_login(self):
        """Админ может войти в систему."""
        login_url = reverse("admin:login")
        response = self.client.get(login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "id_username")

    def test_admin_question_list(self):
        """Админ видит список вопросов."""
        self.client.login(username="admin", password="admin123")
        q = Question.objects.create(
            question_text="Admin test",
            pub_date=timezone.now(),
        )
        response = self.client.get(reverse("admin:polls_question_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin test")
