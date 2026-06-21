# news/tests/test_content.py
"""
Тесты для проверки контента веб‑приложения YaNews.

Проверяемые сценарии:
* отображение и сортировка новостей отсвежей к самой старой на главной
странице, не более 10 новостей на странице;
* отображение и сортировка комментариев на странице новости, от старых к новым;
* наличие формы для комментариев для авторизованных пользователей и
отсутствие формы для анонимных пользователей.
"""

from django.conf import settings  # type: ignore
from django.test import TestCase  # type: ignore
# Импортируем функцию reverse(), она понадобится для получения адреса страницы.
from django.urls import reverse  # type: ignore
# Импортируйте нужные классы.
from datetime import datetime, timedelta
# Импортируем функцию для получения модели пользователя.
from django.contrib.auth import get_user_model  # type: ignore
# Допишите новый импорт.
from django.utils import timezone  # type: ignore


# Импортируем класс формы.
from news.forms import CommentForm
from news.models import News, Comment

User = get_user_model()


class TestHomePage(TestCase):
    """
    Набор тестов для проверки отображения новостей на главной странице.

    Проверяет:
    * количество отображаемых новостей, не более 10;
    * правильную сортировку новостей (по убыванию).
    """

    # Вынесем ссылку на домашнюю страницу в атрибуты класса.
    HOME_URL = reverse('news:home')

    @classmethod
    def setUpTestData(cls):
        """
        Подготовка тестовых данных для всех тестов класса.

        Создаёт набор новостей с датами, отстоящими друг от друга на один день,
        чтобы проверить сортировку и ограничение количества.
        Количество новостей на 1 больше, чем лимит на странице.
        """
        # Вычисляем текущую дату.
        today = datetime.today()
        News.objects.bulk_create(
            News(
                title=f'Новость {index}',
                text='Просто текст.',
                # Для каждой новости уменьшаем дату на index дней от today,
                # где index - счётчик цикла.
                date=today - timedelta(days=index)
            )
            for index in range(settings.NEWS_COUNT_ON_HOME_PAGE + 1)
        )

    def test_news_count(self):
        """
        Тест количества новостей на главной странице.

        Проверяет, что на главной странице отображается ровно
        `NEWS_COUNT_ON_HOME_PAGE` новостей (настройка из settings).

        Шаги:
        1. Запрашивает главную страницу.
        2. Получает список новостей из контекста.
        3. Сравнивает количество с ожидаемым значением.
        """
        # Загружаем главную страницу.
        response = self.client.get(self.HOME_URL)
        # Код ответа не проверяем, его уже проверили в тестах маршрутов.
        # Получаем список объектов из словаря контекста.
        object_list = response.context['object_list']
        # Определяем количество записей в списке.
        news_count = object_list.count()
        # Проверяем, что на странице именно 10 новостей.
        self.assertEqual(news_count, settings.NEWS_COUNT_ON_HOME_PAGE)

    def test_news_order(self):
        """
        Тест сортировки новостей на главной странице.

        Проверяет, что новости отображаются в порядке убывания даты
        (самые свежие — первыми).

        Шаги:
        1. Запрашивает главную страницу.
        2. Извлекает даты всех новостей из списка.
        3. Сортирует даты по убыванию.
        4. Сравнивает исходный порядок с отсортированным.
        """
        response = self.client.get(self.HOME_URL)
        object_list = response.context['object_list']
        # Получаем даты новостей в том порядке, как они выведены на странице.
        all_dates = [news.date for news in object_list]
        # Сортируем полученный список по убыванию.
        sorted_dates = sorted(all_dates, reverse=True)
        # Проверяем, что исходный список был отсортирован правильно.
        self.assertEqual(all_dates, sorted_dates)


class TestDetailPage(TestCase):
    """
    Набор тестов для проверки страницы отдельной новости.

    Проверяет:
    * сортировку комментариев (по возрастанию даты создания);
    * наличие формы для комментариев у авторизованного пользователя;
    * отсутствие формы у анонимного пользователя.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Подготовка тестовых данных для всех тестов класса.

        Создаёт:
        * одну тестовую новость;
        * пользователя‑автора комментариев;
        * 10 комментариев к новости с последовательными датами создания.

        Сохраняет URL страницы новости и пользователя в атрибуты класса.
        """
        cls.news = News.objects.create(
            title='Тестовая новость', text='Просто текст.'
        )
        # Сохраняем в переменную адрес страницы с новостью:
        cls.detail_url = reverse('news:detail', args=(cls.news.id,))
        cls.author = User.objects.create(username='Комментатор')
        # Запоминаем текущее время:
        # now = datetime.now()
        # Получите текущее время при помощи утилиты timezone.
        now = timezone.now()
        # Создаём комментарии в цикле.
        for index in range(10):
            # Создаём объект и записываем его в переменную.
            comment = Comment.objects.create(
                news=cls.news, author=cls.author, text=f'Tекст {index}',
            )
            # Сразу после создания меняем время создания комментария.
            comment.created = now + timedelta(days=index)
            # И сохраняем эти изменения.
            comment.save()

    def test_comments_order(self):
        """
        Тест сортировки комментариев на странице новости.

        Проверяет, что комментарии отображаются в хронологическом порядке
        (от старых к новым).

        Шаги:
        1. Запрашивает страницу новости.
        2. Проверяет наличие новости в контексте.
        3. Извлекает все комментарии к новости.
        4. Собирает временные метки комментариев.
        5. Сравнивает порядок с отсортированным по возрастанию.
        """
        response = self.client.get(self.detail_url)
        # Проверяем, что объект новости находится в словаре контекста
        # под ожидаемым именем - названием модели.
        self.assertIn('news', response.context)
        # Получаем объект новости.
        news = response.context['news']
        # Получаем все комментарии к новости.
        all_comments = news.comment_set.all()
        # Собираем временные метки всех комментариев.
        all_timestamps = [comment.created for comment in all_comments]
        # Сортируем временные метки, менять порядок сортировки не надо.
        sorted_timestamps = sorted(all_timestamps)
        # Проверяем, что временные метки отсортированы правильно.
        self.assertEqual(all_timestamps, sorted_timestamps)

    def test_anonymous_client_has_no_form(self):
        """
        Тест отсутствия формы комментариев для анонимного пользователя.

        Проверяет, что анонимный клиент не видит форму для добавления
        комментариев на странице новости.

        Шаги:
        1. Запрашивает страницу новости без авторизации.
        2. Убеждается, что ключ 'form' отсутствует в контексте ответа.
        """
        response = self.client.get(self.detail_url)
        self.assertNotIn('form', response.context)

    def test_authorized_client_has_form(self):
        """
        Тест наличия формы комментариев для авторизованного пользователя.

        Проверяет, что авторизованный пользователь видит форму для комментариев
        и что форма относится к классу CommentForm.

        Шаги:
        1. Авторизует клиента под тестовым пользователем.
        2. Запрашивает страницу новости.
        3. Проверяет наличие ключа 'form' в контексте.
        4. Убеждается, что объект формы — экземпляр CommentForm.
        """
        # Авторизуем клиент при помощи ранее созданного пользователя.
        self.client.force_login(self.author)
        response = self.client.get(self.detail_url)
        self.assertIn('form', response.context)
        # Проверим, что объект формы соответствует нужному классу формы.
        self.assertIsInstance(response.context['form'], CommentForm)
