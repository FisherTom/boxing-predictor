import requests
from lxml import html
import csv
import time
import pickle
import re


# def make_connection(login, password, cookies):
#     print('sending login request...')
#     headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0',
#                'Referer': 'http://boxrec.com/en/login',
#                }
#     login_data = {'_target_path': '', '_username': login, '_password': password,
#                   '_remember_me': 'on', '_login[go]': ''}
#     login_post_req = requests.post('http://boxrec.com/en/login',
#                      data=login_data,
#                      cookies=cookies)


# """ Old loading, does not work, log-in required """
# def get_tree(url):
#     headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'}
#     req = requests.get(url, headers=headers)
#     return html.fromstring(req.text.encode('utf-8'))

def get_tree(url):
    login = 'slonsky'
    password = 'mysecretpassword666slonsky'
    c = dict(_ga='GA1.2.2017541976.1515683682',
             _gid='GA1.2.2018961571.1515683682',
             boxrec_forum_k='',
             boxrec_forum_u='235197',
             boxrec_forum_sid='1347e92c7d37ce1e5051a46f77804de7',
             PHPSESSID='3tncd77ea670evnlh5f5mfm6vn',
             _gat='1')

    login_data = {'_target_path': url, '_username': login, '_password': password,
                  '_remember_me': 'on', '_login[go]': ''}


    login_post_req = requests.post('http://boxrec.com/en/login',
                                   data=login_data,
                                   cookies=c)

    return html.fromstring(login_post_req.text.encode('utf-8'))


def make_dump(filename, bouts):
    with open(filename, 'wb') as file:
        try:
            pickle.dump(bouts, file)
        except pickle.PicklingError:
            print("Failed to dump.")


def scrap_boxers(rows, bouts, dump_name, bout_keys):
    for i in range(0, len(rows)):
        print("\nBoxer #%d: " % (i + 1), end='', flush=True)
        link = rows[i].find_class('personLink')[0].attrib['href']

        scrap_bouts('http://boxrec.com' + link, bouts, bout_keys)

        make_dump(dump_name, bouts)


def scrap_bouts(boxer_url, bouts, bout_keys):
    def find_row(name, rows):
        for row in rows:
            title = row.find('.//b')  # title is stored in <b> tag
            if title is None:
                continue
            if name == title.text:
                return row

    def get_column_data(row, cast_type=str):
        # if bad or missing data do not cast,
        # just set None

        try:
            A = cast_type(row.getchildren()[0].text)  # left column
        except (IndexError, ValueError, TypeError) as e:
            A = None
        try:
            B = cast_type(row.getchildren()[2].text)  # right column
        except (IndexError, ValueError, TypeError) as e:
            B = None

        return A, B

    def scrap_bout_result(bout_tree):
        """  Decisions
        SD - splitted decision - Two judges have scored in favour of one boxer
             and the other judge has scored in favour of the other
        MD - majority decision - Two judges have scored in favour of one boxer
             and the other judge has scored in favour of a draw
        UD - unanimous decision - All three judges have scored in agreement
        KO - knock out - A boxer is knocked down and the referee has counted
             to 10 before he can rise
        TKO - technical knock out - The referee has stopped the fight due to a
             boxer being in no fit condition to continue
        DQ - A boxer is disqualified by the referee and loses the bout when he
             repeatedly or severely fouls or infringes the rules
        RTD - A boxer has retired between rounds
        """
        """ Results
        win_A | win_B | draw
        """

        def find_label():
            for label in ['textWon', 'textDrawn']:
                res = bout_tree.find_class(label)
                if len(res) == 0 or res[0].tag != 'span':
                    continue

                td = res[0].getparent()
                tr = td.getparent()
                tr_children = tr.getchildren()

                return tr_children.index(td), res[0].text

        index, res_string = find_label()
        positions = ['A', None, 'B']

        result, decision = res_string.split(' ')
        result_str = 'win_' + positions[index] if result == 'won' else 'draw'

        return result_str, decision

    def scrap_bout_info(link):
        try:
            tree = get_tree('http://boxrec.com' + link)
        except requests.RequestException as e:
            print('\n', e)
            print('Unable to load URL:\n', 'http://boxrec.com' + link)
            return None

        """ Scorecard """
        scores_A = [None, None, None]
        scores_B = [None, None, None]

        try:
            # last 3 header rows
            scorecard = tree.find_class('clearTable')[0].getchildren()[-3:]
            for i, row in enumerate(scorecard):
                scores_A[i], scores_B[i] = get_column_data(row, int)  # from left column
        except (TypeError, IndexError) as e:
            print('\n', e)

        rows = tree.find_class('responseLessDataTable')[0].findall('.//tr')

        """ Age """
        age_A, age_B = get_column_data(find_row('age', rows), int)

        """ Height """
        height_row = find_row('height', rows)

        try:
            height_A = int(height_row.getchildren()[0].text[-6:-3])  # e.g. 5′ 9″   /   175cm:
        except (IndexError, ValueError, TypeError) as e:
            height_A = None
        try:
            height_B = int(height_row.getchildren()[2].text[-6:-3])  # last 5 to 2 characters
        except (IndexError, ValueError, TypeError) as e:
            height_B = None

        """ Reach """  # hands amount length
        reach_row = find_row('reach', rows)

        try:
            reach_A = int(reach_row.getchildren()[0].text[-6:-3])  # e.g. 5′ 9″   /   175cm:
        except (IndexError, ValueError, TypeError) as e:
            reach_A = None
        try:
            reach_B = int(reach_row.getchildren()[2].text[-6:-3])  # last 5 to 2 characters
        except (IndexError, ValueError, TypeError) as e:
            reach_B = None

        """ KO's """
        ko_A, ko_B = get_column_data(find_row('KOs', rows), int)

        """ Stance """
        stance_A, stance_B = get_column_data(find_row('stance', rows), str)
        stance_A, stance_B = re.sub('[^a-z]', '', stance_A), re.sub('[^a-z]', '', stance_B)
        if stance_A not in ['orthodox', 'southpaw']:
            stance_A = None
        if stance_B not in ['orthodox', 'southpaw']:
            stance_B = None

        """ Won """
        won_A, won_B = get_column_data(find_row('won', rows), int)

        """ Lost """
        lost_A, lost_B = get_column_data(find_row('lost', rows), int)

        """ Drawn """
        drawn_A, drawn_B = get_column_data(find_row('drawn', rows), int)

        """ Result """
        result, decision = scrap_bout_result(tree)

        return {'age_A': age_A, 'age_B': age_B,
                'height_A': height_A, 'height_B': height_B,
                'reach_A': reach_A, 'reach_B': reach_B,
                'stance_A': stance_A, 'stance_B': stance_B,
                'won_A': won_A, 'won_B': won_B,
                'lost_A': lost_A, 'lost_B': lost_B,
                'drawn_A': drawn_A, 'drawn_B': drawn_B,
                'kos_A': ko_A, 'kos_B': ko_B,
                'result': result, 'decision': decision,
                'judge1_A': scores_A[0], 'judge1_B': scores_B[0],
                'judge2_A': scores_A[1], 'judge2_B': scores_B[1],
                'judge3_A': scores_A[2], 'judge3_B': scores_B[2]}

    def scrap_weights(row):
        try:
            weight_A = int(row.getchildren()[2].text)
        except (IndexError, ValueError, TypeError) as e:
            weight_A = None
        try:
            weight_B = int(row.getchildren()[6].text)
        except (IndexError, ValueError, TypeError) as e:
            weight_B = None

        return weight_A, weight_B

    """ Function instructions """
    try:
        tree = get_tree(boxer_url)
    except requests.RequestException as e:
        print('\n', e)
        print('Unable to load URL:\n', boxer_url)
        return

    for row in tree.find_class('drawRowBorder'):
        print(".", end='', flush=True)
        bout = row.find_class('bout')
        if len(bout) == 0:
            continue

        bout_link = bout[0].getparent().attrib['href']
        if bout_link in bout_keys:
            continue

        bout_keys.append(bout_link)

        result = row.find_class('boutResult')
        if len(result) > 0 and result[0].text not in ['W', 'D', 'L']: # scheduled/no-contest/etc.
            continue

        bout_info = scrap_bout_info(bout_link)
        if bout_info is None:

            continue

        bout_info['weight_A'], bout_info['weight_B'] = scrap_weights(row)

        bouts[bout_link] = bout_info


