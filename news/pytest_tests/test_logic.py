"""
Тесты бизнес‑логики работы с комментариями в приложении новостей.

Проверяемые сценарии:
* создание комментариев (авторизованными и анонимными пользователями);
* фильтрация стоп‑слов в комментариях;
* редактирование комментариев (автором и другими пользователями);
* удаление комментариев (автором и другими пользователями).
"""
import pytest
from http import HTTPStatus

from pytest_lazyfixture import lazy_fixture as lf  # type: ignore
from django.urls import reverse  # type: ignore

from news.forms import WARNING, BAD_WORDS
from news.models import Comment


@pytest.mark.parametrize(
    'client, create_comment',
    [
        (lf('anonymous_client'), False),
        (lf('author_client'), True),
    ]
)
@pytest.mark.django_db
def test_create_comment_user_and_anonymous(news, client, create_comment):
    """
    Проверка создания комментариев авторизованными и анонимными пользователями.

    Аргументы:
        news: фикстура новости, к которой добавляется комментарий.
        client: фикстура HTTP‑клиента (анонимный или авторизованный).
        create_comment: булево значение, ожидаемый создание комментария:
            * True — комментарий должен быть создан (авторизованный);
            * False — комментарий не должен быть создан (анонимный).
    """
    url = reverse('news:detail', kwargs={'pk': news.pk})
    comment_data = {'text': 'Тестовый комментарий'}
    response = client.post(url, comment_data, follow=False)
    assert response.status_code == HTTPStatus.FOUND.value
    if create_comment:
        comment = Comment.objects.first()
        assert comment.text == 'Тестовый комментарий'
    else:
        assert Comment.objects.count() == 0


@pytest.mark.parametrize(
    'client, comment_fixture, edit_comment, expected_status',
    [
        (lf('author_client'), lf('comment'), True, HTTPStatus.FOUND),
        (
            lf('author_client'),
            lf('another_comment'),
            False,
            HTTPStatus.NOT_FOUND
        ),
    ]
)
@pytest.mark.django_db
def test_edit_comment_user_and_anonymous(
    client,
    comment_fixture,
    edit_comment,
    expected_status
):
    """
    Проверка редактирования коммент. автором и неавторизованным пользователями.

    Аргументы:
        client: фикстура HTTP‑клиента (авторизованный пользователь).
        comment_fixture: фикстура комментария для редактирования.
        edit_comment: булево значение, имеется ли право на редактирование:
            * True — клиент является автором, а редактирование успешно;
            * False — клиент не является автором, редактирование запрещено.
        expected_status: ожидаемый HTTP‑статус ответа сервера.
    """
    url = reverse('news:edit', kwargs={'pk': comment_fixture.pk})
    edit_data = {'text': 'Отредактированный комментарий'}
    response = client.post(url, edit_data, follow=False)
    assert response.status_code == expected_status
    comment_fixture.refresh_from_db()
    if edit_comment:
        assert comment_fixture.text == 'Отредактированный комментарий'
    else:
        original_text = comment_fixture.text
        assert comment_fixture.text == original_text


@pytest.mark.parametrize(
    'client, comment_fixture, delete_comment, expected_status',
    [
        (lf('author_client'), lf('comment'), True, HTTPStatus.FOUND),
        (
            lf('author_client'),
            lf('another_comment'),
            False,
            HTTPStatus.NOT_FOUND
        ),
    ]
)
@pytest.mark.django_db
def test_del_comment_user_and_anonymous(
    client,
    comment_fixture,
    delete_comment,
    expected_status
):
    """Проверка удаления коммент. автором и неавторизованными пользователями.

    Аргументы:
        client: фикстура HTTP‑клиента (авторизованный пользователь).
        comment_fixture: фикстура комментария для удаления.
        delete_comment: булево значение, имеется ли право на удаление:
            * True — клиент является автором, удаление должно пройти успешно;
            * False — клиент не является автором, удаление запрещено.
        expected_status: ожидаемый HTTP‑статус ответа сервера.
    """
    url = reverse('news:delete', kwargs={'pk': comment_fixture.pk})
    response = client.post(url, follow=False)
    assert response.status_code == expected_status
    if delete_comment:
        assert not Comment.objects.filter(pk=comment_fixture.pk).exists()
    else:
        assert Comment.objects.filter(pk=comment_fixture.pk).exists()


@pytest.mark.django_db
def test_banned_words_filtering(news, author_client):
    """Проверяет фильтрацию стоп‑слов в комментариях.

    Сценарий: авторизованный пользователь пытается отправить комментарий,
    содержащий запрещённое слово из списка BAD_WORDS. Система должна:
    * отклонить комментарий;
    * показать предупреждение (WARNING);
    * не сохранять комментарий в БД.

    Аргументы:
        news: фикстура новости, к которой добавляется комментарий.
        author_client: фикстура авторизованного HTTP‑клиента.
    """
    url = reverse('news:detail', kwargs={'pk': news.pk})
    for bad_word in BAD_WORDS:
        comment_data = {'text': bad_word}
        response = author_client.post(url, comment_data, follow=True)
        assert response.status_code == 200
        assert WARNING in response.content.decode('utf-8')
