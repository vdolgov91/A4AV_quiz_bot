import datetime

import quizAggregator

import pytest
from unittest.mock import patch

class TestCreateInfoByCity:
    '''Класс для тестирования функции quizAggregator.createInfoByCity'''
    def test_with_None_input(self):
        '''Проверяет createInfoByCity если отдать на вход функции None'''
        expected = ([], [], [])
        result = quizAggregator.createInfoByCity(None)
        assert expected == result


    mockCityDict = {
        'Новосибирск': {
            'bars': ['Три лося', 'Mishkin&Mishkin', 'Арт П.А.Б.', 'Максимилианс', 'Типография', 'Руки ВВерх!'],
            'qp': 'nsk',
            'li': 'novosibirsk',
            'mama': 'nsk',
            'wow': 'nsk',
            'local_organizators': []
        },
    }

    @patch.dict(quizAggregator.cityDict, mockCityDict)
    def test_with_existing_city(self):
        '''Проверяет createInfoByCity если отдать на вход функции существующий моковый город'''
        expectedBars = ['Оставить все бары', 'Три лося', 'Mishkin&Mishkin', 'Арт П.А.Б.', 'Максимилианс', 'Типография', 'Руки ВВерх!']
        expectedOrganizators = ['Оставить всех организаторов', 'Квиз Плиз', 'Лига Индиго', 'Мама Квиз', 'WOW Quiz/ Эйнштейн Party']
        expectedLinks =  ['placeholder', 'https://nsk.quizplease.ru/schedule', 'https://ligaindigo.ru/novosibirsk', 'https://nsk.mamaquiz.ru/', 'https://nsk.wowquiz.ru/schedule']
        cityBars, cityOrganizators, cityLinks = quizAggregator.createInfoByCity('Новосибирск')
        assert expectedBars == cityBars
        assert expectedOrganizators == cityOrganizators
        assert expectedLinks == cityLinks


class TestAssignThemesToQuiz:
    '''Класс для тестирования функции quizAggregator.assignThemesToQuiz'''
    def test_tag_with_None_input(self):
        '''Проверяет передачу некорректных параметров на вход assignThemesToQuiz()'''
        tags = quizAggregator.assignThemesToQuiz(None, None)
        print(tags)
        # TODO: доделать когда в функции будет обработка ошибки


    @pytest.mark.parametrize('gamename', ['Игра №1 Сезон №1', 'Игра №222 Сезон №11', 'игра №3   сезона №5  '])
    def test_tag_is_classic_liga_indigo(self, gamename):
        '''Проверяет присвоение корректного тэга для названий игр Лиги Индиго'''
        tags = quizAggregator.assignThemesToQuiz(gamename, 'Лига Индиго')
        assert 'Классика' in tags


    classicGames = ['Квиз, плиз! NSK #569', 'Угадайка обо всём #44 ( С туром к Новому году)', 'Обо всём #46 Новогодняя',
    'КЛАССИКА #128', 'Квиз, плиз! [железные яйца] NSK #5', '[новички] NSK #459', 'FUN #84', 'Эйнштейн Party #85',
    'Блиц №1']

    @pytest.mark.parametrize('gamename', classicGames)
    def test_tag_is_classic(self, gamename):
        '''Проверяет присвоение тэга Классика для различных форматов названия игры'''
        tags = quizAggregator.assignThemesToQuiz(gamename, '')
        assert 'Классика' in tags

    notClassicGames = ['Угадай мелодию #64', 'КИНОМЬЮЗИК: НОВОГОДНИЙ #2', 'ЛОГИКА ГДЕ? #14', '[кино и музыка] NSK #93',
    'Топ кинопоиска #7', 'СССР vs 90ые!', 'Черный квиз 18+ #2', 'Гарри Поттер #20 Лайт', '18+ #16 За гранью приличия',
    'Угадай футбол #4', 'Аниме #3']

    @pytest.mark.parametrize('gamename', notClassicGames)
    def test_tag_is_not_classic(self, gamename):
        '''Проверяет что тэг Классика не присваивается тем играм, которым не должен'''
        tags = quizAggregator.assignThemesToQuiz(gamename, '')
        assert 'Классика' not in tags


    multimediaGames = ['Угадай мелодию #64 Новогодняя дискотека. Только припевы.', 'КИНОМЬЮЗИК: НОВОГОДНИЙ #2.',
    '[кино и музыка] NSK #93', '[литература] NSK #3', '[music party] кринж эдишн NSK #1', 'Топ кинопоиска #7',
    'Топ 250 Кинопоиска #8', 'Угадай мультфильм #10 Союзмультфильм vs Disney', 'Угадай кино #24 Туры по жанрам', 'Друзья #9',
    'Гарри Поттер #20 Лайт', 'Сумерки #2', 'Кино и музыка СССР #6', 'Угадай футбол #4', 'Властелин колец №5', 'Клиника #3'
    'Угадай сериал #8 Netflix VS HBO', 'Аниме #3', 'Шазам №1', 'indigo show номер 5', 'Компьютерные игры #1',
    'Marvel против DC #1', 'Спорт №3', 'Игра престолов #15']

    @pytest.mark.parametrize('gamename', multimediaGames)
    def test_tag_is_multimedia(self, gamename):
        '''Проверяет присвоение тэга Мультимедиа для различных форматов названия игры'''
        tags = quizAggregator.assignThemesToQuiz(gamename, '')
        assert 'Мультимедиа' in tags


    notMultimediaGames = ['Новый год СССР', 'Квиз, плиз! NSK #569', 'Угадайка обо всём #44', 'КЛАССИКА #128',
    '[новички] NSK #461', 'СССР vs 90ые!', 'Черный квиз 18+ #2', 'FUN #84', 'Эйнштейн Party #87']

    @pytest.mark.parametrize('gamename', notMultimediaGames)
    def test_tag_is_not_multimedia(self, gamename):
        '''Проверяет что тэг Мультимедиа не присваивается тем играм, которым не должен'''
        tags = quizAggregator.assignThemesToQuiz(gamename, '')
        assert 'Мультимедиа' not in tags


    rookieGames = ['[новички] NSK #461']
    @pytest.mark.parametrize('gamename', rookieGames)
    def test_tag_is_rookie(self, gamename):
        '''Проверяет присвоение тэга Новички для различных форматов названия игры'''
        tags = quizAggregator.assignThemesToQuiz(gamename, '')
        assert 'Новички' in tags


    nostalgiaGames = ['Новый год СССР', 'СССР vs 90ые!', 'Кино и музыка СССР #6', 'Угадай мелодию Дискотека 80-х', '00-е vs 90-е']
    @pytest.mark.parametrize('gamename', nostalgiaGames)
    def test_tag_is_nostalgia(self, gamename):
        '''Проверяет присвоение тэга Ностальгия для различных форматов названия игры'''
        tags = quizAggregator.assignThemesToQuiz(gamename, '')
        assert 'Ностальгия' in tags


    nsfwGames = ['Черный квиз 18+ #2', '18+ #16 За гранью приличия', 'Черный квиз #13', 'Чёрный квиз №666']
    @pytest.mark.parametrize('gamename', nsfwGames)
    def test_tag_is_nsfw(self, gamename):
        '''Проверяет присвоение тэга 18+ для различных форматов названия игры'''
        tags = quizAggregator.assignThemesToQuiz(gamename, '')
        assert '18+' in tags


