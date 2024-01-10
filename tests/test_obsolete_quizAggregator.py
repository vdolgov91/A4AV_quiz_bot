import quizAggregator

import datetime
import pytest
from unittest.mock import patch


class TestCreateInfoByCity:
    '''Класс для тестирования функции quizAggregator.create_info_by_city'''
    def test_with_None_input(self):
        '''Проверяет create_info_by_city если отдать на вход функции None'''
        expected = ([], [], [])
        result = quizAggregator.create_info_by_city(None)
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

    @patch.dict(quizAggregator.CITY_DICT, mockCityDict)
    def test_with_existing_city(self):
        '''Проверяет create_info_by_city если отдать на вход функции существующий моковый город'''
        expectedBars = ['Оставить все бары', 'Три лося', 'Mishkin&Mishkin', 'Арт П.А.Б.', 'Максимилианс', 'Типография', 'Руки ВВерх!']
        expectedOrganizators = ['Оставить всех организаторов', 'Квиз Плиз', 'Лига Индиго', 'Мама Квиз', 'WOW Quiz/ Эйнштейн Party']
        expectedLinks =  ['placeholder', 'https://nsk.quizplease.ru/schedule', 'https://ligaindigo.ru/novosibirsk', 'https://nsk.mamaquiz.ru/', 'https://nsk.wowquiz.ru/schedule']
        cityBars, cityOrganizators, cityLinks = quizAggregator.create_info_by_city('Новосибирск')
        assert expectedBars == cityBars
        assert expectedOrganizators == cityOrganizators
        assert expectedLinks == cityLinks


    mockCityDict = {
        'Новосибирск': {
            'bars': ['Три лося', 'Mishkin&Mishkin', 'Арт П.А.Б.', 'Максимилианс', 'Типография', 'Руки ВВерх!'],
            'li': 'novosibirsk',
            'mama': 'nsk',
            'wow': 'nsk',
            'local_organizators': []
        },
    }

    @patch.dict(quizAggregator.CITY_DICT, mockCityDict)
    def test_with_existing_city_with_missing_org(self):
        '''Проверяет create_info_by_city если отдать на вход функции существующий моковый город в котором отсутствует
        один из организаторов из списка ORGANIZATORS_DICT (Квиз Плиз)'''
        expectedBars = ['Оставить все бары', 'Три лося', 'Mishkin&Mishkin', 'Арт П.А.Б.', 'Максимилианс', 'Типография',
                        'Руки ВВерх!']
        expectedOrganizators = ['Оставить всех организаторов', 'Лига Индиго', 'Мама Квиз',
                                'WOW Quiz/ Эйнштейн Party']
        expectedLinks = ['placeholder', 'https://ligaindigo.ru/novosibirsk',
                         'https://nsk.mamaquiz.ru/', 'https://nsk.wowquiz.ru/schedule']
        cityBars, cityOrganizators, cityLinks = quizAggregator.create_info_by_city('Новосибирск')
        assert expectedBars == cityBars
        assert expectedOrganizators == cityOrganizators
        assert expectedLinks == cityLinks


