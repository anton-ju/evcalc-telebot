import psycopg2
from config import database, user, password, host


def insert_values(cr):
    con = psycopg2.connect(database=database[0], user=user[0], password=password[0], host=host[0])

    cursor = con.cursor()

    insert = True
    select_query = '''SELECT table_id FROM EvCalc WHERE table_id = %s AND hand_id = %s LIMIT 1'''
    select_params = (cr.t_id, cr.h_id)
    cursor.execute(select_query, select_params)
    for row in cursor:
        insert = False

    if insert:
        insert_query = '''INSERT INTO EvCalc \
            (date,table_id,hand_id,hero,hero_cards,ai_equity,won_amount, \
            icm_ev_diff,icm_ev_diff_cur,chip_won,chip_ev_diff,bi) \
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'''
        record_to_insert = (str(cr.dt), cr.t_id, cr.h_id, cr.hero, cr.hero_cards, cr.ai_equity,
                            cr.won_amount, cr.icm_ev_diff, cr.icm_ev_diff_cur, cr.chip_won, cr.chip_ev_diff, cr.bi)
        cursor.execute(insert_query, record_to_insert)
        con.commit()

    con.close()
