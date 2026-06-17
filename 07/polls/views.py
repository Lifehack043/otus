from django.db import models
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from .models import Choice, Question


def index(request):
    """Главная страница — список последних 5 опубликованных вопросов."""
    latest_questions = Question.objects.filter(
        pub_date__lte=timezone.now()
    ).order_by("-pub_date")[:5]
    context = {"latest_questions": latest_questions}
    return render(request, "polls/index.html", context)


def detail(request, pk):
    """Страница вопроса с вариантами ответов."""
    question = get_object_or_404(Question, pk=pk)
    return render(request, "polls/detail.html", {"question": question})


def results(request, pk):
    """Страница результатов голосования."""
    question = get_object_or_404(Question, pk=pk)
    total_votes = question.choice_set.aggregate(
        total=models.Sum("votes")
    )["total"] or 0
    return render(
        request,
        "polls/results.html",
        {"question": question, "total_votes": total_votes},
    )


def vote(request, pk):
    """Обработка голосования."""
    question = get_object_or_404(Question, pk=pk)
    try:
        selected_choice = question.choice_set.get(pk=request.POST["choice"])
    except (KeyError, Choice.DoesNotExist):
        return render(
            request,
            "polls/detail.html",
            {
                "question": question,
                "error_message": "Вы не выбрали вариант ответа.",
            },
        )
    else:
        selected_choice.votes += 1
        selected_choice.save()
        return HttpResponseRedirect(reverse("polls:results", args=(question.pk,)))
