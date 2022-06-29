import pandas as pd
from fuzzywuzzy import fuzz
import re
import os

def strip_school(name, best_partial_ratio_match,loc):
    s_name = name.lower()
    s_match = best_partial_ratio_match.lower()
    start = s_name.find(s_match)
    end = start + len(s_match)
    school = (name[0:start] + name[end:len(name)]).strip()
    school = sanitize_school(school).lower()

    if 'at ' in school or ' at' in school:
        school = school.replace('at','')
    if ' the' in school:
        school = school.replace('the','')
    if '  ' in school:
        school = school.replace('  ','')
    school = school.replace('(','')
    school = school.replace(')','')
    
    if s_match in university_map:
        if len(school) > 0:
            for school_type in s_types:
                if school_type in school:
                    if school_type in university_map[s_match]:
                        school = university_map[s_match][school_type]
                        break
                    else:
                        university_map[s_match][school_type] = school
    else:
        university_map[s_match] = {}
        if len(school) > 0:
            for school_type in s_types:
                if school_type in school:
                    university_map[s_match][school_type] = school
                    break
    #print(school,loc)
    return school

def sanitize_school(school_name):
    if school_name.lower().find('school') == -1 and school_name.lower().find('college') == -1:
        return ''
    regex = re.compile('()[-,\.!?]')
    school_name = regex.sub('', school_name).strip()
    school_name = re.sub('\s+',' ', school_name)
    return school_name

def sanitize_name(name):
    # lower case, trimmed
    name = name.strip().lower()

    # remove The at the beginning
    if name.startswith("the "):
        name = name[4:len(name)]
    name = re.sub('\s+',' ', name)

    # replace acronyms
    namesplit = name.split()
    firstword = namesplit[0]
    if firstword in acronyms and name.find(acronyms[firstword].lower()) == -1:
        name = acronyms[firstword]
        if len(namesplit) > 1:
            name = name + ' ' + ' '.join(namesplit[1:])
        #print(f"replaced by acronym: {name}")
    return name


def match(name, loc):
    if name in special_matches:
        value = special_matches[name]
        sanitize_rules.loc[loc] = pd.Series(
            {'orig': name, 'name': value[0], 'school': value[1], 'confidence': 'exactmatch'})
        scoreboard.loc[loc] = pd.Series({'name': name, 'best_ratio_match': value[0], 'best_ratio': 100,
                                         'best_partial_ratio_match': value[0],
                                         'best_partial_ratio': 100,
                                         'best_token_sort_ratio_match': value[0],
                                         'best_token_sort_ratio': 100})
    else:
        fuzzy_match(name, loc)

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

    #print(name, best_ratio_match, best_ratio, best_partial_ratio_match, best_partial_ratio, best_token_sort_ratio_match, best_token_sort_ratio)
    sanitize_rules.loc[loc] = decision(name, cleaned_name, best_ratio_match, best_ratio, best_partial_ratio_match, best_partial_ratio, best_token_sort_ratio_match, best_token_sort_ratio,loc)
    scoreboard.loc[loc] = pd.Series({'name':name, 'best_ratio_match':best_ratio_match, 'best_ratio':best_ratio, 'best_partial_ratio_match':best_partial_ratio_match,
                                     'best_partial_ratio': best_partial_ratio, 'best_token_sort_ratio_match': best_token_sort_ratio_match, 'best_token_sort_ratio': best_token_sort_ratio})

def decision(name, cleaned_name, best_ratio_match, best_ratio, best_partial_ratio_match, best_partial_ratio, best_token_sort_ratio_match, best_token_sort_ratio,loc):
    if best_ratio >= 95:
        sanitized_row = pd.Series({'orig': name, 'name': best_ratio_match, 'school': '', 'confidence': 'high'})
    elif (best_partial_ratio == 100 and best_partial_ratio_match.strip().lower() in cleaned_name.strip().lower()) or \
            (best_token_sort_ratio == 100 and best_token_sort_ratio_match.strip().lower() in cleaned_name.strip().lower()):
        sanitized_row = pd.Series({
            'orig': name,
            'name': best_partial_ratio_match if best_partial_ratio_match == 100 else best_token_sort_ratio_match,
            'school': strip_school(cleaned_name, best_partial_ratio_match if best_partial_ratio == 100 else best_token_sort_ratio_match,loc),
            'confidence': 'high'})
    else:
        if best_ratio > 90:
            sanitized_row = pd.Series({'orig': name, 'name': best_ratio_match, 'school': '', 'confidence': f'ratio-{best_ratio}'})
        elif best_partial_ratio > 95:
            sanitized_row = pd.Series({'orig': name, 'name': best_partial_ratio_match, 'school': '', 'confidence': f'partial-{best_partial_ratio}'})
        elif best_token_sort_ratio > 95:
            sanitized_row = pd.Series(
                {'orig': name, 'name': best_token_sort_ratio_match, 'school': '', 'confidence': f'token-{best_token_sort_ratio}'})
        else:
            sanitized_row = pd.Series(
                {'orig': name, 'name': name, 'school': '', 'confidence': 'not changed'})

    return sanitized_row

