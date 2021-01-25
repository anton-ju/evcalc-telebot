import config
import evcalcbot
import zipfile
from pytest import skip


def test_config():
    prize = config.BI_2_PRIZE[107.84]
    assert prize == ((0.4984, 0.4984, 0.0032))


def test_get_text_from_zip():
    pass
    # with zipfile.ZipFile('zipfile-test.zip', mode='w') as zp:
    #     zp.write('evcalcbot.py')
    #     zp.write('config.py')

    # assert zipfile.is_zipfile('zipfile-test.zip')

    # file_gen = evcalcbot.get_text_from_zip('zipfile-test.zip')
    # assert len(list(file_gen)) == 2
