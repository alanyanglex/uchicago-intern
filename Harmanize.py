import pandas as pd
from fuzzywuzzy import fuzz
import re
import os

def strip_school(name, best_partial_ratio_match):
    s_name = name.lower()
    s_match = best_partial_ratio_match.lower()
    start = s_name.find(s_match)
    end = start + len(s_match)
    school = (name[0:start] + name[end:len(name)]).strip()
    school = sanitize_school(school).lower()
    print(name, school)
    return school

def sanitize_school(school_name):
    if school_name.lower().find('school') == -1 and school_name.lower().find('college') == -1:
        return ''
    regex = re.compile('[-,\.!?]')
    school_name = regex.sub('', school_name).strip()
    return school_name

def sanitize_name(name):
    # lower case, trimmed
    name = name.strip().lower()

    # remove The at the beginning
    if name.startswith("the "):
        name = name[4:len(name)]

    # replace acronyms
    namesplit = name.split()
    firstword = namesplit[0]
    if firstword in acronyms and name.find(acronyms[firstword].lower()) == -1:
        name = acronyms[firstword]
        if len(namesplit) > 1:
            name = name + ' ' + ' '.join(namesplit[1:])
        print(f"replaced by acronym: {name}")
    return name

def fuzzy_match(name, loc):
    best_ratio = 0
    best_partial_ratio = 0
    best_token_sort_ratio = 0
    best_ratio_match = ""
    best_partial_ratio_match = ""
    best_token_sort_ratio_match = ""
    cleaned_name = sanitize_name(name)
    for u_name in all_school_names:
        cleaned_u_name = u_name.strip().lower()
        ratio = fuzz.ratio(cleaned_name, cleaned_u_name)
        partial_ratio = fuzz.partial_ratio(cleaned_name, cleaned_u_name)
        token_sort_ratio = fuzz.token_set_ratio(cleaned_name, cleaned_u_name)
        if ratio > best_ratio:
            best_ratio = ratio
            best_ratio_match = u_name
        if partial_ratio > best_partial_ratio:
            best_partial_ratio = partial_ratio
            best_partial_ratio_match = u_name
        if token_sort_ratio > best_token_sort_ratio:
            best_token_sort_ratio = token_sort_ratio
            best_token_sort_ratio_match = u_name
        if ratio == 100:
            break

    print(name, best_ratio_match, best_ratio, best_partial_ratio_match, best_partial_ratio, best_token_sort_ratio_match, best_token_sort_ratio)
    decision(sanitized, loc, name, cleaned_name, best_ratio_match, best_ratio, best_partial_ratio_match, best_partial_ratio, best_token_sort_ratio_match, best_token_sort_ratio)
    scoreboard.loc[loc] = pd.Series({'name':name, 'best_ratio_match':best_ratio_match, 'best_ratio':best_ratio, 'best_partial_ratio_match':best_partial_ratio_match,
                                     'best_partial_ratio': best_partial_ratio, 'best_token_sort_ratio_match': best_token_sort_ratio_match, 'best_token_sort_ratio': best_token_sort_ratio})

def decision(sanitized, loc, name, cleaned_name, best_ratio_match, best_ratio, best_partial_ratio_match, best_partial_ratio, best_token_sort_ratio_match, best_token_sort_ratio):
    if best_ratio >= 95:
        sanitized.loc[loc] = pd.Series({'orig': name, 'name': best_ratio_match, 'school': '', 'confidence': 'high'})
    elif (best_partial_ratio == 100 and best_partial_ratio_match.strip().lower() in cleaned_name.strip().lower()) or \
            (best_token_sort_ratio == 100 and best_token_sort_ratio_match.strip().lower() in cleaned_name.strip().lower()):
        sanitized.loc[loc] = pd.Series({
            'orig': name,
            'name': best_partial_ratio_match,
            'school': strip_school(cleaned_name, best_partial_ratio_match if best_partial_ratio == 100 else best_token_sort_ratio_match),
            'confidence': 'high'})
    else:
        if best_ratio > 90:
            sanitized.loc[loc] = pd.Series({'orig': name, 'name': best_ratio_match, 'school': '', 'confidence': f'ratio-{best_ratio}'})
        elif best_partial_ratio > 95:
            sanitized.loc[loc] = pd.Series({'orig': name, 'name': best_partial_ratio_match, 'school': '', 'confidence': f'partial-{best_partial_ratio}'})
        elif best_token_sort_ratio > 95:
            sanitized.loc[loc] = pd.Series(
                {'orig': name, 'name': best_token_sort_ratio_match, 'school': '', 'confidence': f'token-{best_token_sort_ratio}'})
        else:
            sanitized.loc[loc] = pd.Series(
                {'orig': name, 'name': name, 'school': '', 'confidence': 'not changed'})

def read_all_schools():
    all_world = pd.read_csv(r'/Users/gluo/Work/UChicagoIntern/world-universities.csv', header=None)
    all_world_names = all_world[1]
    return all_world_names

def read_acronyms():
    acronyms_df = pd.read_csv(r'/Users/gluo/Work/UChicagoIntern/acronym.csv', usecols=['acronym', 'fullname'])
    acronyms = dict(zip(acronyms_df.acronym, acronyms_df.fullname))
    return acronyms

def main():
    # read source data for unique school names
    #data = pd.read_csv(f"{dir_path}/data/alan_highest_degree.csv")
    data = pd.read_csv(f"{dir_path}/data/mytest.csv")
    name_list = pd.DataFrame(data, columns=['Institution of highest degree obtained'])
    unique_name_list = name_list["Institution of highest degree obtained"].unique();

    i = 0
    for name in unique_name_list:
        fuzzy_match(name, i)
        i += 1

    scoreboard.to_csv(f"{dir_path}/data/scoreboard.csv")
    sanitized.to_csv(f"{dir_path}/data/sanitized.csv")

dir_path = os.path.dirname(os.path.realpath(__file__))
# all universities in the world
all_school_names = read_all_schools()
# all acronyms
acronyms = read_acronyms()
# data frame to save fuzzy match scores
scoreboard = pd.DataFrame([], columns=['name', 'best_ratio_match', 'best_ratio', 'best_partial_ratio_match', 'best_partial_ratio',
                                           'best_token_sort_ratio_match', 'best_token_sort_ratio'])
# data frame to save harmanized names
sanitized = pd.DataFrame([], columns=['confidence','orig', 'name', 'school'])

def main2():
    sanitize_name("Harvard University Business School")
    sanitize_school(", school of business")


main()