class TestAssignThemesToQuiz:
    '''Класс для тестирования функции quizAggregator.assign_themes_to_quiz'''
    def test_tag_with_None_input(self):
        '''Проверяет передачу некорректных параметров на вход assign_themes_to_quiz()'''
        tags = quizAggregator.assign_themes_to_quiz(None, None)
        assert tags is None


    @pytest.mark.parametrize('gamename', ['Игра №1 Сезон №1', 'Игра №222 Сезон №11', 'игра №3   сезона №5  '])
    def test_tag_is_classic_liga_indigo(self, gamename):
        '''Проверяет присвоение корректного тэга для названий игр Лиги Индиго'''
        tags = quizAggregator.assign_themes_to_quiz(gamename, 'Лига Индиго')
        assert 'Классика' in tags


    classicGames = ['Квиз, плиз! NSK #569', 'Угадайка обо всём #44 ( С туром к Новому году)', 'Обо всём #46 Новогодняя',
    'КЛАССИКА #128', 'Квиз, плиз! [железные яйца] NSK #5', '[новички] NSK #459', 'FUN #84', 'Эйнштейн Party #85',
    'Блиц №1']

    @pytest.mark.parametrize('gamename', classicGames)
    def test_tag_is_classic(self, gamename):
        '''Проверяет присвоение тэга Классика для различных форматов названия игры'''
        tags = quizAggregator.assign_themes_to_quiz(gamename, '')
        assert 'Классика' in tags

    notClassicGames = ['Угадай мелодию #64', 'КИНОМЬЮЗИК: НОВОГОДНИЙ #2', 'ЛОГИКА ГДЕ? #14', '[кино и музыка] NSK #93',
    'Топ кинопоиска #7', 'СССР vs 90ые!', 'Черный квиз 18+ #2', 'Гарри Поттер #20 Лайт', '18+ #16 За гранью приличия',
    'Угадай футбол #4', 'Аниме #3']

    @pytest.mark.parametrize('gamename', notClassicGames)
    def test_tag_is_not_classic(self, gamename):
        '''Проверяет что тэг Классика не присваивается тем играм, которым не должен'''
        tags = quizAggregator.assign_themes_to_quiz(gamename, '')
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
        tags = quizAggregator.assign_themes_to_quiz(gamename, '')
        assert 'Мультимедиа' in tags


    notMultimediaGames = ['Новый год СССР', 'Квиз, плиз! NSK #569', 'Угадайка обо всём #44', 'КЛАССИКА #128',
    '[новички] NSK #461', 'СССР vs 90ые!', 'Черный квиз 18+ #2', 'FUN #84', 'Эйнштейн Party #87']

    @pytest.mark.parametrize('gamename', notMultimediaGames)
    def test_tag_is_not_multimedia(self, gamename):
        '''Проверяет что тэг Мультимедиа не присваивается тем играм, которым не должен'''
        tags = quizAggregator.assign_themes_to_quiz(gamename, '')
        assert 'Мультимедиа' not in tags


    rookieGames = ['[новички] NSK #461']
    @pytest.mark.parametrize('gamename', rookieGames)
    def test_tag_is_rookie(self, gamename):
        '''Проверяет присвоение тэга Новички для различных форматов названия игры'''
        tags = quizAggregator.assign_themes_to_quiz(gamename, '')
        assert 'Новички' in tags


    nostalgiaGames = ['Новый год СССР', 'СССР vs 90ые!', 'Кино и музыка СССР #6', 'Угадай мелодию Дискотека 80-х', '00-е vs 90-е']
    @pytest.mark.parametrize('gamename', nostalgiaGames)
    def test_tag_is_nostalgia(self, gamename):
        '''Проверяет присвоение тэга Ностальгия для различных форматов названия игры'''
        tags = quizAggregator.assign_themes_to_quiz(gamename, '')
        assert 'Ностальгия' in tags


    nsfwGames = ['Черный квиз 18+ #2', '18+ #16 За гранью приличия', 'Черный квиз #13', 'Чёрный квиз №666']
    @pytest.mark.parametrize('gamename', nsfwGames)
    def test_tag_is_nsfw(self, gamename):
        '''Проверяет присвоение тэга 18+ для различных форматов названия игры'''
        tags = quizAggregator.assign_themes_to_quiz(gamename, '')
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
        cityOrganizators = ['Оставить всех организаторов', 'Квиз Плиз', 'Лига Индиго', 'Мама Квиз',
                        'WOW Quiz/ Эйнштейн Party']
        cityLinks = ['placeholder', 'wrongtesturl', 'wrongtesturl', 'wrongtesturl', 'wrongtesturl']
        games, organizatorErrors = quizAggregator.collectQuizData(cityOrganizators, cityLinks)
        assert len(organizatorErrors) == 4


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


