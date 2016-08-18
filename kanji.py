#!/usr/bin/python3

from argparse import ArgumentParser
from contextlib import closing
import csv
import json
from operator import itemgetter
import os
import random
import shelve
import sqlite3


ANKI_COL = '/home/loamhoof/Documents/Anki/Akarin!/collection.anki2'
DECK_NAME = 'Japanese Core 6000 Vocab and Sentences ALL STEPS'
MODEL_NAME = 'iKnow! Vocabulary Plus PoS'
CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(CURRENT_DIR, 'data')
KANJICSV_PATH = os.path.join(DATA_DIR, 'kanji_info.csv')
KANJILIST_PATH = os.path.join(DATA_DIR, 'kanji_list')
CURRKANJI_PATH = os.path.join(DATA_DIR, 'kanji_%s')
SHELVE_DIR = os.path.join(CURRENT_DIR, 'shelve')
KANJI_SHELF_PATH = os.path.join(SHELVE_DIR, 'kanji')
KANJI_INFO_SHELF_PATH = os.path.join(SHELVE_DIR, 'kanji_info')
KNOWN_WORDS_SHELF_PATH = os.path.join(SHELVE_DIR, 'known_words')

RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
NO_COLOR="\033[0m"


def dump(thing):
    print(json.dumps(thing, indent=4, sort_keys=True))


def find(criteria, haystack):
    return next(iter(needle for needle in haystack if criteria(needle)), None)


def init(_):
    with open(KANJICSV_PATH) as kanji_csv, shelve.open(KANJI_INFO_SHELF_PATH) as kanji_info_shelf:
        for kanji_info in csv.reader(kanji_csv, delimiter='#'):
            kanji_info_shelf[kanji_info[0]] = {
                'meaning': kanji_info[1],
                'words': list(zip(*([iter(kanji_info[2:])] * 3)))
            }


def reload(_):
    with closing(sqlite3.connect(ANKI_COL)) as conn, shelve.open(KNOWN_WORDS_SHELF_PATH) as known_words_shelf:
        col_query = conn.execute('SELECT decks, models FROM col')
        col = dict(zip(map(itemgetter(0), col_query.description), col_query.fetchone()))
        deck_id = find(lambda deck: deck['name'] == DECK_NAME, json.loads(col['decks']).values())['id']
        model_id = find(lambda model: model['name'] == MODEL_NAME, json.loads(col['models']).values())['id']

        cards_query = conn.execute("""
            SELECT n.flds
            FROM cards c
            JOIN notes n ON c.nid = n.id
            WHERE c.did = '%s'
            AND n.mid = '%s'
            AND c.queue != 0
            GROUP BY c.nid
        """ % (deck_id, model_id))

        words = {
            card[0].split('\x1f')[1]
            for card in cards_query
        }

        with open(KANJILIST_PATH, mode='w') as kanji_list_file:
            kanji_list_file.writelines('\n'.join(set(filter(lambda char: char > '\u30FC', ''.join(words)))))

        known_words_shelf['words'] = words


def get(kanji):

    with shelve.open(KANJI_INFO_SHELF_PATH) as kanji_info_shelf, shelve.open(KNOWN_WORDS_SHELF_PATH) as known_words_shelf:
        kanji_info = kanji_info_shelf[kanji]
        kanji_words = kanji_info['words']
        known_words = known_words_shelf['words']
        max_kanji_len = max(map(lambda word: len(word[0]), kanji_words))
        max_reading_len = max(map(lambda word: len(word[1]), kanji_words))

        print('Kanji: ' + CYAN + kanji + NO_COLOR)
        print('Meaning: ' + CYAN + kanji_info['meaning'] + NO_COLOR)
        print('Words:')
        print(*(
            format_word(word, max_kanji_len, max_reading_len, word[0] in known_words)
            for word in kanji_words
        ), sep='\n')


def curr(_):
    with open(CURRKANJI_PATH % os.getenv('TMUX_PANE')) as currkanji_file:
        get(currkanji_file.read()[0])


def format_word(word, max_kanji_len, max_reading_len, known_word):
    return ' '.join((
        GREEN if known_word else RED,
        word[0] + ' ' * ((max_kanji_len - len(word[0])) * 2),
        word[1] + ' ' * ((max_reading_len - len(word[1])) * 2),
        word[2],
        NO_COLOR
    ))


COMMANDS = {
    'init': init,
    'curr': curr,
    'reload': reload,
    'get': get,
}


if __name__ == '__main__':
    argparser = ArgumentParser()
    argparser.add_argument('command')
    argparser.add_argument('-k', dest='arg', required=False)
    args = argparser.parse_args()
    if args.command not in COMMANDS:
        raise Exception('Unknown command: %s' % args.command)

    COMMANDS[args.command](args.arg)