class TestCollectQuizData:
    '''Класс для тестирования функции quizAggregator.collectQuizData'''

    def test_mock_nonexistent_org(self):
        '''Передаем на вход функции collectQuizData несуществующего организатора'''
        cityOrganizators = ['Оставить всех организаторов', 'Тестовый организатор']
        cityLinks = ['placeholder', 'https://test.local']
        expectedGames, expectedOrganizatorErrors = {}, {}
        games, organizatorErrors = quizAggregator.collectQuizData(cityOrganizators, cityLinks)
        assert games == expectedGames
        assert organizatorErrors == expectedOrganizatorErrors


    def test_mock_intented_org_error(self):
        '''Передаем на вход функции намеренно некорректную информацию по реальному организатору
        и проверяем, что получили organizatorError'''
        cityOrganizators = ['Оставить всех организаторов', 'Квиз Плиз']
        cityLinks = ['placeholder', 'wrongtesturl']
        games, organizatorErrors = quizAggregator.collectQuizData(cityOrganizators, cityLinks)
        assert len(organizatorErrors) > 0


    def test_mock_number_of_games(self, quiz_from_local_files):
        '''Проверяем количество извлеченных квизов с локальных копий веб-страниц из папки /tests/saved_web_pages
        ligaindigo_schedule_2023-12-14.html - 1
        mamaquiz_schedule_2023-12-14.html - 5 (одна 13 декабря, поэтому дату задаем 13.12)
        quizplease_schedule_2023-12-14.html - 3 (остальные резерв и должны быть отброшены)
        wowquiz_schedule_2023-12-20.html - 6 (остальные резерв и должны быть отброшены)
        '''
        expected = 1 + 5 + 3 + 6
        localQuizes = quiz_from_local_files[0]
        assert len(localQuizes) == expected

    @pytest.mark.parametrize('gameParam', ['game', 'date', 'bar', 'tag'])
    def test_mock_game_params(self, quiz_from_local_files, expected_games, gameParam):
        '''Проверяем что названия игр извлеклись правильно, сравнивая с эталонными значениями'''
        expectedGameParams = [value[gameParam] for key, value in expected_games.items()]
        returnedGameParams = [value[gameParam] for key, value in quiz_from_local_files[0].items()]
        assert returnedGameParams == expectedGameParams


    def test_real_games_collected_some_games(self, quiz_from_real_web_sites):
        '''Делаем запрос на реальные сайты организаторов и проверяем что список игр вернулся ненулевым'''
        # print(f'\nreal games:\n{quiz_from_real_web_sites[0]}')
        assert len(quiz_from_real_web_sites[0]) > 0


    def test_real_games_no_organizator_errors(self, quiz_from_real_web_sites):
        '''Делаем запрос на реальные сайты организаторов и проверяем что ни по одному из организаторов нет ошибок'''
        #print(f'\nreal organizatorErrors:\n{quiz_from_real_web_sites[1]}')
        assert len(quiz_from_real_web_sites[1]) == 0