class TestCreateQuizList:
    '''Класс для тестирования функции quizAggregator.createQuizList()'''

    def test_sort_by_date_and_formatting(self, expected_games):
        '''Проверяем что игры разных организаторов были правильно отсортированы по дате проведения,
        формат предоставляемых данных соответствует ожидаемому,а заодно проверяем кейс для случая когда
        выбран любой день недели (DOW = [1...7]
        '''
        organizatorErrors = []
        dow = [1, 2, 3, 4, 5, 6, 7]
        selected_theme = 'Оставить все'
        excl_bar, excl_theme, excl_orgs = 'None', 'None', 'None'
        expectedQuizList = [
'1. <b>Мама Квиз</b>: КВИЗАНУТЫЙ НОВЫЙ ГОД 2024. Бар: MISHKIN&MISHKIN, среда, 13 декабря, 19:30\n',
'2. <b>Квиз Плиз</b>: Квиз, плиз! NSK #567. Бар: Арт П.А.Б., четверг, 14 декабря, 20:00\n',
'3. <b>Лига Индиго</b>: Новый год СССР. Бар: Три Лося, понедельник, 18 декабря, 19:30\n',
'4. <b>Квиз Плиз</b>: Квиз, плиз! NSK #569. Бар: Арт П.А.Б., вторник, 19 декабря, 20:00\n',
'5. <b>Квиз Плиз</b>: Квиз, плиз! NSK #570. Бар: Арт П.А.Б., четверг, 21 декабря, 20:00\n',
'6. <b>WOW Quiz/ Эйнштейн Party</b>: Обо всём. Похмельно-новогодняя #47 . Бар: Три Лося, вторник, 2 января, 16:00\n',
'7. <b>Мама Квиз</b>: АЛКОКВИЗ #2. Бар: MISHKIN&MISHKIN, среда, 3 января, 14:00\n',
'8. <b>WOW Quiz/ Эйнштейн Party</b>: Угадай мелодию. Русское (туры по жанрам). Бар: Три Лося, среда, 3 января, 16:00\n',
'9. <b>Мама Квиз</b>: КИНОМЬЮЗИК: НОВОГОДНИЙ #2. Бар: MISHKIN&MISHKIN, четверг, 4 января, 14:00\n',
'10. <b>WOW Quiz/ Эйнштейн Party</b>: Топовые кино, мультфильмы, сериалы #4. Бар: Три Лося, четверг, 4 января, 16:00\n',
'11. <b>Мама Квиз</b>: ЛОГИКА ГДЕ? #14. Бар: MISHKIN&MISHKIN, пятница, 5 января, 14:00\n',
'12. <b>WOW Quiz/ Эйнштейн Party</b>: Советское кино #2 (туры по 5 фильмам). Бар: Три Лося, пятница, 5 января, 16:00\n',
'13. <b>Мама Квиз</b>: КЛАССИКА #128. Бар: MISHKIN&MISHKIN, суббота, 6 января, 14:00\n',
'14. <b>WOW Quiz/ Эйнштейн Party</b>: РУсская музыка 90-х и 00-х #2. Бар: Три Лося, суббота, 6 января, 16:00\n',
'15. <b>WOW Quiz/ Эйнштейн Party</b>: Гарри Поттер лайт #29 (с туром про рождество). Бар: Три Лося, воскресенье, 7 января, 16:00\n'
]
        returnedQuizList = quizAggregator.createQuizList(expected_games, organizatorErrors, dow, selected_theme, excl_bar, excl_theme, excl_orgs)
        assert expectedQuizList == returnedQuizList


    def test_dow_1_to_5(self, expected_games):
        '''Проверяем что функция вернула только игры проходящие в будние дни'''
        organizatorErrors = []
        dow = [1, 2, 3, 4, 5]
        selected_theme = 'Оставить все'
        excl_bar, excl_theme, excl_orgs = 'None', 'None', 'None'
        returnedQuizList = quizAggregator.createQuizList(expected_games, organizatorErrors, dow, selected_theme,
                                                         excl_bar, excl_theme, excl_orgs)
        for quiz in returnedQuizList:
            assert 'суббота' not in quiz
            assert 'воскресенье' not in quiz


    def test_dow_6_to_7(self, expected_games):
        '''Проверяем что функция вернула только игры проходящие в выходные дни '''
        organizatorErrors = []
        dow = [6, 7]
        selected_theme = 'Оставить все'
        excl_bar, excl_theme, excl_orgs = 'None', 'None', 'None'
        returnedQuizList = quizAggregator.createQuizList(expected_games, organizatorErrors, dow, selected_theme,
                                                         excl_bar, excl_theme, excl_orgs)
        for quiz in returnedQuizList:
            assert 'понедельник' not in quiz
            assert 'вторник' not in quiz
            assert 'среда' not in quiz
            assert 'четверг' not in quiz
            assert 'пятница' not in quiz


    def test_filter_by_tag_classic(self, expected_games):
        '''Проверяет что при выборе темы возвращаются только игры с тематикой Классика'''
        organizatorErrors = []
        dow = [1, 2, 3, 4, 5, 6, 7]
        selected_theme = 'Классика'
        excl_bar, excl_theme, excl_orgs = 'None', 'None', 'None'
        expectedQuizList = [
            '1. <b>Квиз Плиз</b>: Квиз, плиз! NSK #567. Бар: Арт П.А.Б., четверг, 14 декабря, 20:00\n',
            '2. <b>Квиз Плиз</b>: Квиз, плиз! NSK #569. Бар: Арт П.А.Б., вторник, 19 декабря, 20:00\n',
            '3. <b>Квиз Плиз</b>: Квиз, плиз! NSK #570. Бар: Арт П.А.Б., четверг, 21 декабря, 20:00\n',
            '4. <b>WOW Quiz/ Эйнштейн Party</b>: Обо всём. Похмельно-новогодняя #47 . Бар: Три Лося, вторник, 2 января, 16:00\n',
            '5. <b>Мама Квиз</b>: КЛАССИКА #128. Бар: MISHKIN&MISHKIN, суббота, 6 января, 14:00\n'
        ]
        returnedQuizList = quizAggregator.createQuizList(expected_games, organizatorErrors, dow, selected_theme,
                                                         excl_bar, excl_theme, excl_orgs)
        assert expectedQuizList == returnedQuizList


    def test_filter_by_tag_multimedia(self, expected_games):
        '''Проверяем что при выборе темы возвращаются только игры с тематикой Мультимедиа'''
        organizatorErrors = []
        dow = [1, 2, 3, 4, 5, 6, 7]
        selected_theme = 'Мультимедиа'
        excl_bar, excl_theme, excl_orgs = 'None', 'None', 'None'
        expectedQuizList = [
            '1. <b>WOW Quiz/ Эйнштейн Party</b>: Угадай мелодию. Русское (туры по жанрам). Бар: Три Лося, среда, 3 января, 16:00\n',
            '2. <b>Мама Квиз</b>: КИНОМЬЮЗИК: НОВОГОДНИЙ #2. Бар: MISHKIN&MISHKIN, четверг, 4 января, 14:00\n',
            '3. <b>WOW Quiz/ Эйнштейн Party</b>: Топовые кино, мультфильмы, сериалы #4. Бар: Три Лося, четверг, 4 января, 16:00\n',
            '4. <b>WOW Quiz/ Эйнштейн Party</b>: Советское кино #2 (туры по 5 фильмам). Бар: Три Лося, пятница, 5 января, 16:00\n',
            '5. <b>WOW Quiz/ Эйнштейн Party</b>: РУсская музыка 90-х и 00-х #2. Бар: Три Лося, суббота, 6 января, 16:00\n',
            '6. <b>WOW Quiz/ Эйнштейн Party</b>: Гарри Поттер лайт #29 (с туром про рождество). Бар: Три Лося, воскресенье, 7 января, 16:00\n'
        ]
        returnedQuizList = quizAggregator.createQuizList(expected_games, organizatorErrors, dow, selected_theme,
                                                         excl_bar, excl_theme, excl_orgs)
        assert expectedQuizList == returnedQuizList


    def test_filter_by_tag_nostalgy(self, expected_games):
        '''Проверяем что при выборе темы возвращаются только игры с тематикой Ностальгия'''
        organizatorErrors = []
        dow = [1, 2, 3, 4, 5, 6, 7]
        selected_theme = 'Ностальгия'
        excl_bar, excl_theme, excl_orgs = 'None', 'None', 'None'
        expectedQuizList = [
            '1. <b>Лига Индиго</b>: Новый год СССР. Бар: Три Лося, понедельник, 18 декабря, 19:30\n',
            '2. <b>WOW Quiz/ Эйнштейн Party</b>: Советское кино #2 (туры по 5 фильмам). Бар: Три Лося, пятница, 5 января, 16:00\n',
            '3. <b>WOW Quiz/ Эйнштейн Party</b>: РУсская музыка 90-х и 00-х #2. Бар: Три Лося, суббота, 6 января, 16:00\n'
        ]

        returnedQuizList = quizAggregator.createQuizList(expected_games, organizatorErrors, dow, selected_theme,
                                                         excl_bar, excl_theme, excl_orgs)
        assert expectedQuizList == returnedQuizList


    def test_filter_by_tag_nsfw(self, expected_games_2):
        '''Проверяем что при выборе темы возвращаются только игры с тематикой 18+
        Здесь используем отдельный набор игр, так как в локальных HTML нет игр с нужным тэгом'''
        organizatorErrors = []
        dow = [1, 2, 3, 4, 5, 6, 7]
        selected_theme = '18+'
        excl_bar, excl_theme, excl_orgs = 'None', 'None', 'None'
        expectedQuizList = [
    '1. <b>WOW Quiz/ Эйнштейн Party</b>: Черный квиз 18+ #2. Бар: Три Лося, воскресенье, 29 января, 18:00\n',
    '2. <b>WOW Quiz/ Эйнштейн Party</b>: 18+ #16 За гранью приличия. Бар: Три Лося, воскресенье, 19 февраля, 18:00\n'
        ]

        returnedQuizList = quizAggregator.createQuizList(expected_games_2, organizatorErrors, dow, selected_theme,
                                                         excl_bar, excl_theme, excl_orgs)
        assert expectedQuizList == returnedQuizList

    def test_filter_by_tag_rookie(self, expected_games_2):
        '''Проверяем что при выборе темы возвращаются только игры с тематикой Новички
        Здесь используем отдельный набор игр, так как в локальных HTML нет игр с нужным тэгом'''
        organizatorErrors = []
        dow = [1, 2, 3, 4, 5, 6, 7]
        selected_theme = 'Новички'
        excl_bar, excl_theme, excl_orgs = 'None', 'None', 'None'
        expectedQuizList = [
    '1. <b>Квиз Плиз</b>: [новички] NSK #459. Бар: Максимилианс, суббота, 28 января, 16:00\n',
    '2. <b>Квиз Плиз</b>: [новички] NSK #459. Бар: Арт П.А.Б., воскресенье, 29 января, 16:00\n'
    ]
        returnedQuizList = quizAggregator.createQuizList(expected_games_2, organizatorErrors, dow, selected_theme,
                                                         excl_bar, excl_theme, excl_orgs)
        assert expectedQuizList == returnedQuizList


    @pytest.mark.parametrize('excl_bar', ['Три лося', 'Mishkin&Mishkin', 'Арт П.А.Б.', 'Максимилианс',
                                     'Типография', 'Руки ВВерх!'])
    def test_by_excl_bar(self, expected_games, expected_games_2, excl_bar):
        '''Проверяет что правильно работает исключение баров. Проверяем на двух наборах квизов,
        так как в первом (из локальных HMTL) есть не все бары
        '''
        organizatorErrors = []
        dow = [1, 2, 3, 4, 5, 6, 7]
        selected_theme = 'Оставить все'
        excl_theme, excl_orgs = 'None', 'None'
        returnedQuizList1 = quizAggregator.createQuizList(expected_games, organizatorErrors, dow, selected_theme, excl_bar, excl_theme, excl_orgs)
        returnedQuizList2 = quizAggregator.createQuizList(expected_games_2, organizatorErrors, dow, selected_theme,
                                                          excl_bar, excl_theme, excl_orgs)
        for quiz in returnedQuizList1:
            assert excl_bar not in quiz

        for quiz in returnedQuizList2:
            assert excl_bar not in quiz

    @pytest.mark.parametrize('excl_theme', ['Классика', 'Мультимедиа', 'Новички', 'Ностальгия', '18+'])
    def test_by_excl_theme(self, expected_games, expected_games_2, excl_theme):
        '''Проверяет что правильно работает исключение тематик. Проверяем на двух наборах квизов,
        так как в первом (из локальных HMTL) есть не все тематики
        '''
        organizatorErrors = []
        dow = [1, 2, 3, 4, 5, 6, 7]
        selected_theme = 'Оставить все'
        excl_bar, excl_orgs = 'None', 'None'
        returnedQuizList1 = quizAggregator.createQuizList(expected_games, organizatorErrors, dow, selected_theme,
                                                          excl_bar, excl_theme, excl_orgs)
        returnedQuizList2 = quizAggregator.createQuizList(expected_games_2, organizatorErrors, dow, selected_theme,
                                                          excl_bar, excl_theme, excl_orgs)

        for quiz in returnedQuizList1:
            assert excl_theme not in quiz

        for quiz in returnedQuizList2:
            assert excl_theme not in quiz

    @pytest.mark.parametrize('excl_orgs', ['Квиз Плиз', 'Лига Индиго', 'WOW Quiz/ Эйнштейн Party', 'Мама Квиз'])
    def test_by_excl_orgs(self, expected_games, excl_orgs):
        '''Проверяет что правильно работает исключение организаторов'''
        organizatorErrors = []
        dow = [1, 2, 3, 4, 5, 6, 7]
        selected_theme = 'Оставить все'
        excl_bar, excl_theme = 'None', 'None'
        returnedQuizList = quizAggregator.createQuizList(expected_games, organizatorErrors, dow, selected_theme,
                                                          excl_bar, excl_theme, excl_orgs)

        for quiz in returnedQuizList:
            assert excl_orgs not in quiz


    def test_organizator_errors(self, expected_games):
        '''Проверяем что правильно выводятся ошибки по организаторам, при их наличии'''
        organizatorErrors = {
            'Квиз Плиз': "Invalid URL 'wrongtesturl': No scheme supplied. Perhaps you meant https://wrongtesturl?",
            'Лига Индиго': "Invalid URL 'wrongtesturl': No scheme supplied. Perhaps you meant https://wrongtesturl?",
            'WOW Quiz/ Эйнштейн Party': "Invalid URL 'wrongtesturl': No scheme supplied. Perhaps you meant https://wrongtesturl?",
            'Мама Квиз': "Invalid URL 'wrongtesturl': No scheme supplied. Perhaps you meant https://wrongtesturl?"
        }
        dow = [1, 2, 3, 4, 5, 6, 7]
        selected_theme = 'Оставить все'
        excl_bar, excl_theme, excl_orgs = 'None', 'None', 'None'
        expectedEnding = [
            '\nК сожалению не удалось получить информацию по следующим организаторам: ',
            'Квиз Плиз',
            'Лига Индиго',
            'WOW Quiz/ Эйнштейн Party',
            'Мама Квиз',
            '\nПопробуй запросить информацию по ним позже.'
        ]
        returnedQuizList = quizAggregator.createQuizList(expected_games, organizatorErrors, dow, selected_theme,
                                                         excl_bar, excl_theme, excl_orgs)
        assert expectedEnding == returnedQuizList[-6:]