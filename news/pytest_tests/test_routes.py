"""
Тесты маршрутизации веб‑приложения YaNews.

Проверяемые сценарии:
* доступность основных страниц приложения для анонимных пользователей;
* разграничение доступа к операциям редактирования и удаления комментариев
  (только для автора);
* редиректы на страницу логина для неавторизованных пользователей
  при попытке доступа к защищённым страницам.
"""
import pytest
from http import HTTPStatus

from pytest_django.asserts import assertRedirects
from django.urls import reverse  # type: ignore


@pytest.mark.parametrize(
    'name, expected_status',
    (
        ('news:home', HTTPStatus.OK),
        ('users:login', HTTPStatus.OK),
        ('users:signup', HTTPStatus.OK),
    ),
)
@pytest.mark.django_db
def test_home_availability_for_anonymous_user(
    anonymous_client,
    news_urls,
    name,
    expected_status
):
    """Доступность основных страниц приложения для анонимных пользователей."""
    url = news_urls[name]
    response = anonymous_client.get(url)
    assert response.status_code == expected_status.value


@pytest.mark.django_db
def test_news_detail_for_anonymous(anonymous_client, news_detail_url):
    """Доступность страницы отдельной новости для анонимного пользователя."""
    response = anonymous_client.get(news_detail_url)
    assert response.status_code == HTTPStatus.OK.value


@pytest.mark.parametrize(
    'name',
    ('news:edit', 'news:delete'),
)
@pytest.mark.django_db
def test_access_author_for_edit_and_delete_comment(
    author_client,
    name,
    comment_edit_url,
    comment_delete_url
):
    """Проверят возможность редоктирования и удаления комментария автором.

    Тестируемые маршруты:
    * редактирование комментария (news:edit);
    * удаление комментария (news:delete).

    Аргументы:
        author_client (Client): HTTP‑клиент, авторизованный как автор.
        name (str): имя URL‑маршрута для тестирования ('news:edit' или
    'news:delete').
        comment_edit_url (str): полный URL страницы редактирования комментария.
        comment_delete_url (str): полный URL страницы удаления комментария.

    Поведение: клиент выполняет GET‑запрос к маршруту с ID комментария.

    Ожидаемый результат: сервер возвращает статус 200 OK, что означает
    успешное отображение страницы редактирования/удаления
    для автора комментария.
    """
    if name == 'news:edit':
        url = comment_edit_url
    else:
        url = comment_delete_url

    response = author_client.get(url)
    assert response.status_code == HTTPStatus.OK.value


@pytest.mark.parametrize(
    'name',
    ('news:edit', 'news:delete'),
)
@pytest.mark.django_db
def test_access_not_author_for_edit_and_delete_comment_author(
    not_author_client,
    name,
    comment_edit_url,
    comment_delete_url
):
    """Проверят возможность редоктирования и удаления комментария не автором.

    Тестируемые маршруты:
    * редактирование чужого комментария (news:edit);
    * удаление чужого комментария (news:delete).

    Аргументы:
        not_author_client (Client): HTTP‑клиент, авторизованный как
    пользователь, не являющийся автором комментария.
        name (str): имя URL‑маршрута для тестирования ('news:edit' или
    'news:delete').
        comment_edit_url (str): полный URL страницы редактирования комментария.
        comment_delete_url (str): полный URL страницы удаления комментария.

    Поведение: клиент выполняет GET‑запрос к маршруту с ID чужого комментария.

    Ожидаемый результат: сервер возвращает статус 404 Not Found,
    что означает отсутствие доступа к чужим комментариям.
    """
    if name == 'news:edit':
        url = comment_edit_url
    else:
        url = comment_delete_url

    response = not_author_client.get(url)
    assert response.status_code == HTTPStatus.NOT_FOUND.value


@pytest.mark.parametrize(
    'name',
    ('news:edit', 'news:delete'),
)
@pytest.mark.django_db
def test_access_anonymous_client_for_edit_and_delete_comment_author(
    anonymous_client,
    name,
    comment_edit_url,
    comment_delete_url
):
    """Проверяет редирект анонимного пользователя на страницу авторизации.

    Тестируемые сценарии:
    * попытка редактирования комментария без авторизации (news:edit);
    * попытка удаления комментария без авторизации (news:delete).

    Аргументы:
        anonymous_client (Client): анонимный HTTP‑клиент (не авторизован).
        name (str): имя URL‑маршрута для теста ('news:edit' или 'news:delete').
        comment_edit_url (str): полный URL страницы редактирования комментария.
        comment_delete_url (str): полный URL страницы удаления комментария.

    Поведение:
        Клиент выполняет GET‑запрос к защищённому маршруту с ID комментария.


    Ожидаемый результат:
    * сервер возвращает статус 302 Found (редирект);
    * заголовок Location содержит URL страницы логина с параметром next,
    указывающим на исходный маршрут;
    * пользователь перенаправляется на страницу авторизации с возможностью
    вернуться к исходному действию после входа.
    """
    if name == 'news:edit':
        url = comment_edit_url
    else:
        url = comment_delete_url

    response = anonymous_client.get(url)
    login_url = reverse('users:login')
    expected_url = f'{login_url}?next={url}'
    assert response.status_code == HTTPStatus.FOUND.value
    assertRedirects(response, expected_url)