def read_all_schools():
    all_world = pd.read_csv(f"{dir_path}/data/world-universities.csv", header=None)
    all_world_names = all_world[1]
    return all_world_names

def read_acronyms():
    acronyms_df = pd.read_csv(f"{dir_path}/data/acronym.csv", usecols=['acronym', 'fullname'])
    acronyms = dict(zip(acronyms_df.acronym, acronyms_df.fullname))
    return acronyms

def read_special_matches():
    special_match_df = pd.read_csv(f"{dir_path}/data/special_match.csv", usecols=['orig','name','school'])
    special_matches = {k: (v1, v2) for k, v1, v2 in zip(special_match_df.orig, special_match_df.name, special_match_df.school)}
    return special_matches

def read_school_types():
    school_types_df = pd.read_csv(f"{dir_path}/data/school_types.csv", header=None)
    school_types = school_types_df[0]
    return school_types

def harmanize_source(sanitize_rules_df):
    source = pd.DataFrame(data, columns=['newid', 'Institution of highest degree obtained'])
    updated_source = pd.DataFrame([], columns=['newid', 'Institution of highest degree obtained', 'name', 'school'])
    sanitize_rules_map = {k: (v1, v2) for k, v1, v2 in
                       zip(sanitize_rules_df.orig, sanitize_rules_df.name, sanitize_rules_df.school)}
    i = 0
    for index, row in source.iterrows():
        orig_name = row['Institution of highest degree obtained']
        if orig_name in sanitize_rules_map:
            value = sanitize_rules_map[orig_name]
            updated_source.loc[i] = pd.Series(
                    {'newid': row['newid'], 'Institution of highest degree obtained': row['Institution of highest degree obtained'],
                     'name': value[0], 'school': value[1]})
        else:
            updated_source.loc[i] = pd.Series(
                {'newid': row['newid'],
                 'Institution of highest degree obtained': row['Institution of highest degree obtained'],
                 'name': '', 'school': ''})
        i += 1
    return updated_source

def main():

    # step 1: build mapping rules
    name_list = pd.DataFrame(data, columns=['Institution of highest degree obtained'])
    unique_name_list = name_list["Institution of highest degree obtained"].unique()

    i = 0
    print(unique_name_list[145])
    for name in unique_name_list:
        if name.strip() == '-':
            continue
        match(name, i)
        i += 1

    scoreboard.to_csv(f"{dir_path}/data/scoreboard.csv")
    sanitize_rules.to_csv(f"{dir_path}/data/sanitize_rules.csv")

    # step 2: replace the university name based on mapping rules
    sanitize_rules_df = pd.read_csv(f"{dir_path}/data/sanitize_rules.csv", usecols=['orig', 'name', 'school'])

    updated_source = harmanize_source(sanitize_rules_df)
    updated_source.to_csv(f"{dir_path}/data/updated_source.csv")


# global values
dir_path = os.path.dirname(os.path.realpath(__file__))

# read source data for unique school names
data = pd.read_csv(f"{dir_path}/data/alan_highest_degree.csv")
# all universities in the world
all_school_names = read_all_schools()
# all acronyms
acronyms = read_acronyms()
# special matches
special_matches = read_special_matches()
# data frame to save fuzzy match scores
scoreboard = pd.DataFrame([], columns=['name', 'best_ratio_match', 'best_ratio', 'best_partial_ratio_match', 'best_partial_ratio',
                                           'best_token_sort_ratio_match', 'best_token_sort_ratio'])
# data frame to save harmanized names
sanitize_rules = pd.DataFrame([], columns=['confidence','orig', 'name', 'school'])

# data frame to create map of school names
s_types = read_school_types()
university_map = {}

# ------

main()

