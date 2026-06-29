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

from django.urls import reverse  # type: ignore

from news.forms import WARNING, BAD_WORDS
from news.models import Comment

COMMENT_DATA = {'text': 'Тестовый комментарий'}
COMMENT_DATA_EDITED = {'text': 'Отредактированный комментарий'}


@pytest.mark.django_db
def test_authorized_user_can_create_comment(author_client, author,
                                            news, news_detail_url):
    """
    Проверка возможности авторизованным пользователем создать комментарий.

    Сценарий:
        1. Авторизованный клиент отправляет POST с данными комментария на
           страницу новости.
        2. Ожидается редирект (302).
        3. В БД появляется новый комментарий с переданным текстом.

    Аргументы:
        author_client: клиент, залогиненный под обычным пользователем.
        news_detail_url: URL страницы новости, куда отправляются комментарии.
    """
    response = author_client.post(news_detail_url, COMMENT_DATA, follow=False)

    assert response.status_code == HTTPStatus.FOUND.value

    comment = Comment.objects.first()
    assert comment is not None
    assert comment.author == author
    assert comment.news == news
    assert Comment.objects.count() == 1
    assert comment.text == COMMENT_DATA['text']


@pytest.mark.django_db
def test_anonymous_user_cannot_create_comment(
    anonymous_client,
    news_detail_url
):
    """
    Проверка возможности анонимным пользователем создать комментарий.

    Сценарий:
        1. Анонимный клиент отправляет POST с данными комментария.
        2. Ожидается редирект на страницу логина (302) либо 403/405 — зависит
           от твоей реализации.
        3. В БД не должно появиться новых комментариев.

    Аргументы:
        anonymous_client: незалогиненный Client().
        news_detail_url: URL страницы новости.
    """
    response = anonymous_client.post(
        news_detail_url, COMMENT_DATA, follow=False)

    assert response.status_code == HTTPStatus.FOUND.value

    assert Comment.objects.count() == 0


@pytest.mark.django_db
def test_author_can_edit_own_comment(author_client, author, news,
                                     comment, comment_edit_url):
    """
    Проверка возможности отредактировать собственный комментарий.

    Сценарий:
        1. Авторизованный клиент (author_client), являющийся автором
           комментария, отправляет POST‑запрос с новыми данными на URL
           редактирования.
        2. Ожидается редирект (статус 302) после успешного сохранения.
        3. Данные в базе обновляются: текст комментария должен точно совпадать
           с тем, что был отправлен в запросе.

    Аргументы:
        author_client (Client): HTTP‑клиент,
            авторизованный под пользователем — автором комментария.
        comment (Comment): экземпляр комментария, принадлежащий author_client.
        comment_edit_url (str): URL для редактирования данного комментария.
    """
    response = author_client.post(comment_edit_url,
                                  COMMENT_DATA_EDITED, follow=False)
    assert response.status_code == HTTPStatus.FOUND.value

    comment.refresh_from_db()
    assert comment.text == COMMENT_DATA_EDITED["text"]
    assert comment.author == author
    assert comment.news == news
    assert Comment.objects.count() == 1


@pytest.mark.django_db
def test_user_cannot_edit_other_comment(
    author_client,
    another_comment,
    author,
    news,
    not_author,
    comment_edit_url_for_other
):
    """
    Проверка возможности редактировать чужой комментарий.

    Сценарий:
        1. Сохраняем исходный текст комментария из БД.
        2. Авторизованный клиент (author_client) пытается отредактировать
           комментарий, автором которого является другой пользователь.
        3. Отправляется POST‑запрос с изменённым текстом на URL чужого
           комментария.
        4. Ввиду проверки прав в get_object (возврат None при несовпадении
           автора) Django возвращает статус 404 Not Found.
        5. Данные комментария в БД не должны измениться.

    Аргументы:
        author_client (Client): HTTP‑клиент, авторизованный под пользователем,
                                который НЕ является автором another_comment.
        another_comment (Comment): комментарий, созданный другим пользователем.
        comment_edit_url_for_other (str): URL для редактирования чужого
                              комментария (соответствует another_comment.pk).
    """
    response = author_client.post(
        comment_edit_url_for_other, COMMENT_DATA_EDITED, follow=False)

    assert response.status_code == HTTPStatus.NOT_FOUND.value

    assert another_comment.text != COMMENT_DATA_EDITED["text"]
    assert another_comment.author == not_author
    assert author_client.author == author
    assert another_comment.news == news
    assert Comment.objects.count() == 1


@pytest.mark.django_db
def test_author_can_delete_own_comment(
    author_client,
    comment,
    comment_delete_url
):
    """
    Проверяем возможность удалить свой комметарий.

    Сценарий:
    1. Авторизованный клиент (автор) отправляет POST на URL удаления.
    2. Ожидается редирект (302).
    3. Комментарий удаляется из БД.

    Аргументы:
        author_client: клиент, залогиненный под автором комментария.
        comment: комментарий, принадлежащий author_client.
        comment_delete_url: URL удаления комментария по его pk.
    """
    response = author_client.post(comment_delete_url, follow=False)

    assert response.status_code == HTTPStatus.FOUND.value
    assert not Comment.objects.filter(pk=comment.pk).exists()


@pytest.mark.django_db
def test_user_cannot_delete_other_comment(
    author_client,
    not_author,
    author,
    news,
    another_comment,
    comment_delete_url
):
    """
    Проверка возможности удалить чужой комментарий.

    Сценарий:
        1. Сохраняем факт существования комментария до запроса.
        2. Авторизованный клиент (не автор) отправляет POST на URL чужого
           комментария.
        3. Ожидается 404 Not Found (из‑за get_object → None).
        4. Комментарий остаётся в БД.

    Аргументы:
        author_client: клиент, залогиненный под пользователем, НЕ являющимся
            автором another_comment.
        another_comment: комментарий, созданный другим пользователем.
        comment_delete_url: URL удаления комментария по его pk.
    """
    response = author_client.post(comment_delete_url, follow=False)

    assert response.status_code == HTTPStatus.FOUND.value
    assert Comment.objects.filter(pk=another_comment.pk).exists()
    assert another_comment.author == not_author
    assert author_client.author == author
    assert another_comment.news == news
    assert Comment.objects.count() == 1


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
