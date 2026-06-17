from django.db import models
from django.urls import reverse
from django.utils import timezone


class Question(models.Model):
    """Вопрос опроса."""
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField("date published")

    class Meta:
        ordering = ["-pub_date"]
        indexes = [
            models.Index(fields=["-pub_date"]),
        ]

    def __str__(self):
        return self.question_text

    def get_absolute_url(self):
        """Возвращает URL для просмотра результатов вопроса."""
        return reverse("polls:detail", kwargs={"pk": self.pk})

    def was_published_recently(self):
        """Проверяет, был ли вопрос опубликован недавно (за последние 1 день)."""
        now = timezone.now()
        return now - timezone.timedelta(days=1) <= self.pub_date <= now


class Choice(models.Model):
    """Вариант ответа на вопрос опроса."""
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["question", "choice_text"], name="unique_choice")
        ]

    def __str__(self):
        return self.choice_text
