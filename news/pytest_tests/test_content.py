"""
Тесты для проверки контента веб‑приложения YaNews.

Проверяемые сценарии:
* отображение и сортировка новостей отсвежей к самой старой на главной
странице, не более 10 новостей на странице;
* отображение и сортировка комментариев на странице новости, от старых к новым;
* наличие формы для комментариев для авторизованных пользователей и
отсутствие формы для анонимных пользователей.
"""
import pytest
from http import HTTPStatus

from django.conf import settings  # type: ignore
from django.urls import reverse  # type: ignore

from news.models import Comment
from news.forms import CommentForm


@pytest.mark.django_db
def test_home_availability_for_anonymous_user_and_news_order(
    anonymous_client,
    news_urls,
    news_list  # нужен только чтобы создать 11 новостей в БД
):
    """Доступность главной страниц для анонимных пользователей и сортировку.

    Аргументы:
        anonymous_client (Client): анонимный HTTP‑клиент для запросов.

    Ожидаемый результат:
        * статус ответа домашней страницы — 200 OK;
        * количество новостей на странице (пагинацыя) соответствует настройке
        NEWS_COUNT_ON_HOME_PAGE;
        * новости отсортированы по дате публикации (от новых к старым).
    """
    url = news_urls['news:home']
    response = anonymous_client.get(url, follow=False)
    assert response.status_code == HTTPStatus.OK.value
    object_list = response.context['object_list']
    news_count = object_list.count()
    assert news_count == settings.NEWS_COUNT_ON_HOME_PAGE

    dates = [news.date for news in object_list]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.django_db
def test_comments_order(comment_list, news, client):
    """
    Проверяет сортировку комметнариев на странице новости по дате создания.

    Аргументы:
        comment_list (list[Comment]): 11 комментариев с убывающими датами
            создания (комментарий №1 — сегодня, №2 — вчера и т. д.).
        news (News): тестовая новость, к которой привязываются комментарии.
        client (Client): анонимный HTTP‑клиент для выполнения запроса.

    Ожидаемые результаты:
    * статус ответа сервера — 200 OK;
    * в БД ровно 11 комментариев для этой новости;
    * порядок дат создания в БД совпадает с отсортированным по убыванию списком
    дат из comment_list.
    """
    url = reverse('news:detail', kwargs={'pk': news.pk})
    response = client.get(url, follow=False)
    assert response.status_code == HTTPStatus.OK.value
    db_comments = Comment.objects.filter(news=news).order_by('-created')
    all_timestamps = [comment.created for comment in db_comments]
    assert all_timestamps == sorted(
        [comment.created for comment in comment_list],
        reverse=True
    )


@pytest.mark.django_db
def test_author_client_sees_comment_form(author_client, news):
    """
    Проверяется наличие формы комментария для авторизованного пользователя.

    Аргументы:
        author_client (Client): HTTP‑клиент, авторизованный под
            пользователем‑автором.
        news (News): экземпляр модели новости, для которой проверяется
            отображение формы.

    Ожидаемый результат:
        * статус ответа страницы — 200 OK;
        * в response.context присутствует ключ 'form';
        * объект по ключу 'form' является экземпляром класса CommentForm.
    """
    url = reverse('news:detail', kwargs={'pk': news.pk})
    response = author_client.get(url, follow=False)

    assert response.status_code == HTTPStatus.OK.value
    assert 'form' in response.context
    assert isinstance(response.context['form'], CommentForm)


@pytest.mark.django_db
def test_anonymous_client_does_not_see_comment_form(anonymous_client, news):
    """
    Проверяется наличие формы комментария для анонимного пользователя.

    Аргументы:
        anonymous_client (Client): анонимный HTTP‑клиент (не авторизован).
        news (News): экземпляр модели новости, для которой проверяется
            отсутствие формы.

    Ожидаемый результат:
        * статус ответа страницы — 200 OK;
        * в response.context отсутствует ключ 'form'.
    """
    url = reverse('news:detail', kwargs={'pk': news.pk})
    response = anonymous_client.get(url, follow=False)

    assert response.status_code == HTTPStatus.OK.value
    assert 'form' not in response.context
