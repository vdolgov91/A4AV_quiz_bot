import quizAggregator

import pytest
from unittest.mock import patch

def test_createInfoByCity_with_None():
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
def test_createInfoByCity_with_real_city():
    '''Проверяет createInfoByCity если отдать на вход функции существующий моковый город'''
    expectedBars = ['Оставить все бары', 'Три лося', 'Mishkin&Mishkin', 'Арт П.А.Б.', 'Максимилианс', 'Типография', 'Руки ВВерх!']
    expectedOrganizators = ['Оставить всех организаторов', 'Квиз Плиз', 'Лига Индиго', 'Мама Квиз', 'WOW Quiz/ Эйнштейн Party']
    expectedLinks =  ['placeholder', 'https://nsk.quizplease.ru/schedule', 'https://ligaindigo.ru/novosibirsk', 'https://nsk.mamaquiz.ru/', 'https://nsk.wowquiz.ru/schedule']
    cityBars, cityOrganizators, cityLinks = quizAggregator.createInfoByCity('Новосибирск')
    assert expectedBars == cityBars
    assert expectedOrganizators == cityOrganizators
    assert expectedLinks == cityLinks


def test_tag_with_None_input():
    '''Проверяет передачу некорректных параметров на вход assignThemesToQuiz()'''
    tags = quizAggregator.assignThemesToQuiz(None, None)
    print(tags)
    # TODO: доделать когда в функции будет обработка ошибки


@pytest.mark.parametrize('gamename', ['Игра №1 Сезон №1', 'Игра №222 Сезон №11', 'игра №3   сезона №5  '])
def test_tag_is_classic_liga_indigo(gamename):
    '''Проверяет присвоение корректного тэга для названий игр Лиги Индиго'''
    tags = quizAggregator.assignThemesToQuiz(gamename, 'Лига Индиго')
    assert 'Классика' in tags


classicGames = ['Квиз, плиз! NSK #569', 'Угадайка обо всём #44 ( С туром к Новому году)', 'Обо всём #46 Новогодняя',
'КЛАССИКА #128', 'Квиз, плиз! [железные яйца] NSK #5', '[новички] NSK #459', 'FUN #84', 'Эйнштейн Party #85',
'Блиц №1']

@pytest.mark.parametrize('gamename', classicGames)
def test_tag_is_classic(gamename):
    '''Проверяет присвоение тэга Классика для различных форматов названия игры'''
    tags = quizAggregator.assignThemesToQuiz(gamename, '')
    assert 'Классика' in tags

notClassicGames = ['Угадай мелодию #64', 'КИНОМЬЮЗИК: НОВОГОДНИЙ #2', 'ЛОГИКА ГДЕ? #14', '[кино и музыка] NSK #93',
'Топ кинопоиска #7', 'СССР vs 90ые!', 'Черный квиз 18+ #2', 'Гарри Поттер #20 Лайт', '18+ #16 За гранью приличия',
'Угадай футбол #4', 'Аниме #3']

@pytest.mark.parametrize('gamename', notClassicGames)
def test_tag_is_not_classic(gamename):
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
def test_tag_is_multimedia(gamename):
    '''Проверяет присвоение тэга Мультимедиа для различных форматов названия игры'''
    tags = quizAggregator.assignThemesToQuiz(gamename, '')
    assert 'Мультимедиа' in tags


notMultimediaGames = ['Новый год СССР', 'Квиз, плиз! NSK #569', 'Угадайка обо всём #44', 'КЛАССИКА #128',
'[новички] NSK #461', 'СССР vs 90ые!', 'Черный квиз 18+ #2', 'FUN #84', 'Эйнштейн Party #87']

@pytest.mark.parametrize('gamename', notMultimediaGames)
def test_tag_is_not_multimedia(gamename):
    '''Проверяет что тэг Мультимедиа не присваивается тем играм, которым не должен'''
    tags = quizAggregator.assignThemesToQuiz(gamename, '')
    assert 'Мультимедиа' not in tags


rookieGames = ['[новички] NSK #461']
@pytest.mark.parametrize('gamename', rookieGames)
def test_tag_is_rookie(gamename):
    '''Проверяет присвоение тэга Новички для различных форматов названия игры'''
    tags = quizAggregator.assignThemesToQuiz(gamename, '')
    assert 'Новички' in tags


nostalgiaGames = ['Новый год СССР', 'СССР vs 90ые!', 'Кино и музыка СССР #6', 'Угадай мелодию Дискотека 80-х', '00-е vs 90-е']
@pytest.mark.parametrize('gamename', nostalgiaGames)
def test_tag_is_nostalgia(gamename):
    '''Проверяет присвоение тэга Ностальгия для различных форматов названия игры'''
    tags = quizAggregator.assignThemesToQuiz(gamename, '')
    assert 'Ностальгия' in tags


nsfwGames = ['Черный квиз 18+ #2', '18+ #16 За гранью приличия', 'Черный квиз #13', 'Чёрный квиз №666']
@pytest.mark.parametrize('gamename', nsfwGames)
def test_tag_is_nsfw(gamename):
    '''Проверяет присвоение тэга 18+ для различных форматов названия игры'''
    tags = quizAggregator.assignThemesToQuiz(gamename, '')
    assert '18+' in tags