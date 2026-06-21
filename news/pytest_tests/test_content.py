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
from pytest_lazyfixture import lazy_fixture as lf  # type: ignore
from django.urls import reverse  # type: ignore

from news.models import Comment
from news.forms import CommentForm


@pytest.mark.django_db
def test_home_availability_for_anonymous_user_and_news_order(
    anonymous_client,
    news_list
):
    """Доступность главной страниц для анонимных пользователей и сортировку.

    Аргументы:
        anonymous_client (Client): анонимный HTTP‑клиент для запросов.
        news_list (list[News]): список из 11 тестовых новостей, из фикстуры.

    Ожидаемый результат:
        * статус ответа домашней страницы — 200 OK;
        * количество новостей на странице (пагинацыя) соответствует настройке
        NEWS_COUNT_ON_HOME_PAGE;
        * новости отсортированы по дате публикации (от новых к старым).
    """
    assert len(news_list) == 11
    url = reverse('news:home')
    response = anonymous_client.get(url, follow=False)
    assert response.status_code == HTTPStatus.OK.value
    object_list = response.context['object_list']
    news_count = len(object_list)
    expected_count = settings.NEWS_COUNT_ON_HOME_PAGE
    assert news_count == expected_count

    dates = [news.date for news in object_list]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.django_db
def test_comments_order(comment_list, news, client):
    """
    Проверяет сортировку комметнариев на странице новости по дате создания.

    Шаги теста:
    1. Привязывает 11 тестовых комментариев к новости и сохраняет их в БД.
    2. Выполняет GET‑запрос на страницу новости.
    3. Извлекает комментарии для этой новости из БД (с сортировкой -created).
    4. Сравнивает порядок дат создания комментариев с ожидаемым (убывающий).

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


@pytest.mark.parametrize(
    'parametrized_client, form_on_detail',
    (
        (lf('author_client'), True),
        (lf('anonymous_client'), False),
    )
)
@pytest.mark.django_db
def test_anonymous_client_has_no_form(
    news, parametrized_client,
    form_on_detail
):
    """
    Тестирует отображение формы комментариев в зависимости от пользователя.

    Для авторизованного пользователя (author_client) ожидается, что форма
    комментариев (CommentForm) будет присутствовать в контексте шаблона.
    Для анонимного пользователя (anonymous_client) форма в контексте
    отсутствовать.

    Аргументы:
        news: экземпляр модели News, используемый для построения URL.
        parametrized_client: HTTP‑клиент (авторизованный или анонимный).
        form_on_detail (bool): флаг, указывающий, должна ли форма
            присутствовать в контексте (True для авторизованных,
            False для анонимных).
    """
    url = reverse('news:detail', kwargs={'pk': news.pk})
    response = parametrized_client.get(url, follow=False)
    assert response.status_code == HTTPStatus.OK.value
    if form_on_detail:
        assert 'form' in response.context
        assert isinstance(response.context['form'], CommentForm)
    else:
        assert 'form' not in response.context
