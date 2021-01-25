import config
import csv
from config import Answers, Messages, BI_2_PRIZE, DOWNLOADS_DIR, TOKEN
import eval7
from importlib import reload  # Python 3.4+ only.
from pypokertools.parsers import PSHandHistory
import pypokertools
from pypokertools.storage.hand_storage import HandStorage
from pypokertools.calc.pokercalc import Icm, EV
from pathlib import Path
import requests
import telebot
from telebot import types
from typing import Tuple
import traceback
import sys
from enum import Enum
from collections import namedtuple
import time
from mimetypes import guess_type
import logging
import zipfile
import tempfile
import pdb

logger = logging.getLogger(__name__)
CWD = Path.cwd()
result_fields = ['h_id',
                 'hero',
                 'prize',
                 'ai_equity',
                 'icm_ev_diff_cur',
                 'icm_ev_cur',
                 'icm_ev_diff',
                 'icm_ev',
                 'chip_ev_diff',
                 'chip_won',
                 'dt',
                 'bi',
                 'hero_cards',
                 'won_amount',
                 't_id'
                 ]



CalcResults = namedtuple('CalcResults', result_fields)


class CalcResultsReport:
    def __init__(self) -> None:
        self.ai_equity = 0
        self.total_won = 0
        self.icm_ev = 0
        self.icm_evdiff = 0
        self.chip_won = 0
        self.chip_evdiff = 0
        self.hands_count = 0
        self.ai_hands_count = 0
        self.tournaments_set = set()
        self.results_list = []

    def add_result(self, cr: CalcResults) -> None:
        self.ai_equity += cr.ai_equity
        self.total_won += cr.won_amount
        self.icm_ev += cr.icm_ev_cur
        self.icm_evdiff += cr.icm_ev_diff_cur
        self.chip_won += cr.chip_won
        self.chip_evdiff += cr.chip_ev_diff
        self.hands_count += 1
        self.ai_hands_count += 1 if cr.ai_equity else 0
        self.tournaments_set.add((cr.t_id, cr.bi))
        self.results_list.append({'t_id': cr.t_id,
                                  'h_id': cr.h_id,
                                  'hero_cards': cr.hero_cards,
                                  'ai_equity': cr.ai_equity,
                                  'won_amount': cr.won_amount,
                                  'icm_ev_cur': cr.icm_ev_cur,
                                  'icm_ev_diff_cur': cr.icm_ev_diff_cur,
                                  'chip_won': cr.chip_won,
                                  'chip_ev_diff': cr.chip_ev_diff,
                                  'bi': cr.bi})

    def print_report(self) -> str:
        """print report"""
        if self.hands_count == 0:
            return ""
        if self.ai_hands_count:
            avg_ai_equity = self.ai_equity / self.ai_hands_count
        else:
            avg_ai_equity = 0
        total_bi = sum([t[1] for t in list(self.tournaments_set)]) / len(self.tournaments_set)
        report = []
        report.append(f'avg all in eq: {avg_ai_equity}')
        report.append(f'total won: {self.total_won}')
        report.append(f'ICM EV: {self.icm_ev}')
        report.append(f'ICM EV diff: {self.icm_evdiff}')
        report.append(f' Chip won: {self.chip_won}')
        report.append(f'Chip EV diff: {self.chip_evdiff}')
        report.append(f'Total BI: {total_bi}')
        report.append(f'Total hands: {self.hands_count}')
        report.append(f'Total tounrnaments: {len(self.tournaments_set)}')

        return '\n'.join(report)

    def save_csv(self, file_path) -> bool:
        """save report to file_path
        :file_path: path to file
        :returns: True if success
        """
        fieldnames = ['t_id', 'h_id', 'hero_cards',
                      'ai_equity', 'won_amount', 'icm_ev_cur',
                      'icm_ev_diff_cur', 'chip_won', 'chip_ev_diff', 'bi']
        try:
            with open(file_path, mode='w', encoding='utf-8') as f:
                csv_writer = csv.DictWriter(f, fieldnames=fieldnames)
                csv_writer.writeheader()

                for row in self.results_list:
                    csv_writer.writerow(row)

        except Exception as e:
            return False
        return True


output_dir_path = CWD.joinpath(DOWNLOADS_DIR)
if not output_dir_path.exists():
    output_dir_path.mkdir()

fmt = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M')
fh = logging.FileHandler('evcalcbot.log', mode='a')
fh.setFormatter(fmt)
logger.addHandler(fh)
logger.setLevel(logging.INFO)

bot = telebot.TeleBot(config.TOKEN)

keyboard_remove = types.ReplyKeyboardRemove(selective=False)


def get_prize_structure(parsed_hand):
    bi = parsed_hand.bi - parsed_hand.rake
    return BI_2_PRIZE.get(bi, ((1,)))