def write_header(name):
    file = open(name, 'w', newline='')
    writer = csv.writer(file)
    writer.writerow(('age_A', 'age_B',
                     'height_A', 'height_B',
                     'reach_A', 'reach_B',
                     'stance_A', 'stance_B',
                     'weight_A', 'weight_B',
                     'won_A', 'won_B',
                     'lost_A', 'lost_B',
                     'drawn_A', 'drawn_B',
                     'kos_A', 'kos_B',
                     'result', 'decision',
                     'judge1_A', 'judge1_B',
                     'judge2_A', 'judge2_B',
                     'judge3_A', 'judge3_B'))
    file.close()


def write_bouts(name, bouts):
    file = open(name, 'a', newline='')
    writer = csv.writer(file)
    for key in bouts:
        bout = bouts[key]
        writer.writerow((bout['age_A'], bout['age_B'],
                         bout['height_A'], bout['height_B'],
                         bout['reach_A'], bout['reach_B'],
                         bout['stance_A'], bout['stance_B'],
                         bout['weight_A'], bout['weight_B'],
                         bout['won_A'], bout['won_B'],
                         bout['lost_A'], bout['lost_B'],
                         bout['drawn_A'], bout['drawn_B'],
                         bout['kos_A'], bout['kos_B'],
                         bout['result'], bout['decision'],
                         bout['judge1_A'], bout['judge1_B'],
                         bout['judge2_A'], bout['judge2_B'],
                         bout['judge3_A'], bout['judge3_B']))
    file.close()


def HOLY_scrap(pages_nums, out_filename, override=False, dump_filename='dump', load_dump=False):
    if load_dump:
        with open(dump_filename + '_bouts.pickle', 'rb') as dump:
            bouts = pickle.load(dump)

        with open(dump_filename + '_keys.pickle', 'rb') as dump:
            bout_keys = pickle.load(dump)
    else:
        bouts = dict()
        bout_keys = list()


    if override:
        write_header(out_filename)

    for i in pages_nums:
        print('\nScrapping %d-th page' % (i + 1))
        page_start_time = time.time()

        # http://boxrec.com/en/ratings?r%5Bsex%5D=M&r%5Bstance%5D=&r%5Bstatus%5D=&r_go=
        # page with all boxers - 331,615 men; 6,333 pages; no female
        url = "http://boxrec.com/en/ratings?offset=%d" % (i * 50)

        try:
            tree = get_tree(url)
        except requests.RequestException as e:
            print('\n', e)
            print('Unable to load URL:\n', url)
            continue

        rows = tree.find_class('drawRowBorder')

        scrap_boxers(rows, bouts, dump_filename + '_bouts.pickle', bout_keys)

        write_bouts(out_filename, bouts)
        bouts = dict()
        make_dump(dump_filename + '_keys.pickle', bout_keys)

        print('\nScrapped %d-th page, time: %.2fs' % ((i + 1), (time.time() - page_start_time)))


HOLY_scrap([4,5, 6, 7, 8], 'bouts_out.csv', load_dump=True)
