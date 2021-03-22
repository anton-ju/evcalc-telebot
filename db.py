def edit(con, cr):
    cursor = con.cursor()
    insert = True
    update = False

    select_query = '''SELECT chip_ev_diff, icm_ev_diff FROM EvCalc \
        WHERE table_id = %s AND hand_id = %s AND hero = %s LIMIT 1'''
    select_params = (cr.t_id, cr.h_id, cr.hero)
    cursor.execute(select_query, select_params)
    for row in cursor:
        insert = False
        if row[0] != cr.chip_ev_diff or row[1] != cr.icm_ev_diff:
            update = True

    if insert:
        query = '''INSERT INTO EvCalc \
            (date,table_id,hand_id,hero,hero_cards,ai_equity,won_amount, \
            icm_ev_diff,icm_ev_diff_cur,chip_won,chip_ev_diff,bi) \
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'''
        params = (str(cr.dt), cr.t_id, cr.h_id, cr.hero, cr.hero_cards, cr.ai_equity,
                  cr.won_amount, cr.icm_ev_diff, cr.icm_ev_diff_cur, cr.chip_won, cr.chip_ev_diff, cr.bi)

    if update:
        query = '''UPDATE EvCalc SET chip_ev_diff = %s, icm_ev_diff = %s \
            WHERE table_id = %s AND hand_id = %s AND hero = %s'''
        params = (cr.icm_ev_diff, cr.chip_ev_diff, cr.t_id, cr.h_id, cr.hero)

    if update or insert:
        cursor.execute(query, params)
        con.commit()


def delete(con, hero, table_id='', hand_id=''):
    cursor = con.cursor()

    query = '''DELETE FROM EvCalc WHERE hero = %s'''
    params = (hero,)

    if table_id != '':
        query = '''DELETE FROM EvCalc WHERE table_id = %s AND hand_id = %s AND hero = %s'''
        params = (table_id, hand_id, hero)

    cursor.execute(query, params)
    con.commit()