def get_calc_results(hand_text: str) -> CalcResults:
    parsed_hand = PSHandHistory(hand_text)
    hero = parsed_hand.hero
    prize = get_prize_structure(parsed_hand)
    icm = Icm(prize)
    try:
        ev_calc = EV(parsed_hand, icm)
        ev_calc.calc(hero)
        ai_equity = round(ev_calc.get_probs(hero), 4) * 100
        icm_ev_diff_cur = round(ev_calc.icm_ev_diff(), 2)
        icm_ev_cur = round(ev_calc.icm_ev(), 2)
        icm_ev_diff = round(ev_calc.icm_ev_diff_pct(), 4) * 100
        icm_ev = round(ev_calc.icm_ev_pct(), 4) * 100
        chip_ev_diff = round(ev_calc.chip_diff_ev_adj(), 0)
        chip_won = ev_calc.chip_net_won().get(hero, 0)
        won_amount = round(parsed_hand.prize_won.get(hero, 0), 2)
    except Exception as e:
        logger.exception(f"Exception", exc_info=sys.exc_info())
    rc = CalcResults(dt=parsed_hand.datetime,
                     bi=parsed_hand.bi,
                     hero_cards=parsed_hand.hero_cards,
                     hero=parsed_hand.hero,
                     h_id=parsed_hand.hid,
                     prize=get_prize_structure(parsed_hand),
                     ai_equity=ai_equity,
                     icm_ev_diff_cur=icm_ev_diff_cur,
                     icm_ev_cur=icm_ev_cur,
                     icm_ev_diff=icm_ev_diff,
                     icm_ev=icm_ev,
                     chip_ev_diff=chip_ev_diff,
                     chip_won=chip_won,
                     won_amount=won_amount,
                     t_id=parsed_hand.tid,
                     )
    return rc


def format_calc_results(cr: CalcResults) -> str:
    result = []
    result.append(str(cr.dt))
    result.append(str(cr.bi) + ' $')
    result.append(cr.hero)
    result.append(cr.hero_cards)
    result.append(f'all in equity: {cr.ai_equity} %')
    result.append(f'prize: {cr.prize}')
    result.append(f'chip diff: {cr.chip_ev_diff}')
    result.append(f'chip won: {cr.chip_won}')
    result.append(f'icm diff pct: {cr.icm_ev_diff} %')
    result.append(f'icm diff $ : {cr.icm_ev_diff_cur}')
    result.append(f'icm pct: {cr.icm_ev} %')
    result.append(f'icm $: {cr.icm_ev_cur}')
    result.append(f'won $: {cr.won_amount}')
    result = '\n'.join(result)
    return result


def download(file_id):
    """ Download
    returns: file text str if read = True else None
    """
    file_obj = bot.get_file(file_id)
    file = requests.get(f'https://api.telegram.org/file/bot{config.TOKEN}/{file_obj.file_path}')
    return file.content


def save_binary_content(content, file_name):
    """ saves file_name to output_dir_path"""
    with open(output_dir_path.joinpath(file_name), 'w+b') as f:
        f.write(content)


def get_uniq_id() -> str:
    return str(round(time.time()))


def process_hh(txt: str) -> Tuple[CalcResults, str, str]:
    """ get reults from calc and save saves to file
    generates file name
    log errors
    returns CalcResult for output to bot and file name of saved hand history
    """

    cr = None
    fn = get_uniq_id() + '.txt'
    log_record = False
    try:
        cr = get_calc_results(txt)
        result = format_calc_results(cr)
    except Exception as e:
        result = traceback.format_exc()
        log_record = True
    if cr:
        file_name = cr.h_id + '.txt'
    else:
        file_name = fn
    save_binary_content(txt.encode(), file_name)

    if log_record:
        logger.exception(f"Exception in file: {file_name}", exc_info=sys.exc_info())

    return (cr, result, file_name)


@bot.message_handler(regexp="Pokerstars Hand #.* Tournament #.*")
def handle_text_hh(message):  #
    txt = message.text
    cr = None
    fn = get_uniq_id() + '.txt'
    log_record = False
    try:
        cr = get_calc_results(txt)
        result = format_calc_results(cr)
    except Exception as e:
        result = traceback.format_exc()
        log_record = True
    if cr:
        file_name = cr.h_id + '.txt'
    else:
        file_name = fn
    save_binary_content(txt.encode(), file_name)

    if log_record:
        logger.exception(f"Exception in file: {file_name}", exc_info=sys.exc_info())
    bot.send_message(message.chat.id, result)

    markup = types.ReplyKeyboardMarkup(selective=True, resize_keyboard=True)
    itembtn1 = types.KeyboardButton(Answers['CORRECT'])
    itembtn2 = types.KeyboardButton(Answers['WRONG'])
    markup.add(itembtn1, itembtn2)
    bot.reply_to(message, Messages['ASK_FEEDBACK'], reply_markup=markup)
    bot.register_next_step_handler(message, register_feedback, file_name)


def get_text_from_zip(zip_file_path) -> str:
    """ returns generator"""
    if zipfile.is_zipfile(zip_file_path):
        with tempfile.TemporaryDirectory() as tmpdirname:
            zipfile.ZipFile(zip_file_path).extractall(tmpdirname)
            storage = HandStorage(tmpdirname)
            for hand in storage.read_hand():
                yield hand


def zip_doc_handler(message):
    """open zip file in message, save to download directory
    calculates stats for every hand and agregates stats in report
    """
    reply = Messages['GOT_FILE']
    bot.send_message(message.chat.id, reply, reply_markup=keyboard_remove)
    doc = message.document
    f_uid = get_uniq_id()
    file_obj = bot.get_file(doc.file_id)
    fp = Path(file_obj.file_path)
    save_fn = f_uid + fp.suffix

    try:
        save_binary_content(download(doc.file_id), save_fn)
        calc_report = CalcResultsReport()
        counter = 0

        response = bot.send_message(message.chat.id, 'Processing...', reply_markup=keyboard_remove)
        for txt in get_text_from_zip(output_dir_path.joinpath(save_fn)):
            if txt:
                cr, reply, file_name = process_hh(txt)
                if cr:
                    calc_report.add_result(cr)
                    counter += 1
    except Exception as e:
        reply = traceback.format_exc()
        logger.exception(f"Exception while downloading file: {fp}", exc_info=sys.exc_info())
        bot.send_message(message.chat.id, reply, reply_markup=keyboard_remove)

    fn = get_uniq_id() + '.csv'
    file_path = output_dir_path.joinpath(fn)

    if calc_report.save_csv(file_path):
        with open(file_path, 'r') as f:
            bot.send_document(message.chat.id, f)
    else:
        bot.send_message(message.chat.id, "Unable to send csv file", reply_markup=keyboard_remove)

    bot.send_message(message.chat.id, calc_report.print_report(), reply_markup=keyboard_remove)


def text_doc_handler(message):
    doc = message.document
    txt = download(doc.file_id).decode()
    cr, reply, file_name = process_hh(txt)
    bot.send_message(message.chat.id, reply)

    markup = types.ReplyKeyboardMarkup(selective=True, resize_keyboard=True)
    itembtn1 = types.KeyboardButton(Answers['CORRECT'])
    itembtn2 = types.KeyboardButton(Answers['WRONG'])
    markup.add(itembtn1, itembtn2)
    bot.reply_to(message, Messages['ASK_FEEDBACK'], reply_markup=markup)
    bot.register_next_step_handler(message, register_feedback, file_name)


@bot.message_handler(content_types=['document'])
def handle_doc(message):
    """
    routes message to handler based on file type
    """
    reply = Messages['GOT_FILE']
    mime_type_handlers = {
        'text/plain': text_doc_handler,
        'application/x-zip-compressed': zip_doc_handler,
        'application/zip': zip_doc_handler,
        }
    handler = mime_type_handlers.get(message.document.mime_type)
    if handler:
        handler(message)
    else:
        reply = Messages['WRONG_DOC'] + f" {message.document.mime_type}"
        bot.send_message(message.chat.id, reply, reply_markup=keyboard_remove)


@bot.message_handler(content_types=['text'], commands=['help'])
def send_help_message(message):  #
    bot.send_message(message.chat.id, Messages['HELP'], reply_markup=keyboard_remove)


@bot.message_handler(content_types=['text'])
def send_welcome_message(message):  #
    bot.send_message(message.chat.id, Messages['WELCOME'], reply_markup=keyboard_remove, parse_mode='Markdown')


def register_feedback(message, hh_file_name):
    text = message.text
    if text == Answers['WRONG']:
        bot.send_message(message.chat.id, Messages['SCREEN'], reply_markup=keyboard_remove)
        bot.register_next_step_handler(message, save_photo, hh_file_name)
    elif text == Answers['CORRECT']:
        bot.send_message(message.chat.id, Messages['GOT_FEEDBACK'], reply_markup=keyboard_remove)


def get_file_path(file_id) -> Path:
    file_obj = bot.get_file(file_id)
    return Path(file_obj.file_path)


def save_photo(message, hh_file_name):
    # downloaded photo will have same name as hh file

    reply = Messages['GOT_FEEDBACK']
    if message.content_type == 'photo':
        photo = message.photo[-1]
        file_obj = bot.get_file(photo.file_id)
        fp = Path(file_obj.file_path)
        try:
            # downloaded photo will have same name as hh file
            save_binary_content(download(photo.file_id), hh_file_name + fp.suffix)
            logger.error(f"Incorrect calculation: {hh_file_name}, screen: {fp.name}")
        except Exception as e:
            reply = traceback.format_exc()
            logger.exception(f"Exception while downloading file: {fp}", exc_info=sys.exc_info())
    elif message.content_type == 'document':
        doc = message.document
        file_obj = bot.get_file(doc.file_id)
        fp = Path(file_obj.file_path)
        try:
            save_binary_content(download(doc.file_id, hh_file_name), hh_file_name + fp.suffix)
            logger.error(f"Incorrect calculation: {hh_file_name}, screen: {doc.file_name}")
        except Exception as e:
            reply = traceback.format_exc()
            logger.exception(f"Exception while downloading file: {doc.file_name}", exc_info=sys.exc_info())

    bot.send_message(message.chat.id, reply)




if __name__ == '__main__':
    bot.infinity_polling()
